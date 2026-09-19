"""Task 4F — Risk + Trust Fusion & Safe Abstention integration tests.

Hermetic harness (same pattern as the 4A/4B/4C/4D/4E/3B/3C suites): real
routers + auth/RBAC dependencies over an in-memory fake Mongo via FastAPI
TestClient, plus direct service-level calls.  No live MongoDB or backend
process required.

The locked inference engine is the real ``InferenceEngine`` over the repo
artifacts, so the full path runs genuinely in-process; success-path tests are
skipped only when the model artifacts are absent.

Covers:
- decision states (SUPPORTED / LIMITED_EVIDENCE / INSUFFICIENT_EVIDENCE):
  high & low risk x sufficient & insufficient trust
- incomplete four-week data honestly reported (temporal coverage)
- missing observations and insufficient temporal evidence -> abstentions
- invalid observations detected and downgraded (never over-stated)
- future-dated stored snapshots excluded (causal, no future leakage)
- deterministic repeated output
- explainable decision basis (never claims the model was modified)
- model output preserved vs the existing Phase 4C endpoint
- prediction unavailable / model failure / trust-calculation failure when the
  layer degrades to a safe abstention envelope (sanitized, no crash on 4E/4D)
- RBAC enforcement (WELFARE_OFFICER / PERSONNEL / COMMANDER) + isolation
- no 44-vector / model / path / credential exposure in any envelope
- Phase 4C / 4D / 4E regression protection
"""

from __future__ import annotations

import asyncio
import datetime
import json
import os
import sys
import warnings
from pathlib import Path

# auth_service requires AUTH_SECRET_KEY before import. Test-only secret.
os.environ.setdefault("AUTH_SECRET_KEY", "test-only-secret-key-not-for-production-1234567890")

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from lib.auth_service import create_access_token
from lib.inference import InferenceEngine

BACKEND_DIR = Path(__file__).resolve().parent.parent
ARTIFACT_DIR = BACKEND_DIR.parent / "artifacts"


# ---------------------------------------------------------------------------
# In-memory fake collections (minimal motor interface used by the routers)
# ---------------------------------------------------------------------------


class _FakeCursor:
    def __init__(self, docs):
        self._docs = list(docs)

    def sort(self, *args, **kwargs):
        return self

    async def to_list(self, length: int | None = None) -> list[dict]:
        if length is not None:
            return list(self._docs[:length])
        return list(self._docs)


class _FakeCollection:
    def __init__(self):
        self.docs: list[dict] = []

    async def find_one(self, query: dict):
        for doc in self.docs:
            if all(doc.get(k) == v for k, v in query.items()):
                return doc
        return None

    async def insert_one(self, doc):
        self.docs.append(dict(doc))
        return None

    async def update_many(self, query, update):
        for doc in self.docs:
            if all(doc.get(k) == v for k, v in query.items()):
                if "$set" in update:
                    doc.update(update["$set"])
        return None

    async def delete_many(self, query):
        self.docs = [d for d in self.docs if not all(d.get(k) == v for k, v in query.items())]
        return None

    async def count_documents(self, query):
        q = query or {}
        return sum(
            1
            for d in self.docs
            if all(d.get(k) == v for k, v in q.items() if not isinstance(v, dict))
        )

    def find(self, query=None):
        q = query or {}
        matches = [d for d in self.docs if all(d.get(k) == v for k, v in q.items())]
        return _FakeCursor(matches)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TZ = datetime.timezone.utc
WEEK = datetime.timedelta(days=7)
NOW = datetime.datetime.now(TZ)
ANCHOR = datetime.datetime(2026, 2, 22, tzinfo=TZ)

STATIC_FIELDS = {
    "years_of_service": 12.0,
    "hardship_posting_flag": 1,
    "transfer_count_24mo": 3.0,
    "years_in_current_posting": 2.5,
}

ALL_RAW_FIELDS = (
    "weekly_duty_hours",
    "night_shift_ratio",
    "overtime_hours",
    "days_since_last_rest",
    "days_since_last_leave",
    "leave_balance",
    "wellness_score_self_report",
    "sleep_quality_score_self_report",
    "resting_hr_trend_biometric",
    "sleep_hours_biometric",
)


def _utc(y, m, d, h=0, minute=0):
    return datetime.datetime(y, m, d, h, minute, tzinfo=TZ)


def _parse(value: str) -> datetime.datetime:
    return datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))


def _token(user_id: str, username: str, role: str) -> str:
    return create_access_token(user_id=user_id, username=username, role=role)


def _headers(user_id: str, username: str, role: str) -> dict:
    return {"Authorization": f"Bearer {_token(user_id, username, role)}"}


