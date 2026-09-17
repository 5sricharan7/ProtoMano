"""Task 4C — Production welfare prediction integration tests.

Hermetic harness (same pattern as the 4A/4B/3B/3C suites): real routers +
auth/RBAC dependencies over an in-memory fake Mongo via FastAPI TestClient,
plus direct service-level calls.  No live MongoDB or backend process required.

The locked inference engine is the real ``InferenceEngine`` over the repo
artifacts, so the full MongoDB -> 4-week raw window -> canonical 44-feature
engineering -> calibrated LightGBM prediction path runs genuinely in-process;
these tests are skipped only when the model artifacts are absent.

Covers:
- successful production prediction (full integration flow)
- exact 44-feature compatibility in model-metadata order
- 4-week window -> feature engineering -> model integration
- missing/incomplete data -> safe structured envelope (never fabricated)
- no future / out-of-window / cross-personnel leakage into the prediction
- personnel isolation, RBAC enforcement (WELFARE_OFFICER / PERSONNEL / COMMANDER)
- no 44-vector exposure, no model/path exposure
- model/inference error handling (sanitized 503, re-raised artifact error)
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

RAW_NUMERIC_FIELDS = [
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
]


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
    """Pin the module-level router engine to a freshly loaded real engine.

    Falls back to a broken engine (or module default) when artifacts are
    absent; success-path tests then skip via :func:`_require_engine`.
    """
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
    """Seed an exact 4-week history ending at 2026-02-22."""
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


# ===================================================================
# 1. Successful production prediction (full integration flow)
# ===================================================================


class TestSuccessfulProductionPrediction:
    def test_officer_gets_model_backed_prediction(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_full_window("pers-A")

        resp = client.get("/personnel/pers-A/welfare-prediction", headers=_officer_headers())
        assert resp.status_code == 200, resp.text
        body = resp.json()

        assert body["personnel_id"] == "pers-A"
        assert body["predicted_band"] in ("Low", "Moderate", "High")
        assert 0.0 <= body["risk_probability"] <= 1.0
        assert 0.0 <= body["prediction_confidence"] <= 1.0
        total = sum(item["probability"] for item in body["class_probabilities"])
        assert abs(total - 1.0) < 1e-6
        assert body["model_version"]
        assert body["feature_version"]

        # window metadata faithfully reports the stored data basis
        assert body["data_sufficiency"]["week_count"] == 4
        assert body["data_sufficiency"]["weeks_with_data"] == [0, 1, 2, 3]
        assert _parse(body["data_sufficiency"]["latest_observation_date"]) == _utc(2026, 2, 22)

        assert body["data_trust"]["score"] >= 0
        assert body["decision_support"]["state"] in ("REVIEW_RECOMMENDED", "MONITOR", "VERIFY_DATA")
        assert body["welfare_recommendations"]

    def test_repeated_predictions_are_deterministic(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_full_window("pers-A")

        first = client.get("/personnel/pers-A/welfare-prediction", headers=_officer_headers()).json()
        second = client.get("/personnel/pers-A/welfare-prediction", headers=_officer_headers()).json()
        # assessed_at is a fresh timestamp; the model-derived signal must be stable
        assert first["predicted_band"] == second["predicted_band"]
        assert first["risk_probability"] == second["risk_probability"]
        assert first["prediction_confidence"] == second["prediction_confidence"]


# ===================================================================
# 2. Exact 44-feature compatibility (service level)
# ===================================================================


class TestExactFortyFourFeatureCompatibility:
    def test_service_features_are_44_in_metadata_order(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        from lib.db import db
        _seed_full_window("pers-A")

        from lib.feature_engineering import FEATURE_COUNT, features_for_latest_week, get_feature_columns, records_to_frame
        from lib.welfare_prediction import predict_personnel_welfare

        window, _, features = await_result(predict_personnel_welfare(
            "pers-A", {"user_id": "wo-1", "role": "WELFARE_OFFICER"}, inference_engine
        ))

        assert len(features) == FEATURE_COUNT == 44
        assert list(features) == inference_engine.feature_names
        assert list(features) == get_feature_columns()
        meta_order = json.loads((ARTIFACT_DIR / "model_metadata.json").read_text(encoding="utf-8"))
        assert list(features) == meta_order["feature_list_in_order"]

        # the features the endpoint trusted are exactly what the pipeline derives
        frame = records_to_frame(window["raw_records"])
        latest = features_for_latest_week(frame)
        assert latest.shape == (1, 1 + FEATURE_COUNT)
        for name in get_feature_columns():
            assert float(latest[name].iloc[0]) == features[name]

        del db


# ===================================================================
# 3. 4-week window -> feature engineering -> model integration
# ===================================================================


class TestWindowFeatureModelIntegration:
    def test_service_matches_direct_window_plus_inference(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        from lib.db import db
        _seed_full_window("pers-A")

        from lib.history import build_four_week_window
        from lib.welfare_prediction import predict_personnel_welfare

        direct_window = await_result(build_four_week_window(
            "pers-A", {"user_id": "wo-1", "role": "WELFARE_OFFICER"}
        ))
        # predict_from_raw_records is synchronous (feature engineering + model)
        direct_result, _ = inference_engine.predict_from_raw_records(
            direct_window["raw_records"], personnel_id="pers-A"
        )

        _, service_result, _ = await_result(predict_personnel_welfare(
            "pers-A", {"user_id": "wo-1", "role": "WELFARE_OFFICER"}, inference_engine
        ))

        assert service_result["predicted_band"] == direct_result["predicted_band"]
        assert service_result["risk_probability"] == direct_result["risk_probability"]
        assert service_result["class_probabilities"] == direct_result["class_probabilities"]
        assert service_result["prediction_confidence"] == direct_result["prediction_confidence"]

        del db


# ===================================================================
# 4. Missing / incomplete data
# ===================================================================


class TestMissingAndIncompleteData:
    def test_no_observations_returns_safe_envelope(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A", extra={**STATIC_FIELDS})

        resp = client.get("/personnel/pers-A/welfare-prediction", headers=_officer_headers())
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "insufficient_data"
        assert body["personnel_id"] == "pers-A"
        assert body["reason"] == "no_welfare_history"
        assert "predicted_band" not in body
        assert "risk_probability" not in body
        assert "features" not in json.dumps(body)

    def test_unrecoverable_static_fields_return_safe_envelope(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        # personnel carries NO static feature fields anywhere
        _seed_personnel("pers-A")
        _seed_record("pers-A", "wellness_logs", "x", _utc(2026, 2, 22),
                     payload_extra={"weekly_duty_hours": 66})

        resp = client.get("/personnel/pers-A/welfare-prediction", headers=_officer_headers())
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "insufficient_data"
        assert body["reason"] == "insufficient_data"
        assert "predicted_band" not in body

    def test_sparse_data_still_predicts_with_data_sufficiency(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A", extra={**STATIC_FIELDS})
        _seed_record("pers-A", "wellness_logs", "only", _utc(2026, 2, 22),
                     payload_extra={"weekly_duty_hours": 66})

        resp = client.get("/personnel/pers-A/welfare-prediction", headers=_officer_headers())
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["predicted_band"] in ("Low", "Moderate", "High")
        assert body["data_sufficiency"]["week_count"] == 1
        assert body["data_sufficiency"]["weeks_with_data"] == [3]
        # sparse inputs cannot fabricate a perfect data quality story
        assert 0.0 <= body["data_trust"]["score"] <= 100.0

    def test_service_raises_unavailable_for_ghost_personnel(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")

        from lib.welfare_prediction import WelfarePredictionUnavailable, predict_personnel_welfare
        with pytest.raises(WelfarePredictionUnavailable):
            await_result(predict_personnel_welfare(
                "ghost-id", {"user_id": "wo-1", "role": "WELFARE_OFFICER"}, inference_engine
            ))


# ===================================================================
# 5. No future / cross-personnel leakage
# ===================================================================


def _prediction_signal(client, headers) -> tuple[str, float]:
    body = client.get("/personnel/pers-A/welfare-prediction", headers=headers).json()
    return body["predicted_band"], body["risk_probability"]


class TestNoFutureOrCrossPersonnelLeakage:
    def test_out_of_window_records_do_not_change_prediction(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_full_window("pers-A")

        baseline = _prediction_signal(client, _officer_headers())

        # a record older than the 28-day window with an extreme value
        _seed_record("pers-A", "workload_records", "stale", _utc(2026, 2, 22) - 4 * WEEK,
                     payload_extra={"weekly_duty_hours": 999, "overtime_hours": 777})

        after = client.get("/personnel/pers-A/welfare-prediction", headers=_officer_headers())
        assert after.status_code == 200
        assert "999" not in after.text and "777" not in after.text
        band, prob = after.json()["predicted_band"], after.json()["risk_probability"]
        assert (band, prob) == baseline

    def test_other_personnel_records_never_leak_into_prediction(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A", extra={**STATIC_FIELDS})
        _seed_personnel("pers-B", extra={**STATIC_FIELDS})
        anchor = _utc(2026, 2, 22)
        _seed_record("pers-A", "wellness_logs", "own", anchor,
                     payload_extra={"weekly_duty_hours": 40})

        baseline = _prediction_signal(client, _officer_headers())

        # pers-B records share the same collections; one is even later and extreme
        _seed_record("pers-B", "wellness_logs", "b-secret", anchor,
                     payload_extra={"weekly_duty_hours": 999})
        _seed_record("pers-B", "workload_records", "b-late", anchor + datetime.timedelta(days=10),
                     payload_extra={"overtime_hours": 777})

        after = client.get("/personnel/pers-A/welfare-prediction", headers=_officer_headers())
        assert after.status_code == 200
        assert "999" not in after.text and "777" not in after.text
        band, prob = after.json()["predicted_band"], after.json()["risk_probability"]
        assert (band, prob) == baseline

    def test_anchor_is_latest_observation_not_wall_clock(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A", extra={**STATIC_FIELDS})
        future = _utc(2031, 1, 15, 9)
        _seed_record("pers-A", "wellness_logs", "future-latest", future,
                     payload_extra={"weekly_duty_hours": 50})
        _seed_record("pers-A", "workload_records", "future-old", future - datetime.timedelta(days=25),
                     payload_extra={"overtime_hours": 4})

        body = client.get("/personnel/pers-A/welfare-prediction", headers=_officer_headers()).json()
        assert _parse(body["data_sufficiency"]["latest_observation_date"]) == future
        assert body["predicted_band"] in ("Low", "Moderate", "High")
        assert body["data_sufficiency"]["week_count"] == 2


# ===================================================================
# 6. Personnel isolation + RBAC enforcement
# ===================================================================


class TestRbacAndPersonnelIsolation:
    def test_welfare_officer_is_authorized(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_full_window("pers-A")
        resp = client.get("/personnel/pers-A/welfare-prediction", headers=_officer_headers())
        assert resp.status_code == 200

    def test_personnel_cannot_request_another_persons_prediction(self, client, inference_engine):
        _seed_user(client, "pers-A", "persona", "PERSONNEL")
        _seed_user(client, "pers-B", "personb", "PERSONNEL")
        _seed_personnel("pers-B", extra={**STATIC_FIELDS})
        _seed_record("pers-B", "wellness_logs", "B-secret", _utc(2026, 2, 22),
                     payload_extra={"weekly_duty_hours": 66})

        resp = client.get("/personnel/pers-B/welfare-prediction",
                          headers=_headers("pers-A", "persona", "PERSONNEL"))
        assert resp.status_code == 403
        blob = resp.text
        assert "B-secret" not in blob and "pers-B" not in blob

    def test_personnel_cannot_request_their_own_prediction(self, client, inference_engine):
        _seed_user(client, "pers-A", "persona", "PERSONNEL")
        _seed_personnel("pers-A", extra={**STATIC_FIELDS})
        _seed_record("pers-A", "wellness_logs", "own", _utc(2026, 2, 22),
                     payload_extra={"weekly_duty_hours": 66})
        resp = client.get("/personnel/pers-A/welfare-prediction",
                          headers=_headers("pers-A", "persona", "PERSONNEL"))
        assert resp.status_code == 403
        assert "predicted_band" not in resp.text

    def test_commander_is_blocked_aggregate_only(self, client, inference_engine):
        _seed_user(client, "cmd-1", "cmdr", "COMMANDER")
        _seed_personnel("pers-A", extra={**STATIC_FIELDS})
        _seed_record("pers-A", "wellness_logs", "x", _utc(2026, 2, 22),
                     payload_extra={"weekly_duty_hours": 66})
        resp = client.get("/personnel/pers-A/welfare-prediction", headers=_headers("cmd-1", "cmdr", "COMMANDER"))
        assert resp.status_code == 403
        assert "pers-A" not in resp.text

    def test_unauthenticated_is_blocked(self, client, inference_engine):
        resp = client.get("/personnel/pers-A/welfare-prediction")
        assert resp.status_code in (401, 403)

    def test_service_rejects_non_officer_direct_calls(self, client, inference_engine):
        _require_engine(inference_engine)
        from lib.history import HistoryAccessError
        from lib.welfare_prediction import predict_personnel_welfare
        for role in ("PERSONNEL", "COMMANDER"):
            with pytest.raises(HistoryAccessError):
                await_result(predict_personnel_welfare(
                    "pers-A", {"user_id": "u", "role": role}, inference_engine
                ))
        with pytest.raises(HistoryAccessError):
            await_result(predict_personnel_welfare("pers-A", None, inference_engine))


# ===================================================================
# 7. No 44-vector / model / path exposure
# ===================================================================


class TestNoVectorOrModelExposure:
    # Model/path/credential tokens that must never appear anywhere in a response.
    # (``confidence_basis`` is a deliberate officer-facing explanation field in
    # the success envelope, consistent with the existing PredictionResponse, and
    # is therefore asserted absent only in the unavailable envelope below.)
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

    # A 44-feature vector is a mapping whose keys are the engineered feature
    # names (e.g. ``weekly_duty_hours__roll4_mean``) or whose key is ``features``.
    # Contribution explanations reuse the PUBLIC metadata feature names under a
    # ``feature`` key, which is not the vector.
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

    def test_success_response_exposes_no_vector_or_model_internals(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_full_window("pers-A")

        resp = client.get("/personnel/pers-A/welfare-prediction", headers=_officer_headers())
        assert resp.status_code == 200, resp.text
        self._assert_no_vector_or_internals(resp.json())

    def test_unavailable_envelope_exposes_nothing(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A", extra={**STATIC_FIELDS})

        resp = client.get("/personnel/pers-A/welfare-prediction", headers=_officer_headers())
        assert resp.status_code == 200
        body = resp.json()
        self._assert_no_vector_or_internals(body)
        for forbidden in ("predicted_band", "risk_probability", "confidence_basis"):
            assert forbidden not in json.dumps(body), f"guessed risk material leaked {forbidden}"

    def test_denied_responses_expose_no_prediction_material(self, client, inference_engine):
        _seed_user(client, "pers-A", "persona", "PERSONNEL")
        _seed_personnel("pers-X", extra={**STATIC_FIELDS})
        _seed_record("pers-X", "wellness_logs", "secret", _utc(2026, 2, 22),
                     payload_extra={"weekly_duty_hours": 66})
        resp = client.get("/personnel/pers-X/welfare-prediction",
                          headers=_headers("pers-A", "persona", "PERSONNEL"))
        assert resp.status_code == 403
        for forbidden in self.FORBIDDEN_BODY_TOKENS + ("66", "pers-X"):
            assert forbidden not in resp.text, f"leaked forbidden token {forbidden}"


# ===================================================================
# 8. Model / inference error handling
# ===================================================================


class _BrokenEngine:
    """Fake inference surface that reports a load failure."""

    load_error = "Missing model artifacts: risk_model.pkl, baseline_model.pkl"
    risk_model = None
    preprocessing_pipeline = None


class _RaisingEngine:
    """Fake inference surface that loads but raises during prediction."""

    load_error = None
    risk_model = object()
    preprocessing_pipeline = object()

    def predict_from_raw_records(self, *args, **kwargs):
        from lib.inference import ModelArtifactError
        raise ModelArtifactError("inference explosion")


class TestModelAndInferenceErrorHandling:
    def test_endpoint_returns_sanitized_503_on_broken_artifacts(self, client, inference_engine, monkeypatch):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_full_window("pers-A")

        import routers.welfare as rw
        monkeypatch.setattr(rw, "engine", _BrokenEngine())

        resp = client.get("/personnel/pers-A/welfare-prediction", headers=_officer_headers())
        assert resp.status_code == 503
        assert "risk_model.pkl" not in resp.text
        assert "risk_model" not in resp.text
        assert "baseline_model.pkl" not in resp.text

    def test_endpoint_returns_sanitized_503_when_inference_fails(self, client, inference_engine, monkeypatch):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_full_window("pers-A")

        import routers.welfare as rw
        monkeypatch.setattr(rw, "engine", _RaisingEngine())

        resp = client.get("/personnel/pers-A/welfare-prediction", headers=_officer_headers())
        assert resp.status_code == 503
        assert "inference explosion" not in resp.text
        assert ".pkl" not in resp.text

    def test_service_re_raises_model_artifact_error(self, client, inference_engine):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_full_window("pers-A")

        from lib.inference import ModelArtifactError
        from lib.welfare_prediction import predict_personnel_welfare
        with pytest.raises(ModelArtifactError):
            await_result(predict_personnel_welfare(
                "pers-A", {"user_id": "wo-1", "role": "WELFARE_OFFICER"}, _RaisingEngine()
            ))
        with pytest.raises(ModelArtifactError):
            await_result(predict_personnel_welfare(
                "pers-A", {"user_id": "wo-1", "role": "WELFARE_OFFICER"}, None
            ))


# ===================================================================
# 9. Regression protection for existing APIs
# ===================================================================


class TestRegressionExistingApis:
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

    def test_overview_and_model_info_still_work(self, client, inference_engine):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        resp = client.get("/overview", headers=_officer_headers())
        assert resp.status_code == 200, resp.text
        info = client.get("/model-info")
        assert info.status_code == 200, info.text
        assert info.json()["feature_count"] == 44

    def test_predict_endpoint_validation_regression(self, client, inference_engine):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        resp = client.post("/predict", json={"personnel_id": "pers-A"}, headers=_officer_headers())
        assert resp.status_code == 422
        assert "raw_records" in resp.text

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
# 10. Module entry-point contract
# ===================================================================


def test_service_exports_expected_entry_points():
    from lib.welfare_prediction import WelfarePredictionUnavailable, predict_personnel_welfare
    assert callable(predict_personnel_welfare)
    assert issubclass(WelfarePredictionUnavailable, ValueError)
    exc = WelfarePredictionUnavailable("insufficient_data", "some message")
    assert exc.reason == "insufficient_data"
    assert exc.message == "some message"