"""Task 4E — Explainable welfare AI integration tests.

Hermetic harness (same pattern as the 4A/4B/4C/4D/3B/3C suites): real routers +
auth/RBAC dependencies over an in-memory fake Mongo via FastAPI TestClient,
plus direct service-level calls.  No live MongoDB or backend process required.

The locked inference engine is the real ``InferenceEngine`` over the repo
artifacts, so the full MongoDB -> 4-week raw window -> canonical 44-feature
engineering -> calibrated LightGBM prediction -> explanation path runs genuinely
in-process; success-path tests are skipped only when the model artifacts are
absent.

Covers:
- successful explanation envelope (status, prediction summary, factors, What Changed)
- correct factor ordering/names from the model's metadata feature order
- top contributing factors + contribution direction/impact summaries
- What Changed? over a stored prior snapshot and over the window prior week
- stable / no meaningful change inside the materiality threshold
- missing data is never reported as improvement or deterioration
- insufficient temporal evidence -> structured insufficient-data result
- causal no-future-leakage cut-off for future-dated stored snapshots
- deterministic repeated output
- SHAP availability probe + documented native fallback (never claims SHAP)
- explanation-unavailable path (no per-factor contributions for the artifact)
- model/artifact failure handling (sanitized 503, no traceback leak)
- RBAC enforcement (WELFARE_OFFICER / PERSONNEL / COMMANDER) + personnel isolation
- no 44-vector exposure, no model/path/credential exposure
- Phase 4C and Phase 4D regression protection
"""

from __future__ import annotations

import asyncio
import datetime
import json
import os
import sys
import types
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


def _seed_single_week(personnel_id: str = "pers-A"):
    """Single observation only -> prediction works but What Changed cannot."""
    _seed_personnel(personnel_id, extra={**STATIC_FIELDS})
    _seed_record(personnel_id, "wellness_logs", "only", _utc(2026, 2, 22),
                 payload_extra={"weekly_duty_hours": 66, "wellness_score_self_report": 3.5})


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


# ===================================================================
# 1. Successful explanation envelope
# ===================================================================


