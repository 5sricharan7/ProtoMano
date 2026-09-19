"""Task 4D — Welfare risk trajectory and early-warning integration tests.

Hermetic harness (same pattern as the 4A/4B/4C/3B/3C suites): real routers +
auth/RBAC dependencies over an in-memory fake Mongo via FastAPI TestClient,
plus direct service-level calls.  No live MongoDB or backend process required.

The locked inference engine is the real ``InferenceEngine`` over the repo
artifacts, so the full MongoDB -> 4-week raw window -> canonical 44-feature
engineering -> calibrated LightGBM prediction -> trajectory classification path
runs genuinely in-process; success-path tests are skipped only when the model
artifacts are absent.

Covers:
- pure trajectory classification (increasing / decreasing / stable / insufficient_data)
- pure temporal early-warning rules (never fires from a single point or missing data)
- endpoint envelope (trend, early warning, minimized history, current prediction)
- increasing / decreasing / stable / sustained-high / single-point trajectories
- missing weeks / missing assessment history -> no fabricated points or warnings
- causal no-future-leakage cut-off for future-dated stored assessments
- deterministic repeated output
- RBAC enforcement (WELFARE_OFFICER / PERSONNEL / COMMANDER) + personnel isolation
- no 44-vector exposure, no model/path exposure, no class-probability leak
- regression protection for the existing welfare APIs
"""

from __future__ import annotations

import asyncio
import datetime
import json
import os
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

STATIC_FIELDS = {
    "years_of_service": 12.0,
    "hardship_posting_flag": 1,
    "transfer_count_24mo": 3.0,
    "years_in_current_posting": 2.5,
}


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


def _seed_assessment(
    personnel_id: str,
    id_suffix: str,
    assessed_at: datetime.datetime,
    band: str,
    risk_probability: float,
    high_probability: float,
):
    """Seed a stored assessment doc exactly as the canonical pipeline writes it."""
    from lib.db import db

    moderate = 0.04
    low = max(0.0, 1.0 - high_probability - moderate)
    db.risk_assessments.docs.append({
        "id": f"ass-{id_suffix}",
        "personnel_id": personnel_id,
        "assessed_at": assessed_at,
        "predicted_band": band,
        "risk_probability": risk_probability,
        "class_probabilities": [
            {"band": "Low", "probability": low},
            {"band": "Moderate", "probability": moderate},
            {"band": "High", "probability": high_probability},
        ],
        "is_latest": True,
    })


def _seed_full_window(personnel_id: str = "pers-A"):
    """Exact 4-week stress hint line ending 2026-02-22 -> High risk."""
    _seed_personnel(personnel_id, extra={**STATIC_FIELDS})
    anchor = _utc(2026, 2, 22)
    _seed_record(personnel_id, "wellness_logs", "wk3", anchor,
                 payload_extra={"weekly_duty_hours": 66, "wellness_score_self_report": 3.5})
    _seed_record(personnel_id, "workload_records", "wk2", anchor - WEEK,
                 payload_extra={"weekly_duty_hours": 54, "overtime_hours": 9.4})
    _seed_record(personnel_id, "leave_requests", "wk1", anchor - 2 * WEEK,
                 payload_extra={"leave_balance": 12})
    _seed_record(personnel_id, "deployment_history", "wk0", anchor - 3 * WEEK,
                 payload_extra={"days_since_last_rest": 6})


def _seed_mild_window(personnel_id: str = "pers-A"):
    """Exact 4-week mild window ending 2026-02-22 -> Low risk."""
    _seed_personnel(personnel_id, extra={**STATIC_FIELDS})
    anchor = _utc(2026, 2, 22)
    _seed_record(personnel_id, "wellness_logs", "wk3", anchor,
                 payload_extra={"weekly_duty_hours": 40, "wellness_score_self_report": 8.0,
                                "sleep_quality_score_self_report": 8.0})
    _seed_record(personnel_id, "workload_records", "wk2", anchor - WEEK,
                 payload_extra={"weekly_duty_hours": 41, "overtime_hours": 1.0})
    _seed_record(personnel_id, "leave_requests", "wk1", anchor - 2 * WEEK,
                 payload_extra={"leave_balance": 35})
    _seed_record(personnel_id, "deployment_history", "wk0", anchor - 3 * WEEK,
                 payload_extra={"days_since_last_rest": 2})