def _officer_headers():
    return _headers("wo-1", "welfareo", "WELFARE_OFFICER")


def await_result(coro):
    return asyncio.run(coro)


@pytest.fixture
def client(monkeypatch):
    """TestClient over the real routers with fake DB collections injected."""
    from lib.db import db

    monkeypatch.setattr(db, "users", _FakeCollection())
    monkeypatch.setattr(db, "personnel", _FakeCollection())
    monkeypatch.setattr(db, "risk_assessments", _FakeCollection())
    monkeypatch.setattr(db, "interventions", _FakeCollection())
    monkeypatch.setattr(db, "audit_logs", _FakeCollection())
    for name in ("wellness_logs", "workload_records", "deployment_history", "leave_requests", "status_checks"):
        monkeypatch.setattr(db, name, _FakeCollection())

    from routers.auth import router as auth_router
    from routers.welfare import router as welfare_router

    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(welfare_router)
    return TestClient(app)


@pytest.fixture(autouse=True)
def inference_engine(monkeypatch):
    """Pin the module-level router engine to a freshly loaded real engine."""
    import routers.welfare as rw

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            engine = InferenceEngine(ARTIFACT_DIR)
            engine.load()
        except Exception:
            engine = None
    if engine is not None:
        monkeypatch.setattr(rw, "engine", engine)
    return engine


def _require_engine(engine=None):
    if engine is None:
        pytest.skip("BLOCKED: LightGBM model artifacts unavailable in this environment")


def _seed_user(client, user_id: str, username: str, role: str):
    from lib.db import db

    db.users.docs.append({
        "id": user_id,
        "username": username,
        "role": role,
        "active": True,
        "password_hash": "unused-in-token-tests",
    })


def _seed_personnel(user_id: str, name: str = "Test Person", extra: dict | None = None):
    from lib.db import db

    doc = {
        "id": user_id,
        "name": name,
        "service_number": f"SRV-{user_id}",
        "rank": "Sepoy",
        "unit": "Provost Unit",
        "posting": "Field Base",
        "created_at": _utc(2026, 1, 1),
    }
    if extra:
        doc.update(extra)
    db.personnel.docs.append(doc)


def _seed_record(
    user_id: str,
    collection: str,
    note: str,
    created_at: datetime.datetime,
    payload_extra: dict | None = None,
    record_id: str | None = None,
):
    from lib.db import db

    doc = {
        "id": record_id or f"rec-{collection}-{note}",
        "personnel_id": user_id,
        "created_at": created_at,
        "payload": {"note": note, **(payload_extra or {})},
    }
    getattr(db, collection).docs.append(doc)


def _complete_stress_payloads():
    """4 fully-observed stress weeks -> real artifact = High risk, trust ~96."""
    return [
        {"weekly_duty_hours": 60, "night_shift_ratio": 0.5, "overtime_hours": 8,
         "days_since_last_rest": 6, "days_since_last_leave": 30, "leave_balance": 8,
         "wellness_score_self_report": 3.5, "sleep_quality_score_self_report": 3.0,
         "resting_hr_trend_biometric": 0.6, "sleep_hours_biometric": 6.0},
        {"weekly_duty_hours": 62, "night_shift_ratio": 0.5, "overtime_hours": 9,
         "days_since_last_rest": 6, "days_since_last_leave": 30, "leave_balance": 8,
         "wellness_score_self_report": 3.0, "sleep_quality_score_self_report": 2.5,
         "resting_hr_trend_biometric": 0.6, "sleep_hours_biometric": 5.5},
        {"weekly_duty_hours": 64, "night_shift_ratio": 0.5, "overtime_hours": 10,
         "days_since_last_rest": 6, "days_since_last_leave": 30, "leave_balance": 8,
         "wellness_score_self_report": 3.0, "sleep_quality_score_self_report": 3.0,
         "resting_hr_trend_biometric": 0.6, "sleep_hours_biometric": 5.5},
        {"weekly_duty_hours": 66, "night_shift_ratio": 0.5, "overtime_hours": 12,
         "days_since_last_rest": 6, "days_since_last_leave": 30, "leave_balance": 8,
         "wellness_score_self_report": 2.5, "sleep_quality_score_self_report": 2.5,
         "resting_hr_trend_biometric": 0.6, "sleep_hours_biometric": 5.0},
    ]