class TestSuccessfulExplanation:
    def test_officer_gets_explanation_envelope(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_full_window("pers-A")

        resp = client.get("/personnel/pers-A/welfare-explanation", headers=_officer_headers())
        assert resp.status_code == 200, resp.text
        body = resp.json()

        assert body["personnel_id"] == "pers-A"
        assert body["explanation_status"] == "available"
        assert body["status_message"]
        assert body["prediction"]["predicted_band"] in ("Low", "Moderate", "High")
        assert 0.0 <= body["prediction"]["risk_probability"] <= 1.0
        assert body["explanation_method"] == "native_feature_contributions"
        assert body["top_contributing_factors"]
        assert body["what_changed"]["status"] in ("available", "insufficient_data")
        assert body["evidence_basis"]
        assert body["derived_outputs"]
        assert _parse(body["assessed_at"])

    def test_top_factors_use_model_feature_names_in_metadata_order(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_full_window("pers-A")

        body = client.get("/personnel/pers-A/welfare-explanation", headers=_officer_headers()).json()
        metadata_names = set(inference_engine.feature_names)
        factors = body["top_contributing_factors"]
        assert 0 < len(factors) <= 5
        seen = set()
        contributions = []
        for factor in factors:
            assert factor["feature"] in metadata_names, f"unknown factor {factor['feature']}"
            assert factor["direction"] in ("increases", "decreases", "neutral")
            assert factor["impact_summary"]
            assert isinstance(factor["display_name"], str) and factor["display_name"]
            assert "__" not in factor["display_name"]
            assert factor["feature"] not in seen  # no duplicates
            seen.add(factor["feature"])
            contributions.append(factor["contribution"])
        # ranked by absolute contribution magnitude, descending
        magnitudes = [abs(value) for value in contributions]
        assert magnitudes == sorted(magnitudes, reverse=True)

    def test_top_factors_are_identical_to_4c_native_contributions(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_full_window("pers-A")

        prediction = client.get("/personnel/pers-A/welfare-prediction", headers=_officer_headers()).json()
        expected = {item["feature"] for item in prediction["top_contributing_factors"]}

        body = client.get("/personnel/pers-A/welfare-explanation", headers=_officer_headers()).json()
        assert {item["feature"] for item in body["top_contributing_factors"]} == expected

    def test_explanation_is_decision_support_not_diagnosis(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_full_window("pers-A")

        body = client.get("/personnel/pers-A/welfare-explanation", headers=_officer_headers()).json()
        joined = " ".join(body["derived_outputs"]).lower()
        assert "not a diagnosis" in joined or "decision-support" in joined
        blob = json.dumps(body).lower()
        for token in ("diagnosed", "diagnosis of", "suffers from"):
            assert token not in blob


# ===================================================================
# 2. What Changed? scenarios
# ===================================================================


class TestWhatChanged:
    def _seed_prior_snapshot(self, personnel_id: str, engine):
        """Seed a stored prior snapshot where weekly_duty_hours was 40."""
        features = _current_features(personnel_id, engine)
        prior = dict(features)
        prior["weekly_duty_hours"] = 40.0
        prior["weekly_duty_hours__was_missing"] = 0
        _seed_stored_assessment(personnel_id, "prior", NOW - datetime.timedelta(days=30), features=prior)
        return features

    def test_reports_meaningful_changes_from_prior_snapshot(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_full_window("pers-A")
        self._seed_prior_snapshot("pers-A", inference_engine)

        body = client.get("/personnel/pers-A/welfare-explanation", headers=_officer_headers()).json()
        wc = body["what_changed"]
        assert wc["status"] == "available"
        assert wc["comparison"] == "prior_assessment"
        assert not wc["no_material_change"]
        duty = next(item for item in wc["changes"] if item["feature"] == "weekly_duty_hours")
        assert duty["change"] == "increased"
        assert abs(duty["delta"] - 26.0) < 1e-9
        assert duty["previous"] == 40.0
        assert duty["current"] > 40.0
        assert duty["impact"] in ("increases_risk_signal", "decreases_risk_signal", "unknown")

    def test_what_changed_is_ranked_by_magnitude(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_full_window("pers-A")
        features = _current_features("pers-A", inference_engine)
        prior = dict(features)
        prior["weekly_duty_hours"] = 40.0
        prior["weekly_duty_hours__roll4_mean"] = features["weekly_duty_hours__roll4_mean"] - 9.0
        old = NOW - datetime.timedelta(days=60)
        _seed_stored_assessment("pers-A", "a", old, features=prior)
        _seed_stored_assessment("pers-A", "b", NOW - datetime.timedelta(days=30), features={
            **prior, "wellness_score_self_report": features["wellness_score_self_report"] - 4.0,
        })

        wc = client.get("/personnel/pers-A/welfare-explanation", headers=_officer_headers()).json()["what_changed"]
        magnitudes = [abs(item["delta"]) for item in wc["changes"]]
        assert magnitudes == sorted(magnitudes, reverse=True)
        assert len(wc["changes"]) <= 5

    def test_stable_inputs_yield_no_material_change(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_full_window("pers-A")
        features = _current_features("pers-A", inference_engine)
        # prior snapshot identical to current -> no material change
        _seed_stored_assessment("pers-A", "same", NOW - datetime.timedelta(days=30), features=dict(features))

        wc = client.get("/personnel/pers-A/welfare-explanation", headers=_officer_headers()).json()["what_changed"]
        assert wc["status"] == "available"
        assert wc["no_material_change"] is True
        assert wc["changes"] == []
        assert "materiality" in wc["basis"]

    def test_missing_data_is_never_reported_as_change(self):
        from lib.explanation import build_change_items

        current = {
            "weekly_duty_hours": 66.0,
            "weekly_duty_hours__roll4_mean": 50.0,
            "weekly_duty_hours__delta_wow": 10.0,
            "weekly_duty_hours__was_missing": 0,
            "wellness_score_self_report": 3.5,
            "wellness_score_self_report__was_missing": 1,
            "years_of_service": 12.0,
        }
        prior = {
            "weekly_duty_hours": 40.0,
            "weekly_duty_hours__roll4_mean": 46.0,
            "weekly_duty_hours__delta_wow": 2.0,
            "weekly_duty_hours__was_missing": 0,
            "wellness_score_self_report": 8.0,
            "wellness_score_self_report__was_missing": 0,
            "years_of_service": 12.0,
        }
        items = build_change_items(current, prior, {"weekly_duty_hours": "increases"})
        reported = {item["feature"] for item in items}
        # observed in both -> reported; missing in current -> NEVER reported as change
        assert "weekly_duty_hours" in reported
        assert "wellness_score_self_report" not in reported
        assert "years_of_service" not in reported
        blob = json.dumps(items).lower()
        for token in ("improvement", "deterioration"):
            assert token not in blob

    def test_insufficient_temporal_evidence_returns_structured_result(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_single_week("pers-A")  # prediction possible, but only ONE observed week

        body = client.get("/personnel/pers-A/welfare-explanation", headers=_officer_headers()).json()
        assert body["explanation_status"] == "available"  # prediction + factors still available
        wc = body["what_changed"]
        assert wc["status"] == "insufficient_data"
        assert wc["changes"] == []
        assert not wc["no_material_change"]
        assert "no usable prior temporal evidence" in wc["basis"] or "No usable prior temporal evidence" in wc["basis"]

    def test_window_prior_week_fallback_when_no_stored_snapshot(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_full_window("pers-A")  # 4 observed weeks, NO stored assessments

        wc = client.get("/personnel/pers-A/welfare-explanation", headers=_officer_headers()).json()["what_changed"]
        assert wc["status"] == "available"
        assert wc["comparison"] == "prior_week"
        assert wc["changes"]
        duty = next(item for item in wc["changes"] if item["feature"] == "weekly_duty_hours")
        assert abs(duty["delta"] - 12.0) < 1e-9  # 54 -> 66 across the observed window

    def test_no_future_leakage_causal_cut_off(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_full_window("pers-A")
        features = _current_features("pers-A", inference_engine)

        # legitimate prior (observed weekly_duty_hours 40)
        prior = {**features, "weekly_duty_hours": 40.0, "weekly_duty_hours__was_missing": 0}
        _seed_stored_assessment("pers-A", "past", NOW - datetime.timedelta(days=30), features=prior)
        # future-dated snapshot with an extreme value that must NEVER be compared
        future = {**features, "weekly_duty_hours": 999.0, "weekly_duty_hours__was_missing": 0}
        _seed_stored_assessment("pers-A", "future", NOW + datetime.timedelta(days=4000), features=future)

        body = client.get("/personnel/pers-A/welfare-explanation", headers=_officer_headers())
        assert body.status_code == 200, body.text
        blob = body.text
        assert "999" not in blob
        wc = body.json()["what_changed"]
        assert wc["comparison"] == "prior_assessment"
        duty = next(item for item in wc["changes"] if item["feature"] == "weekly_duty_hours")
        assert duty["previous"] == 40.0

    def test_deterministic_output(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_full_window("pers-A")
        features = _current_features("pers-A", inference_engine)
        prior = {**features, "weekly_duty_hours": 40.0, "weekly_duty_hours__was_missing": 0}
        _seed_stored_assessment("pers-A", "prior", NOW - datetime.timedelta(days=30), features=prior)

        first = client.get("/personnel/pers-A/welfare-explanation", headers=_officer_headers()).json()
        second = client.get("/personnel/pers-A/welfare-explanation", headers=_officer_headers()).json()

        assert first["explanation_status"] == second["explanation_status"]
        assert first["prediction"] == second["prediction"]
        assert first["top_contributing_factors"] == second["top_contributing_factors"]
        assert first["what_changed"] == second["what_changed"]
        assert first["evidence_basis"] == second["evidence_basis"]
        assert first["assessed_at"] != second["assessed_at"]


# ===================================================================
# 3. SHAP availability / fallback behavior
# ===================================================================


class TestShapFallbackBehavior:
    def test_shap_is_not_claimed_or_used_in_current_runtime(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_full_window("pers-A")

        body = client.get("/personnel/pers-A/welfare-explanation", headers=_officer_headers()).json()
        assert body["explanation_method"] == "native_feature_contributions"
        assert "shap" not in json.dumps(body).lower()
        assert "approximate" not in json.dumps(body).lower()

    def test_shap_probe_reports_runtime_availability_structurally(self):
        from lib.explanation import shap_availability

        info = shap_availability()
        assert isinstance(info, dict)
        assert "available" in info and isinstance(info["available"], bool)
        assert "version" in info and (info["version"] is None or isinstance(info["version"], str))
        assert info["available"] is False  # shap is not part of the deployed runtime

    def test_fake_shap_import_never_changes_the_method(self, monkeypatch):
        fake = types.ModuleType("shap")
        fake.__version__ = "99.0.0"
        monkeypatch.setitem(sys.modules, "shap", fake)

        from lib.explanation import EXPLANATION_METHOD, _impact_summary, shap_availability

        assert shap_availability()["available"] is True
        # availability probe flipping true NEVER changes what the layer emits:
        # the artifact is a calibrated multiclass classifier and the runtime
        # attribution stays native; no SHAP claim is ever made.
        assert EXPLANATION_METHOD == "native_feature_contributions"
        assert "shap" not in _impact_summary("increases").lower()

    def test_documentation_marks_output_as_native_not_shap(self):
        from lib.explanation import EXPLANATION_METHOD

        assert EXPLANATION_METHOD == "native_feature_contributions"
        assert "shap" not in EXPLANATION_METHOD


# ===================================================================
# 4. Explanation unavailable / model failure handling
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


class TestExplanationAvailabilityAndFailure:
    def test_explanation_unavailable_when_contributions_missing(self, client, inference_engine, monkeypatch):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_full_window("pers-A")

        from lib import explanation as ex

        real_predict = ex.predict_personnel_welfare

        async def stripped_predict(personnel_id, user, engine):
            window, result, features = await real_predict(personnel_id, user, engine)
            return window, {**result, "top_contributing_factors": []}, features

        monkeypatch.setattr(ex, "predict_personnel_welfare", stripped_predict)

        resp = client.get("/personnel/pers-A/welfare-explanation", headers=_officer_headers())
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["explanation_status"] == "explanation_unavailable"
        assert body["top_contributing_factors"] == []
        assert body["prediction"]["predicted_band"] in ("Low", "Moderate", "High")
        assert "cannot be produced" in body["status_message"]

    def test_build_top_factors_returns_empty_for_factor_less_result(self):
        from lib.explanation import build_top_factors

        assert build_top_factors({"top_contributing_factors": []}) == []
        assert build_top_factors({}) == []
        assert build_top_factors({"top_contributing_factors": [
            {"feature": "weekly_duty_hours", "contribution": 0.5, "direction": "increases"},
        ]})[0]["feature"] == "weekly_duty_hours"

    def test_no_data_returns_structured_unavailable_envelope(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A", extra={**STATIC_FIELDS})  # no welfare records at all

        resp = client.get("/personnel/pers-A/welfare-explanation", headers=_officer_headers())
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "insufficient_data"
        assert body["personnel_id"] == "pers-A"
        assert body["reason"] == "no_welfare_history"
        assert "explanation_status" not in body
        assert "top_contributing_factors" not in body
        assert "features" not in json.dumps(body)

    def test_broken_artifacts_return_sanitized_503(self, client, inference_engine, monkeypatch):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_full_window("pers-A")

        import routers.welfare as rw
        monkeypatch.setattr(rw, "engine", _BrokenEngine())

        resp = client.get("/personnel/pers-A/welfare-explanation", headers=_officer_headers())
        assert resp.status_code == 503
        for forbidden in ("risk_model.pkl", "risk_model", "baseline_model.pkl", "Missing model artifacts"):
            assert forbidden not in resp.text, f"leaked {forbidden}"

    def test_inference_failure_returns_sanitized_503(self, client, inference_engine, monkeypatch):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_full_window("pers-A")

        import routers.welfare as rw
        monkeypatch.setattr(rw, "engine", _RaisingEngine())

        resp = client.get("/personnel/pers-A/welfare-explanation", headers=_officer_headers())
        assert resp.status_code == 503
        for forbidden in ("inference explosion", ".pkl", "Traceback", "File "):
            assert forbidden not in resp.text, f"leaked {forbidden}"

    def test_service_re_raises_model_artifact_error(self, client, inference_engine):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_full_window("pers-A")

        from lib.explanation import build_welfare_explanation
        from lib.inference import ModelArtifactError

        with pytest.raises(ModelArtifactError):
            await_result(build_welfare_explanation(
                "pers-A", {"user_id": "wo-1", "role": "WELFARE_OFFICER"}, _RaisingEngine()
            ))

    def test_service_rejects_non_officer_direct_calls(self, client, inference_engine):
        _require_engine(inference_engine)
        from lib.explanation import build_welfare_explanation
        from lib.history import HistoryAccessError

        for role in ("PERSONNEL", "COMMANDER"):
            with pytest.raises(HistoryAccessError):
                await_result(build_welfare_explanation(
                    "pers-A", {"user_id": "u", "role": role}, inference_engine
                ))
        with pytest.raises(HistoryAccessError):
            await_result(build_welfare_explanation("pers-A", None, inference_engine))


# ===================================================================
# 5. RBAC + personnel isolation
# ===================================================================


class TestRbacAndPersonnelIsolation:
    def test_welfare_officer_is_authorized(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_full_window("pers-A")
        resp = client.get("/personnel/pers-A/welfare-explanation", headers=_officer_headers())
        assert resp.status_code == 200

    def test_personnel_cannot_request_another_persons_explanation(self, client, inference_engine):
        _seed_user(client, "pers-A", "persona", "PERSONNEL")
        _seed_user(client, "pers-B", "personb", "PERSONNEL")
        _seed_full_window("pers-B")

        resp = client.get("/personnel/pers-B/welfare-explanation",
                          headers=_headers("pers-A", "persona", "PERSONNEL"))
        assert resp.status_code == 403
        blob = resp.text
        for forbidden in ("pers-B", "predicted_band", "risk_probability", "weekly_duty_hours"):
            assert forbidden not in blob, f"leaked {forbidden}"

    def test_personnel_cannot_request_own_explanation(self, client, inference_engine):
        _seed_user(client, "pers-A", "persona", "PERSONNEL")
        _seed_full_window("pers-A")
        resp = client.get("/personnel/pers-A/welfare-explanation",
                          headers=_headers("pers-A", "persona", "PERSONNEL"))
        assert resp.status_code == 403
        assert "explanation_status" not in resp.text

    def test_commander_is_blocked_aggregate_only(self, client, inference_engine):
        _seed_user(client, "cmd-1", "cmdr", "COMMANDER")
        _seed_full_window("pers-A")
        resp = client.get("/personnel/pers-A/welfare-explanation",
                          headers=_headers("cmd-1", "cmdr", "COMMANDER"))
        assert resp.status_code == 403
        assert "pers-A" not in resp.text

    def test_unauthenticated_is_blocked(self, client, inference_engine):
        resp = client.get("/personnel/pers-A/welfare-explanation")
        assert resp.status_code in (401, 403)


# ===================================================================
# 6. No 44-vector / model / path / credential exposure
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
    UNAVAILABLE_HIDDEN_KEYS = ("explanation_status", "top_contributing_factors", "what_changed")

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

    def test_success_response_exposes_no_vector_or_model_internals(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_full_window("pers-A")
        features = _current_features("pers-A", inference_engine)
        prior = {**features, "weekly_duty_hours": 40.0, "weekly_duty_hours__was_missing": 0}
        _seed_stored_assessment("pers-A", "prior", NOW - datetime.timedelta(days=30), features=prior)

        resp = client.get("/personnel/pers-A/welfare-explanation", headers=_officer_headers())
        assert resp.status_code == 200, resp.text
        self._assert_no_vector_or_internals(resp.json())

    def test_unavailable_envelope_exposes_nothing(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A", extra={**STATIC_FIELDS})

        body = client.get("/personnel/pers-A/welfare-explanation", headers=_officer_headers()).json()
        self._assert_no_vector_or_internals(body)
        for key in self.UNAVAILABLE_HIDDEN_KEYS:
            assert key not in json.dumps(body), f"guessed explanation material leaked {key}"

    def test_denied_responses_expose_no_explanation_material(self, client, inference_engine):
        _seed_user(client, "pers-A", "persona", "PERSONNEL")
        _seed_full_window("pers-X")
        resp = client.get("/personnel/pers-X/welfare-explanation",
                          headers=_headers("pers-A", "persona", "PERSONNEL"))
        assert resp.status_code == 403
        for forbidden in self.FORBIDDEN_BODY_TOKENS + ("pers-X", "66", "High"):
            assert forbidden not in resp.text, f"leaked forbidden token {forbidden}"

    def test_what_changed_values_never_expose_the_raw_snapshot(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_full_window("pers-A")
        features = _current_features("pers-A", inference_engine)
        prior = {**features, "weekly_duty_hours": 40.0, "weekly_duty_hours__was_missing": 0}
        _seed_stored_assessment("pers-A", "prior", NOW - datetime.timedelta(days=30), features=prior)

        body = client.get("/personnel/pers-A/welfare-explanation", headers=_officer_headers()).json()
        # only the top-N change summary is surfaced; the full 44-value snapshot never is
        assert len(body["what_changed"]["changes"]) <= 5
        for item in body["what_changed"]["changes"]:
            assert set(item) == {
                "feature", "display_name", "previous", "current", "delta",
                "change", "contribution_direction", "impact",
            }


# ===================================================================
# 7. Phase 4C + Phase 4D regression protection
# ===================================================================


class TestRegressionPhases4cAnd4d:
    def test_welfare_prediction_endpoint_still_works(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_full_window("pers-A")
        resp = client.get("/personnel/pers-A/welfare-prediction", headers=_officer_headers())
        assert resp.status_code == 200, resp.text
        assert resp.json()["predicted_band"] in ("Low", "Moderate", "High")

    def test_welfare_trajectory_endpoint_still_works(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_full_window("pers-A")
        _seed_stored_assessment("pers-A", "old", _utc(2026, 1, 1), band="Low", risk_probability=0.9)
        resp = client.get("/personnel/pers-A/welfare-trajectory", headers=_officer_headers())
        assert resp.status_code == 200, resp.text
        assert resp.json()["trend"] in ("increasing", "decreasing", "stable", "insufficient_data")

    def test_raw_window_endpoint_still_works(self, client, inference_engine):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_full_window("pers-A")
        resp = client.get("/personnel/pers-A/raw-window", headers=_officer_headers())
        assert resp.status_code == 200, resp.text
        assert len(resp.json()["raw_records"]) == 4

    def test_overview_and_model_info_still_work(self, client, inference_engine):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        resp = client.get("/overview", headers=_officer_headers())
        assert resp.status_code == 200, resp.text
        info = client.get("/model-info")
        assert info.status_code == 200, info.text
        assert info.json()["feature_count"] == 44

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
# 8. Module entry-point contract
# ===================================================================


def test_service_exports_expected_entry_points():
    import lib.explanation as explanation

    assert callable(explanation.build_welfare_explanation)
    assert callable(explanation.build_what_changed)
    assert callable(explanation.build_change_items)
    assert callable(explanation.shap_availability)
    assert callable(explanation.display_name)
    assert explanation.EXPLANATION_METHOD == "native_feature_contributions"
    assert explanation.CHANGE_MATERIALITY == 1e-6
    assert explanation.MAX_CHANGES == 5