def _seed_partial_window(personnel_id: str = "pers-A"):
    """4-week span with weeks 0 and 2 missing entirely (weeks 1, 3 present)."""
    _seed_personnel(personnel_id, extra={**STATIC_FIELDS})
    anchor = _utc(2026, 2, 22)
    _seed_record(personnel_id, "wellness_logs", "wk3", anchor,
                 payload_extra={"weekly_duty_hours": 40, "wellness_score_self_report": 8.0})
    _seed_record(personnel_id, "leave_requests", "wk1", anchor - 2 * WEEK,
                 payload_extra={"leave_balance": 35})


# ===================================================================
# 1. Pure trajectory classification
# ===================================================================


def _point(assessed_at, band, risk_probability, high_probability, id_suffix="x"):
    return {
        "id": f"p-{id_suffix}",
        "assessed_at": assessed_at,
        "predicted_band": band,
        "risk_probability": risk_probability,
        "class_probabilities": [
            {"band": "Low", "probability": max(0.0, 1.0 - high_probability - 0.04)},
            {"band": "Moderate", "probability": 0.04},
            {"band": "High", "probability": high_probability},
        ],
    }


class TestClassifyTrajectory:
    def test_increasing_returns_increasing(self):
        from lib.trajectory import classify_trajectory
        assert classify_trajectory([
            _point(_utc(2026, 1, 1), "Low", 0.95, 0.05),
            _point(_utc(2026, 1, 8), "High", 0.40, 0.40),
        ]) == "increasing"

    def test_decreasing_returns_decreasing(self):
        from lib.trajectory import classify_trajectory
        assert classify_trajectory([
            _point(_utc(2026, 1, 1), "High", 0.85, 0.85),
            _point(_utc(2026, 1, 8), "High", 0.49, 0.49),
        ]) == "decreasing"

    def test_stable_within_epsilon(self):
        from lib.trajectory import classify_trajectory
        assert classify_trajectory([
            _point(_utc(2026, 1, 1), "Low", 0.95, 0.017090),
            _point(_utc(2026, 1, 8), "Low", 0.95, 0.017090),
        ]) == "stable"

    def test_insufficient_data_for_single_point(self):
        from lib.trajectory import classify_trajectory
        assert classify_trajectory([_point(_utc(2026, 1, 1), "High", 0.49, 0.49)]) == "insufficient_data"

    def test_insufficient_data_for_empty_or_missing_timestamps(self):
        from lib.trajectory import classify_trajectory
        assert classify_trajectory([]) == "insufficient_data"
        point = _point(_utc(2026, 1, 1), "High", 0.49, 0.49)
        point["assessed_at"] = None
        assert classify_trajectory([point, _point(_utc(2026, 1, 8), "Low", 0.5, 0.1)]) == "insufficient_data"

    def test_orders_points_chronologically_regardless_of_input_order(self):
        from lib.trajectory import classify_trajectory
        newer = _point(_utc(2026, 1, 8), "Low", 0.95, 0.05)
        older = _point(_utc(2026, 1, 1), "High", 0.85, 0.85)
        assert classify_trajectory([newer, older]) == "decreasing"

    def test_signal_is_high_class_probability_not_predicted_band_confidence(self):
        # Band Low with confidence 0.95, then band High with confidence 0.40.
        # High-class probability rises 0.017 -> 0.40 = increasing risk, even
        # though raw risk_probability falls 0.95 -> 0.40.
        from lib.trajectory import classify_trajectory
        assert classify_trajectory([
            _point(_utc(2026, 1, 1), "Low", 0.95, 0.017090),
            _point(_utc(2026, 1, 8), "High", 0.40, 0.40),
        ]) == "increasing"

    def test_labels_are_exactly_the_4d_set(self):
        from lib.trajectory import classify_trajectory
        scenarios = [
            ([_point(_utc(2026, 1, 1), "High", 0.85, 0.85),
              _point(_utc(2026, 1, 8), "High", 0.49, 0.49)], "decreasing"),
            ([_point(_utc(2026, 1, 1), "Low", 0.95, 0.05),
              _point(_utc(2026, 1, 8), "High", 0.49, 0.49)], "increasing"),
            ([_point(_utc(2026, 1, 1), "Low", 0.95, 0.017090),
              _point(_utc(2026, 1, 8), "Low", 0.95, 0.017090)], "stable"),
            ([_point(_utc(2026, 1, 1), "High", 0.49, 0.49)], "insufficient_data"),
        ]
        for points, expected in scenarios:
            assert classify_trajectory(points) == expected