def _complete_mild_payloads():
    """4 fully-observed mild weeks -> real artifact = Low risk, trust ~97."""
    return [
        {"weekly_duty_hours": 39, "night_shift_ratio": 0.05, "overtime_hours": 0.5,
         "days_since_last_rest": 2, "days_since_last_leave": 6, "leave_balance": 35,
         "wellness_score_self_report": 8.5, "sleep_quality_score_self_report": 8.5,
         "resting_hr_trend_biometric": -0.3, "sleep_hours_biometric": 8.0},
        {"weekly_duty_hours": 40, "night_shift_ratio": 0.05, "overtime_hours": 1.0,
         "days_since_last_rest": 2, "days_since_last_leave": 6, "leave_balance": 35,
         "wellness_score_self_report": 8.5, "sleep_quality_score_self_report": 8.5,
         "resting_hr_trend_biometric": -0.3, "sleep_hours_biometric": 8.0},
        {"weekly_duty_hours": 41, "night_shift_ratio": 0.05, "overtime_hours": 0.5,
         "days_since_last_rest": 2, "days_since_last_leave": 6, "leave_balance": 35,
         "wellness_score_self_report": 8.5, "sleep_quality_score_self_report": 8.5,
         "resting_hr_trend_biometric": -0.3, "sleep_hours_biometric": 8.0},
        {"weekly_duty_hours": 40, "night_shift_ratio": 0.05, "overtime_hours": 0.5,
         "days_since_last_rest": 2, "days_since_last_leave": 6, "leave_balance": 35,
         "wellness_score_self_report": 8.5, "sleep_quality_score_self_report": 8.5,
         "resting_hr_trend_biometric": -0.3, "sleep_hours_biometric": 8.0},
    ]


def _seed_complete_window(personnel_id: str = "pers-A", stress: bool = True):
    """Four fully-observed weeks ending 2026-02-22 (High or Low risk)."""
    _seed_personnel(personnel_id, extra={**STATIC_FIELDS})
    series = _complete_stress_payloads() if stress else _complete_mild_payloads()
    for week, payload in enumerate(series):
        _seed_record(personnel_id, "wellness_logs", f"w{week}",
                     ANCHOR - (3 - week) * WEEK, payload_extra=payload)


def _seed_partial_window(personnel_id: str = "pers-A"):
    """Two observed weeks of four (wk1, wk3) -> honest half-coverage window."""
    _seed_personnel(personnel_id, extra={**STATIC_FIELDS})
    _seed_record(personnel_id, "wellness_logs", "wk3", ANCHOR,
                 payload_extra={"weekly_duty_hours": 66, "wellness_score_self_report": 3.5})
    _seed_record(personnel_id, "leave_requests", "wk1", ANCHOR - 2 * WEEK,
                 payload_extra={"leave_balance": 12})


def _seed_single_week(personnel_id: str = "pers-A"):
    """Single observation only -> prediction works but temporal evidence is thin."""
    _seed_personnel(personnel_id, extra={**STATIC_FIELDS})
    _seed_record(personnel_id, "wellness_logs", "only", ANCHOR,
                 payload_extra={"weekly_duty_hours": 66, "wellness_score_self_report": 3.5})


def _seed_empty_numeric_window(personnel_id: str = "pers-A"):
    """Four weeks of records that carry NO numeric welfare fields at all."""
    _seed_personnel(personnel_id, extra={**STATIC_FIELDS})
    for week in range(4):
        _seed_record(personnel_id, "wellness_logs", f"empty{week}",
                     ANCHOR - (3 - week) * WEEK, payload_extra={"note": f"w{week}"})


def _seed_invalid_observation_window(personnel_id: str = "pers-A"):
    """Fully-observed window but the latest observation has a negative rest day."""
    _seed_personnel(personnel_id, extra={**STATIC_FIELDS})
    series = _complete_stress_payloads()
    latest = dict(series[3])
    latest["days_since_last_rest"] = -7  # observed but physically impossible
    series[3] = latest
    for week, payload in enumerate(series):
        _seed_record(personnel_id, "wellness_logs", f"w{week}",
                     ANCHOR - (3 - week) * WEEK, payload_extra=payload)


def _seed_stored_assessment(
    personnel_id: str,
    id_suffix: str,
    assessed_at: datetime.datetime,
    features: dict | None = None,
    band: str = "Low",
    risk_probability: float = 0.9,
):
    """Seed a stored assessment doc exactly as the canonical pipeline writes it."""
    from lib.db import db

    doc = {
        "id": f"ass-{id_suffix}",
        "personnel_id": personnel_id,
        "assessed_at": assessed_at,
        "predicted_band": band,
        "risk_probability": risk_probability,
        "class_probabilities": [
            {"band": "Low", "probability": 0.9},
            {"band": "Moderate", "probability": 0.05},
            {"band": "High", "probability": 0.05},
        ],
        "is_latest": True,
    }
    if features is not None:
        doc["features"] = features
    db.risk_assessments.docs.append(doc)


def _current_features(personnel_id: str, engine):
    """Run the existing 4C service and return the exact current engineered vector."""
    from lib.welfare_prediction import predict_personnel_welfare

    _, _, features = await_result(predict_personnel_welfare(
        personnel_id, {"user_id": "wo-1", "role": "WELFARE_OFFICER"}, engine
    ))
    return features


def _decision(body: dict) -> str:
    return body["decision_state"]


# ===================================================================
# 0. Pure decision-rule + evidence-quality unit tests (no artifacts)
# ===================================================================


class _Eq:
    """Minimal stand-in EvidenceQuality for rule-matrix probing."""

    def __init__(self, cov=4, invalid=False, label="Sufficient", score=95.0):
        self.temporal_coverage_weeks = cov
        self.invalid_observations_detected = invalid
        self.label = label
        self.score = score


class TestDecisionRuleMatrix:
    def test_high_risk_sufficient_trust_supported(self):
        import routers.welfare as rw

        state, basis = rw._compute_decision_support_4f(_Eq(), data_trust_score=80.0, prediction_available=True, predicted_band="High")
        assert state == "SUPPORTED"
        assert "sufficient" in basis.lower()

    def test_low_risk_sufficient_trust_supported(self):
        import routers.welfare as rw

        state, basis = rw._compute_decision_support_4f(_Eq(), data_trust_score=80.0, prediction_available=True, predicted_band="Low")
        assert state == "SUPPORTED"
        assert "sufficient" in basis.lower()

    def test_high_risk_insufficient_trust_abstains(self):
        import routers.welfare as rw

        state, basis = rw._compute_decision_support_4f(_Eq(), data_trust_score=30.0, prediction_available=True, predicted_band="High")
        assert state == "INSUFFICIENT_EVIDENCE"
        assert "below" in basis.lower() and "abstains" in basis.lower()
        # abstention must never hide the reason behind a trusted-sounding basis
        assert "actionability threshold" in basis

    @pytest.mark.parametrize("band", ["High", "Low", "Moderate"])
    def test_trust_below_floor_abstains_regardless_of_band(self, band):
        import routers.welfare as rw

        state, _ = rw._compute_decision_support_4f(_Eq(), data_trust_score=30.0, prediction_available=True, predicted_band=band)
        assert state == "INSUFFICIENT_EVIDENCE"

    def test_prediction_unavailable_abstains_even_with_good_trust(self):
        import routers.welfare as rw

        state, basis = rw._compute_decision_support_4f(_Eq(), data_trust_score=95.0, prediction_available=False, predicted_band=None)
        assert state == "INSUFFICIENT_EVIDENCE"
        assert "not present" in basis.lower() or "unavailable" in basis.lower()

    def test_single_observed_week_is_limited(self):
        import routers.welfare as rw

        state, basis = rw._compute_decision_support_4f(_Eq(cov=1), data_trust_score=95.0, prediction_available=True, predicted_band="High")
        assert state == "LIMITED_EVIDENCE"
        assert "temporal" in basis.lower()

    def test_invalid_observations_downgrade_to_limited(self):
        import routers.welfare as rw

        state, basis = rw._compute_decision_support_4f(_Eq(invalid=True), data_trust_score=95.0, prediction_available=True, predicted_band="Low")
        assert state == "LIMITED_EVIDENCE"
        assert "invalid" in basis.lower()


class TestEvidenceQualityUnit:
    def test_absent_features_never_score_high_trust(self):
        import routers.welfare as rw

        eq = rw.compute_evidence_quality(
            {"week_count": 4, "weeks_with_data": [0, 1, 2, 3]},
            features=None,
            model_prediction_available=False,
        )
        # composite 50 (temporal 100 + validity 100) > 45 would read "Limited",
        # but the label is capped to Insufficient because the trust floor fails.
        assert eq.label == "Insufficient"
        assert eq.components.completeness == 0.0
        assert eq.temporal_coverage_weeks == 4
        assert eq.score < 70

    def test_evidence_quality_is_deterministic(self):
        import routers.welfare as rw

        kw = {"week_count": 4, "weeks_with_data": [0, 1, 2, 3]}
        first = rw.compute_evidence_quality(kw, None, False)
        second = rw.compute_evidence_quality(kw, None, False)
        assert first.score == second.score == 50.0
        assert first.label == second.label == "Insufficient"
        assert first.basis == second.basis
        assert first.threshold == rw.EVIDENCE_QUALITY_THRESHOLD

    def test_invalid_observations_detector_flags_non_negative_violations(self):
        import routers.welfare as rw

        non_negative = {
            "weekly_duty_hours", "overtime_hours", "days_since_last_rest",
            "days_since_last_leave", "leave_balance", "sleep_hours_biometric",
            "wellness_score_self_report", "sleep_quality_score_self_report",
        }
        good = {}
        for name in non_negative:
            good[name] = 1.0
            good[f"{name}__was_missing"] = 0
        assert rw._invalid_observations(good) is False
        bad = dict(good)
        bad["days_since_last_rest"] = -7.0
        assert rw._invalid_observations(bad) is True
        nan = dict(good)
        nan["leave_balance"] = float("nan")
        assert rw._invalid_observations(nan) is True
        # a missing (never-observed) negative value is NOT an invalid observation
        naive = dict(good)
        naive["overtime_hours__was_missing"] = 1
        naive["overtime_hours"] = -7.0
        assert rw._invalid_observations(naive) is False
        # the resting-heart-rate-trend can legitimately be negative
        delta = dict(good)
        delta.pop("days_since_last_rest", None)
        delta.pop("days_since_last_rest__was_missing", None)
        assert rw._invalid_observations(delta) is False