# ===================================================================
# 2. Pure temporal early-warning rules
# ===================================================================


class TestBuildEarlyWarning:
    def test_single_high_point_never_warns(self):
        from lib.trajectory import build_early_warning
        warning = build_early_warning([_point(_utc(2026, 1, 1), "High", 0.49, 0.49)])
        assert warning["status"] == "not_available"
        assert "requires at least two chronologically ordered assessments" in warning["basis"]

    def test_empty_history_never_warns(self):
        from lib.trajectory import build_early_warning
        assert build_early_warning([])["status"] == "not_available"

    def test_two_consecutive_high_is_human_review(self):
        from lib.trajectory import build_early_warning
        warning = build_early_warning([
            _point(_utc(2026, 1, 1), "High", 0.85, 0.85),
            _point(_utc(2026, 1, 8), "High", 0.49, 0.49),
        ])
        assert warning["status"] == "human_review"
        assert "both" in warning["basis"]

    def test_rising_low_to_high_is_watch(self):
        from lib.trajectory import build_early_warning
        warning = build_early_warning([
            _point(_utc(2026, 1, 1), "Low", 0.95, 0.05),
            _point(_utc(2026, 1, 8), "High", 0.49, 0.49),
        ])
        assert warning["status"] == "watch"

    def test_easing_high_to_low_is_not_available(self):
        from lib.trajectory import build_early_warning
        warning = build_early_warning([
            _point(_utc(2026, 1, 1), "High", 0.85, 0.85),
            _point(_utc(2026, 1, 8), "Low", 0.95, 0.017090),
        ])
        assert warning["status"] == "not_available"

    def test_stable_is_not_available(self):
        from lib.trajectory import build_early_warning
        warning = build_early_warning([
            _point(_utc(2026, 1, 1), "Low", 0.95, 0.017090),
            _point(_utc(2026, 1, 8), "Low", 0.95, 0.017090),
        ])
        assert warning["status"] == "not_available"


# ===================================================================
# 3. Endpoint envelope
# ===================================================================


class TestTrajectoryEndpointEnvelope:
    def test_officer_gets_trajectory_envelope(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_mild_window("pers-A")
        _seed_assessment("pers-A", "old", _utc(2026, 1, 1), "Low", 0.90, 0.05)

        resp = client.get("/personnel/pers-A/welfare-trajectory", headers=_officer_headers())
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["personnel_id"] == "pers-A"
        assert body["trend"] in ("increasing", "decreasing", "stable", "insufficient_data")
        assert body["early_warning"]["status"] in ("human_review", "watch", "not_available")
        assert len(body["history"]) == 1
        assert body["history"][0]["predicted_band"] == "Low"
        assert body["prediction"]["predicted_band"] in ("Low", "Moderate", "High")
        assert 0.0 <= body["prediction"]["risk_probability"] <= 1.0
        assert body["evidence_basis"]
        assert body["derived_outputs"]
        assert "class_probabilities" not in json.dumps(body)

    def test_no_stored_data_returns_unavailable_envelope(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A", extra={**STATIC_FIELDS})

        resp = client.get("/personnel/pers-A/welfare-trajectory", headers=_officer_headers())
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "insufficient_data"
        assert body["reason"] == "no_welfare_history"
        keys = set(TestNoVectorOrModelExposure._yield_keys(body))
        for forbidden in ("trend", "early_warning", "prediction", "predicted_band"):
            assert forbidden not in keys, f"guessed trajectory material leaked {forbidden}"

    def test_service_raises_unavailable_for_ghost_personnel(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        from lib.trajectory import build_personnel_trajectory
        from lib.welfare_prediction import WelfarePredictionUnavailable
        with pytest.raises(WelfarePredictionUnavailable):
            await_result(build_personnel_trajectory(
                "ghost-id", {"user_id": "wo-1", "role": "WELFARE_OFFICER"}, inference_engine
            ))


# ===================================================================
# 4. Trend scenarios
# ===================================================================


class TestTrendScenarios:
    def test_increasing_trajectory_warns(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_full_window("pers-A")  # current: High 0.490
        _seed_assessment("pers-A", "old", _utc(2026, 1, 1), "Low", 0.90, 0.05)

        body = client.get("/personnel/pers-A/welfare-trajectory", headers=_officer_headers()).json()
        assert body["trend"] == "increasing"
        assert body["early_warning"]["status"] == "watch"
        assert body["prediction"]["predicted_band"] == "High"
        assert len(body["history"]) == 1

    def test_decreasing_trajectory_has_no_warning(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_mild_window("pers-A")  # current: Low 0.017
        _seed_assessment("pers-A", "old", _utc(2026, 1, 1), "High", 0.85, 0.85)

        body = client.get("/personnel/pers-A/welfare-trajectory", headers=_officer_headers()).json()
        assert body["trend"] == "decreasing"
        assert body["early_warning"]["status"] == "not_available"
        assert body["prediction"]["predicted_band"] == "Low"

    def test_stable_trajectory_has_no_warning(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_mild_window("pers-A")

        pred = client.get("/personnel/pers-A/welfare-prediction", headers=_officer_headers()).json()
        high_prob = next(cp["probability"] for cp in pred["class_probabilities"] if cp["band"] == "High")
        _seed_assessment("pers-A", "old", _utc(2026, 1, 1), "Low", pred["risk_probability"], high_prob)

        body = client.get("/personnel/pers-A/welfare-trajectory", headers=_officer_headers()).json()
        assert body["trend"] == "stable"
        assert body["early_warning"]["status"] == "not_available"

    def test_sustained_high_risk_issues_human_review_even_when_easing(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_full_window("pers-A")  # current: High 0.490
        _seed_assessment("pers-A", "old", _utc(2026, 1, 1), "High", 0.85, 0.85)

        body = client.get("/personnel/pers-A/welfare-trajectory", headers=_officer_headers()).json()
        assert body["trend"] == "decreasing"
        assert body["early_warning"]["status"] == "human_review"
        assert "both show a High risk band" in body["early_warning"]["basis"]

    def test_single_assessment_never_warns_even_when_high(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_full_window("pers-A")  # current alone is High; NO stored assessments

        body = client.get("/personnel/pers-A/welfare-trajectory", headers=_officer_headers()).json()
        assert body["trend"] == "insufficient_data"
        assert body["early_warning"]["status"] == "not_available"
        assert body["prediction"]["predicted_band"] == "High"
        assert body["history"] == []


# ===================================================================
# 5. Missing weeks / missing history never fabricate
# ===================================================================


class TestMissingDataNeverFabricates:
    def test_partial_window_still_trajectory_with_no_fabricated_history(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_partial_window("pers-A")
        _seed_assessment("pers-A", "old", _utc(2026, 1, 1), "Low", 0.90, 0.05)

        resp = client.get("/personnel/pers-A/welfare-trajectory", headers=_officer_headers())
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["trend"] in ("increasing", "decreasing", "stable", "insufficient_data")
        # only the one actually stored assessment appears; weeks stay missing
        assert len(body["history"]) == 1
        assert body["history"][0]["assessed_at"]

    def test_no_history_means_no_fabricated_trend_or_warning(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_mild_window("pers-A")
        body = client.get("/personnel/pers-A/welfare-trajectory", headers=_officer_headers()).json()
        assert body["history"] == []
        assert body["trend"] == "insufficient_data"
        assert body["early_warning"]["status"] == "not_available"


# ===================================================================
# 6. Causal no-future-leakage cut-off
# ===================================================================


class TestNoFutureLeakage:
    def test_future_dated_stored_assessment_is_excluded(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_full_window("pers-A")  # current: High 0.490

        # Older evidence: High, easing toward the current 0.49.
        _seed_assessment("pers-A", "older", _utc(2026, 1, 1), "High", 0.85, 0.85)
        # Future-dated record (stamped after the current run) that would
        # collapse the High-class signal to ~0 if it were (wrongly) included.
        _seed_assessment("pers-A", "future", _utc(2099, 1, 1), "Low", 0.95, 0.001)

        body = client.get("/personnel/pers-A/welfare-trajectory", headers=_officer_headers()).json()
        # future record must be cut off: the trend stays easing High->High
        assert body["trend"] == "decreasing"
        assert body["early_warning"]["status"] == "human_review"
        assert len(body["history"]) == 1
        assert body["history"][0]["predicted_band"] == "High"
        assert "2099" not in json.dumps(body)
        assert _parse(body["history"][0]["assessed_at"]) <= _parse(body["prediction"]["assessed_at"])

    def test_history_is_capped_at_newest_20(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_full_window("pers-A")  # current: High 0.49
        for index in range(22):
            high_prob = 0.05 + 0.01 * index
            _seed_assessment("pers-A", f"h{index}", _utc(2026, 1, 1) + index * WEEK, "Low",
                             0.99, high_prob)

        body = client.get("/personnel/pers-A/welfare-trajectory", headers=_officer_headers()).json()
        assert len(body["history"]) == 20
        # newest retained history still rises toward the current High point
        assert body["trend"] == "increasing"


# ===================================================================
# 7. Deterministic output
# ===================================================================


class TestDeterministicOutput:
    def test_repeated_calls_are_deterministic_on_signal(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_full_window("pers-A")
        _seed_assessment("pers-A", "old", _utc(2026, 1, 1), "Low", 0.90, 0.05)

        first = client.get("/personnel/pers-A/welfare-trajectory", headers=_officer_headers()).json()
        second = client.get("/personnel/pers-A/welfare-trajectory", headers=_officer_headers()).json()

        assert first["trend"] == second["trend"]
        assert first["early_warning"] == second["early_warning"]
        assert first["history"] == second["history"]
        assert first["prediction"]["predicted_band"] == second["prediction"]["predicted_band"]
        assert first["prediction"]["risk_probability"] == second["prediction"]["risk_probability"]
        # only the run timestamps are fresh
        assert first["assessed_at"] != second["assessed_at"]
        assert first["prediction"]["assessed_at"] != second["prediction"]["assessed_at"]


# ===================================================================
# 8. RBAC + personnel isolation
# ===================================================================


class TestRbacAndPersonnelIsolation:
    def test_welfare_officer_is_authorized(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_full_window("pers-A")
        resp = client.get("/personnel/pers-A/welfare-trajectory", headers=_officer_headers())
        assert resp.status_code == 200

    def test_personnel_cannot_request_another_persons_trajectory(self, client, inference_engine):
        _seed_user(client, "pers-A", "persona", "PERSONNEL")
        _seed_user(client, "pers-B", "personb", "PERSONNEL")
        _seed_full_window("pers-B")
        _seed_assessment("pers-B", "secret", _utc(2026, 1, 1), "High", 0.85, 0.85)

        resp = client.get("/personnel/pers-B/welfare-trajectory",
                          headers=_headers("pers-A", "persona", "PERSONNEL"))
        assert resp.status_code == 403
        blob = resp.text
        for forbidden in ("pers-B", "secret", "High", "trajectory", "increasing"):
            assert forbidden not in blob, f"leaked {forbidden}"

    def test_personnel_cannot_request_own_trajectory(self, client, inference_engine):
        _seed_user(client, "pers-A", "persona", "PERSONNEL")
        _seed_full_window("pers-A")
        resp = client.get("/personnel/pers-A/welfare-trajectory",
                          headers=_headers("pers-A", "persona", "PERSONNEL"))
        assert resp.status_code == 403
        assert "trend" not in resp.text

    def test_commander_is_blocked_aggregate_only(self, client, inference_engine):
        _seed_user(client, "cmd-1", "cmdr", "COMMANDER")
        _seed_full_window("pers-A")
        resp = client.get("/personnel/pers-A/welfare-trajectory",
                          headers=_headers("cmd-1", "cmdr", "COMMANDER"))
        assert resp.status_code == 403
        assert "pers-A" not in resp.text

    def test_unauthenticated_is_blocked(self, client, inference_engine):
        resp = client.get("/personnel/pers-A/welfare-trajectory")
        assert resp.status_code in (401, 403)

    def test_service_rejects_non_officer_direct_calls(self, client, inference_engine):
        _require_engine(inference_engine)
        from lib.history import HistoryAccessError
        from lib.trajectory import build_personnel_trajectory
        for role in ("PERSONNEL", "COMMANDER"):
            with pytest.raises(HistoryAccessError):
                await_result(build_personnel_trajectory(
                    "pers-A", {"user_id": "u", "role": role}, inference_engine
                ))
        with pytest.raises(HistoryAccessError):
            await_result(build_personnel_trajectory("pers-A", None, inference_engine))


# ===================================================================
# 9. No 44-vector / model / class-probability exposure
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
    )
    FORBIDDEN_KEYS = ("features",)
    ENGINEERED_NAME_TOKENS = ("__roll4_mean", "__delta_wow", "__was_missing")
    ALSO_HIDDEN_KEYS = ("class_probabilities", "confidence_basis", "data_trust")

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
        for token in self.FORBIDDEN_KEYS + self.ENGINEERED_NAME_TOKENS + self.ALSO_HIDDEN_KEYS:
            assert token not in keys, f"internal key '{token}' leaked"
        assert "features" not in blob

    def test_success_response_exposes_no_vector_or_model_internals(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_full_window("pers-A")
        _seed_assessment("pers-A", "old", _utc(2026, 1, 1), "Low", 0.90, 0.05)

        resp = client.get("/personnel/pers-A/welfare-trajectory", headers=_officer_headers())
        assert resp.status_code == 200, resp.text
        self._assert_no_vector_or_internals(resp.json())

    def test_denied_responses_expose_no_trajectory_material(self, client, inference_engine):
        _seed_user(client, "pers-A", "persona", "PERSONNEL")
        _seed_full_window("pers-X")
        _seed_assessment("pers-X", "secret", _utc(2026, 1, 1), "High", 0.85, 0.85)
        resp = client.get("/personnel/pers-X/welfare-trajectory",
                          headers=_headers("pers-A", "persona", "PERSONNEL"))
        assert resp.status_code == 403
        for forbidden in self.FORBIDDEN_BODY_TOKENS + ("pers-X", "High", "increasing"):
            assert forbidden not in resp.text, f"leaked forbidden token {forbidden}"


# ===================================================================
# 10. Model error handling (sanitized 503)
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


class TestModelErrorHandling:
    def test_endpoint_returns_sanitized_503_on_broken_artifacts(self, client, inference_engine, monkeypatch):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_full_window("pers-A")

        import routers.welfare as rw
        monkeypatch.setattr(rw, "engine", _BrokenEngine())

        resp = client.get("/personnel/pers-A/welfare-trajectory", headers=_officer_headers())
        assert resp.status_code == 503
        assert "risk_model.pkl" not in resp.text
        assert "risk_model" not in resp.text

    def test_endpoint_returns_sanitized_503_when_inference_fails(self, client, inference_engine, monkeypatch):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_full_window("pers-A")

        import routers.welfare as rw
        monkeypatch.setattr(rw, "engine", _RaisingEngine())

        resp = client.get("/personnel/pers-A/welfare-trajectory", headers=_officer_headers())
        assert resp.status_code == 503
        assert "inference explosion" not in resp.text
        assert ".pkl" not in resp.text


# ===================================================================
# 11. Regression protection (Phase 4C and earlier APIs)
# ===================================================================


class TestRegressionExistingApis:
    def test_welfare_prediction_endpoint_still_works(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_full_window("pers-A")
        resp = client.get("/personnel/pers-A/welfare-prediction", headers=_officer_headers())
        assert resp.status_code == 200, resp.text
        assert resp.json()["predicted_band"] in ("Low", "Moderate", "High")

    def test_raw_window_endpoint_still_works(self, client, inference_engine):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_full_window("pers-A")
        resp = client.get("/personnel/pers-A/raw-window", headers=_officer_headers())
        assert resp.status_code == 200, resp.text
        assert len(resp.json()["raw_records"]) == 4

    def test_history_endpoint_still_works(self, client, inference_engine):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_full_window("pers-A")
        resp = client.get("/personnel/pers-A/history", headers=_officer_headers())
        assert resp.status_code == 200, resp.text
        assert resp.json()["personnel_id"] == "pers-A"

    def test_predict_endpoint_model_backed_regression(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_full_window("pers-A")
        window = client.get("/personnel/pers-A/raw-window", headers=_officer_headers()).json()
        resp = client.post(
            "/predict",
            json={"personnel_id": "pers-A", "raw_records": window["raw_records"]},
            headers=_officer_headers(),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["predicted_band"] in ("Low", "Moderate", "High")


# ===================================================================
# 12. Module entry-point contract
# ===================================================================


def test_service_exports_expected_entry_points():
    import lib.trajectory as trajectory
    assert callable(trajectory.classify_trajectory)
    assert callable(trajectory.build_early_warning)
    assert callable(trajectory.build_personnel_trajectory)
    assert trajectory.PREDICTION_EPSILON == 1e-9
    assert trajectory.MAX_HISTORY_POINTS == 20