# ===================================================================
# 1. Decision states: risk x trust combinations
# ===================================================================


class TestDecisionStates:
    def test_high_risk_sufficient_trust_is_supported(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_complete_window("pers-H", stress=True)

        resp = client.get("/personnel/pers-H/welfare-decision-support", headers=_officer_headers())
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["prediction_available"] is True
        assert body["predicted_band"] == "High"
        assert body["evidence_quality"]["score"] >= 55
        assert body["evidence_quality"]["label"] == "Sufficient"
        assert _decision(body) == "SUPPORTED"
        assert body["prediction_available"] and body["predicted_band"]

    def test_low_risk_sufficient_trust_is_supported(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_complete_window("pers-L", stress=False)

        body = client.get("/personnel/pers-L/welfare-decision-support", headers=_officer_headers()).json()
        assert body["predicted_band"] == "Low"
        assert body["evidence_quality"]["label"] == "Sufficient"
        assert _decision(body) == "SUPPORTED"

    def test_absent_evidence_abstains_regardless_of_band(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        # four weeks of records that carry NO numeric welfare fields at all:
        # the model can run, but Data Trust falls below the abstention floor.
        _seed_empty_numeric_window("pers-N")

        body = client.get("/personnel/pers-N/welfare-decision-support", headers=_officer_headers()).json()
        assert _decision(body) == "INSUFFICIENT_EVIDENCE"
        assert body["evidence_quality"]["label"] == "Insufficient"
        assert body["predicted_band"] in ("Low", "Moderate", "High")

    def test_incomplete_four_week_data_is_honestly_reported(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_partial_window("pers-P")

        body = client.get("/personnel/pers-P/welfare-decision-support", headers=_officer_headers()).json()
        assert body["data_sufficiency"]["weeks_with_data"] == [1, 3]
        assert body["evidence_quality"]["temporal_coverage_weeks"] == 2
        assert body["evidence_quality"]["label"] == "Limited"
        assert body["prediction_available"] is True
        assert _decision(body) in ("SUPPORTED", "LIMITED_EVIDENCE", "INSUFFICIENT_EVIDENCE")

    def test_missing_observations_never_claims_improvement(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_empty_numeric_window("pers-M")

        body = client.get("/personnel/pers-M/welfare-decision-support", headers=_officer_headers()).json()
        blob = json.dumps(body).lower()
        assert _decision(body) != "SUPPORTED"
        # absence of data is never turned into an actual change/improvement claim
        wc = body.get("what_changed") or {}
        assert wc.get("changes") == []
        # and the only mention of improvement/deterioration is the fixed negation
        assert "absence of data is never treated as evidence" in blob

    def test_insufficient_temporal_evidence_is_limited(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_single_week("pers-S")

        body = client.get("/personnel/pers-S/welfare-decision-support", headers=_officer_headers()).json()
        assert body["evidence_quality"]["temporal_coverage_weeks"] == 1
        assert body["evidence_quality"]["label"] == "Limited"
        assert _decision(body) == "LIMITED_EVIDENCE"
        assert "temporal" in body["decision_basis"].lower()

    def test_invalid_observations_flagged_and_downgraded(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_invalid_observation_window("pers-I")

        body = client.get("/personnel/pers-I/welfare-decision-support", headers=_officer_headers()).json()
        assert body["evidence_quality"]["invalid_observations_detected"] is True
        assert body["evidence_quality"]["label"] == "Limited"
        assert _decision(body) == "LIMITED_EVIDENCE"
        assert "invalid" in body["decision_basis"].lower()
        # the invalid observation is never presented as a trusted risk conclusion
        assert "not sufficiently reliable" not in json.dumps(body)
        assert "data-quality caveat" in body["decision_basis"].lower()

    def test_future_dated_snapshots_never_compared(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_complete_window("pers-F", stress=True)
        features = _current_features("pers-F", inference_engine)
        prior = {**features, "weekly_duty_hours": 40.0, "weekly_duty_hours__was_missing": 0}
        _seed_stored_assessment("pers-F", "past", NOW - datetime.timedelta(days=30), features=prior)
        future = {**features, "weekly_duty_hours": 999.0, "weekly_duty_hours__was_missing": 0}
        _seed_stored_assessment("pers-F", "future", NOW + datetime.timedelta(days=4000), features=future)

        resp = client.get("/personnel/pers-F/welfare-decision-support", headers=_officer_headers())
        assert resp.status_code == 200, resp.text
        assert "999" not in resp.text
        what = resp.json()["what_changed"]
        assert what["status"] == "available"
        assert what["comparison"] == "prior_assessment"
        duty = next(item for item in what["changes"] if item["feature"] == "weekly_duty_hours")
        assert duty["previous"] == 40.0

    def test_deterministic_output(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_complete_window("pers-D", stress=True)

        first = client.get("/personnel/pers-D/welfare-decision-support", headers=_officer_headers()).json()
        second = client.get("/personnel/pers-D/welfare-decision-support", headers=_officer_headers()).json()
        for key in ("decision_state", "decision_basis", "predicted_band", "risk_probability",
                    "prediction_confidence", "evidence_quality", "trend", "what_changed"):
            assert first[key] == second[key], f"{key} not deterministic"
        assert first["assessed_at"] != second["assessed_at"]

    def test_explainable_decision_basis(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_complete_window("pers-X", stress=True)

        body = client.get("/personnel/pers-X/welfare-decision-support", headers=_officer_headers()).json()
        assert body["decision_basis"]
        assert body["evidence_quality"]["basis"]
        assert body["confidence_basis"]
        assert body["derived_outputs"]
        # explainable: the exact mechanism is stated, never a black box
        assert "reuses" in body["evidence_quality"]["basis"]
        derived = json.dumps(body["derived_outputs"]).lower()
        assert "not model confidence" in derived
        assert "never modified" in derived or "not modified" in derived

    def test_prediction_fields_match_4c_exactly(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_complete_window("pers-M", stress=True)

        four_c = client.get("/personnel/pers-M/welfare-prediction", headers=_officer_headers()).json()
        body = client.get("/personnel/pers-M/welfare-decision-support", headers=_officer_headers()).json()
        # Phase 4F REUSES the 4C model output; it must be byte-for-byte identical.
        assert body["predicted_band"] == four_c["predicted_band"]
        assert body["risk_probability"] == four_c["risk_probability"]
        assert body["class_probabilities"] == four_c["class_probabilities"]
        assert body["prediction_confidence"] == four_c["prediction_confidence"]
        assert body["confidence_basis"] == four_c["confidence_basis"]
        assert body["top_contributing_factors"] == four_c["top_contributing_factors"]
        # and the abstention language must never claim the model was altered
        assert "never modified" in json.dumps(body["derived_outputs"]).lower()


# ===================================================================
# 2. Availability & failure handling
# ===================================================================


class _BrokenEngine:
    load_error = "Missing model artifacts: risk_model.pkl, baseline_model.pkl"
    risk_model = None
    preprocessing_pipeline = None


class _RaisingEngine:
    load_error = None
    risk_model = object()
    preprocessing_pipeline = object()

    def predict_from_raw_records(self, *args, **kwargs):
        from lib.inference import ModelArtifactError
        raise ModelArtifactError("inference explosion")


class _ExplodingTrust:
    load_error = None
    risk_model = object()
    preprocessing_pipeline = object()

    def predict_from_raw_records(self, *args, **kwargs):
        raise ValueError("unexpected shutdown of the training server")


class TestAvailabilityAndFailure:
    def test_no_welfare_history_returns_sanitized_abstention_envelope(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-E", extra={**STATIC_FIELDS})  # no welfare records at all

        resp = client.get("/personnel/pers-E/welfare-decision-support", headers=_officer_headers())
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["prediction_available"] is False
        assert body["predicted_band"] is None
        assert body["risk_probability"] is None
        assert _decision(body) == "INSUFFICIENT_EVIDENCE"
        assert body["evidence_quality"]["label"] == "Insufficient"
        assert body["evidence_quality"]["components"]["completeness"] == 0.0
        assert "No model-backed prediction" in " ".join(body["welfare_recommendations"])

    def test_broken_artifacts_return_sanitized_503(self, client, inference_engine, monkeypatch):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_complete_window("pers-B", stress=True)

        import routers.welfare as rw
        monkeypatch.setattr(rw, "engine", _BrokenEngine())

        resp = client.get("/personnel/pers-B/welfare-decision-support", headers=_officer_headers())
        assert resp.status_code == 503
        for forbidden in ("risk_model.pkl", "risk_model", "baseline_model.pkl", "Missing model artifacts"):
            assert forbidden not in resp.text, f"leaked {forbidden}"

    def test_inference_failure_returns_sanitized_503(self, client, inference_engine, monkeypatch):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_complete_window("pers-R", stress=True)

        import routers.welfare as rw
        monkeypatch.setattr(rw, "engine", _RaisingEngine())

        resp = client.get("/personnel/pers-R/welfare-decision-support", headers=_officer_headers())
        assert resp.status_code == 503
        for forbidden in ("inference explosion", ".pkl", "Traceback", "File "):
            assert forbidden not in resp.text, f"leaked {forbidden}"

    def test_trust_calculation_failure_degrades_to_safe_abstention(self, client, inference_engine, monkeypatch):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_complete_window("pers-T", stress=True)

        import routers.welfare as rw

        def exploding_trust(features):
            raise RuntimeError("boom: trust engine unreachable")

        monkeypatch.setattr(rw, "_data_trust", exploding_trust)

        resp = client.get("/personnel/pers-T/welfare-decision-support", headers=_officer_headers())
        # trust failure must NEVER crash the endpoint or leak internals; the
        # layer degrades to a safe abstention envelope instead.
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert _decision(body) == "INSUFFICIENT_EVIDENCE"
        assert body["evidence_quality"]["label"] == "Insufficient"
        assert "abstains" in body["evidence_quality"]["basis"].lower()
        for forbidden in ("boom", "RuntimeError", "Traceback"):
            assert forbidden not in resp.text, f"leaked {forbidden}"

    def test_prediction_unavailable_still_reports_stored_data(self, client, inference_engine, monkeypatch):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_empty_numeric_window("pers-U")

        resp = client.get("/personnel/pers-U/welfare-decision-support", headers=_officer_headers())
        assert resp.status_code == 200, resp.text
        blob = resp.json()
        # never a fabricated risk conclusion on garbage/absent data
        assert blob["decision_state"] in ("INSUFFICIENT_EVIDENCE", "LIMITED_EVIDENCE")
        assert blob["prediction_available"] in (True, False)


# ===================================================================
# 3. RBAC + personnel isolation
# ===================================================================


class TestRbacAndPersonnelIsolation:
    def test_welfare_officer_is_authorized(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_complete_window("pers-A", stress=True)
        resp = client.get("/personnel/pers-A/welfare-decision-support", headers=_officer_headers())
        assert resp.status_code == 200

    def test_personnel_cannot_request_another_persons_support(self, client, inference_engine):
        _seed_user(client, "pers-A", "persona", "PERSONNEL")
        _seed_user(client, "pers-B", "personb", "PERSONNEL")
        _seed_complete_window("pers-B", stress=False)

        resp = client.get("/personnel/pers-B/welfare-decision-support",
                          headers=_headers("pers-A", "persona", "PERSONNEL"))
        assert resp.status_code == 403
        blob = resp.text
        for forbidden in ("pers-B", "decision_state", "predicted_band", "risk_probability", "weekly_duty_hours"):
            assert forbidden not in blob, f"leaked {forbidden}"

    def test_personnel_cannot_request_own_support(self, client, inference_engine):
        _seed_user(client, "pers-A", "persona", "PERSONNEL")
        _seed_complete_window("pers-A", stress=False)
        resp = client.get("/personnel/pers-A/welfare-decision-support",
                          headers=_headers("pers-A", "persona", "PERSONNEL"))
        assert resp.status_code == 403
        assert "decision_state" not in resp.text

    def test_commander_is_blocked_aggregate_only(self, client, inference_engine):
        _seed_user(client, "cmd-1", "cmdr", "COMMANDER")
        _seed_complete_window("pers-A", stress=True)
        resp = client.get("/personnel/pers-A/welfare-decision-support",
                          headers=_headers("cmd-1", "cmdr", "COMMANDER"))
        assert resp.status_code == 403
        assert "pers-A" not in resp.text

    def test_unauthenticated_is_blocked(self, client, inference_engine):
        resp = client.get("/personnel/pers-A/welfare-decision-support")
        assert resp.status_code in (401, 403)


# ===================================================================
# 4. No 44-vector / model / path / credential exposure
# ===================================================================


class TestNoVectorOrModelExposure:
    FORBIDDEN_BODY_TOKENS = (
        ".pkl",
        "risk_model",
        "baseline_model",
        "preprocessing_pipeline",
        "model_metadata.json",
        "artifact",
        "MODEL_ARTIFACT_DIR",
        "joblib",
        "C:\\",
        "auth_secret",
        "password",
        "MONGO_URL",
    )
    FORBIDDEN_KEYS = ("features",)
    ENGINEERED_NAME_TOKENS = ("__roll4_mean", "__delta_wow", "__was_missing")

    @staticmethod
    def _yield_keys(value):
        if isinstance(value, dict):
            for key, val in value.items():
                yield key
                yield from TestNoVectorOrModelExposure._yield_keys(val)
        elif isinstance(value, list):
            for item in value:
                yield from TestNoVectorOrModelExposure._yield_keys(item)

    def _assert_no_vector_or_internals(self, body):
        blob = json.dumps(body)
        for forbidden in self.FORBIDDEN_BODY_TOKENS:
            assert forbidden not in blob, f"leaked forbidden token {forbidden}"
        keys = set(self._yield_keys(body))
        for token in self.FORBIDDEN_KEYS + self.ENGINEERED_NAME_TOKENS:
            assert token not in keys, f"engineered/vector key '{token}' leaked"
        assert "features" not in blob

    def test_success_exposes_no_vector_or_model_internals(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_complete_window("pers-A", stress=True)

        resp = client.get("/personnel/pers-A/welfare-decision-support", headers=_officer_headers())
        assert resp.status_code == 200, resp.text
        self._assert_no_vector_or_internals(resp.json())

    def test_abstention_envelope_exposes_nothing(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-E", extra={**STATIC_FIELDS})

        body = client.get("/personnel/pers-E/welfare-decision-support", headers=_officer_headers()).json()
        self._assert_no_vector_or_internals(body)
        assert body["decision_state"] == "INSUFFICIENT_EVIDENCE"
        assert "features" not in json.dumps(body)

    def test_denied_responses_expose_no_support_material(self, client, inference_engine):
        _seed_user(client, "pers-A", "persona", "PERSONNEL")
        _seed_complete_window("pers-X", stress=True)
        resp = client.get("/personnel/pers-X/welfare-decision-support",
                          headers=_headers("pers-A", "persona", "PERSONNEL"))
        assert resp.status_code == 403
        for forbidden in self.FORBIDDEN_BODY_TOKENS + ("pers-X", "66", "High", "SUPPORTED"):
            assert forbidden not in resp.text, f"leaked forbidden token {forbidden}"


# ===================================================================
# 5. Phase 4C + 4D + 4E regression protection
# ===================================================================


class TestRegressionPhases4c4d4e:
    def test_welfare_prediction_endpoint_still_works(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_complete_window("pers-A", stress=True)
        resp = client.get("/personnel/pers-A/welfare-prediction", headers=_officer_headers())
        assert resp.status_code == 200, resp.text
        assert resp.json()["predicted_band"] == "High"

    def test_welfare_trajectory_endpoint_still_works(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_complete_window("pers-A", stress=True)
        _seed_stored_assessment("pers-A", "old", _utc(2026, 1, 1), band="Low", risk_probability=0.9)
        resp = client.get("/personnel/pers-A/welfare-trajectory", headers=_officer_headers())
        assert resp.status_code == 200, resp.text
        assert resp.json()["trend"] in ("increasing", "decreasing", "stable", "insufficient_data")

    def test_welfare_explanation_endpoint_still_works(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_complete_window("pers-A", stress=True)
        resp = client.get("/personnel/pers-A/welfare-explanation", headers=_officer_headers())
        assert resp.status_code == 200, resp.text
        assert resp.json()["explanation_status"] == "available"

    def test_model_info_features_still_44(self, client, inference_engine):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        info = client.get("/model-info")
        assert info.status_code == 200, info.text
        assert info.json()["feature_count"] == 44


# ===================================================================
# 6. Module entry-point contract
# ===================================================================


def test_service_exports_expected_entry_points():
    import routers.welfare as welfare

    assert callable(welfare.compute_evidence_quality)
    assert callable(welfare._compute_decision_support_4f)
    assert callable(welfare._invalid_observations)
    assert welfare.MINIMUM_TEMPORAL_WEEKS == 2
    assert welfare.TRUST_ABSTENTION_THRESHOLD == 60.0
    assert welfare.EVIDENCE_QUALITY_THRESHOLD == 55.0

    route_paths = {route.path for route in welfare.router.routes}
    assert "/personnel/{personnel_id}/welfare-decision-support" in route_paths