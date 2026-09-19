"""Task 4B — Exact 4-week raw-record intelligence window tests.

Hermetic harness (same pattern as the 4A/3B/3C suites): real routers + auth/RBAC
dependencies over an in-memory fake Mongo via FastAPI TestClient, plus direct
service-level calls.  No live MongoDB or backend process is required.

Covers:
- normal 4-week history -> exactly four chronological raw records ending at
  the latest observation
- fewer than 4 weeks of available data (missing weeks stay missing)
- missing observations preserved as None (never fabricated)
- future / out-of-window record exclusion
- deterministic chronological ordering + static-field consistency
- deterministic duplicate handling (id de-dup, same-week merge)
- raw schema matches the feature-engineering contract exactly
- exact 44-feature compatibility in model-metadata order
- RBAC/IDOR protection (WELFARE_OFFICER / PERSONNEL / COMMANDER)
- no sensitive data exposure
"""

from __future__ import annotations

import datetime
import io
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


def _seed_assessment(user_id: str, assessment_id: str, assessed_at: datetime.datetime):
    from lib.db import db

    db.risk_assessments.docs.append({
        "id": assessment_id,
        "personnel_id": user_id,
        "assessed_at": assessed_at,
        "date_key": assessed_at.date().isoformat(),
        "is_latest": True,
        "features": {"weekly_duty_hours__roll4_mean": 40.0, "INTERNAL_FEATURE_MARKER": 1.0},
        "confidence_basis": "Maximum calibrated class probability from risk_model.pkl",
        "predicted_band": "High",
        "risk_probability": 0.9,
        "prediction_confidence": 0.9,
        "class_probabilities": [],
        "top_contributing_factors": [],
        "data_trust": {"score": 80.0, "threshold": 60.0, "label": "High", "basis": "x",
                       "components": {"completeness": 80.0, "recency": 100.0, "source_reliability": 85.0, "consistency": 75.0}},
        "decision_support": {"state": "MONITOR", "abstained": False, "basis": "y"},
        "model_version": "0.2.0-sih-final",
        "feature_version": "1.1.0",
    })


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


def _officer_headers():
    return _headers("wo-1", "welfareo", "WELFARE_OFFICER")


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
# 1. Normal 4-week history
# ===================================================================


class TestNormalFourWeekWindow:
    def test_officer_gets_exact_four_week_chronological_window(self, client):
        from lib.db import db
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_full_window()

        resp = client.get("/personnel/pers-A/raw-window", headers=_officer_headers())
        assert resp.status_code == 200, resp.text
        body = resp.json()

        assert body["personnel_id"] == "pers-A"
        assert body["personnel"]["id"] == "pers-A"

        records = body["raw_records"]
        assert len(records) == 4
        assert [r["week"] for r in records] == [0, 1, 2, 3]
        assert body["week_count"] == 4
        assert body["weeks_with_data"] == [0, 1, 2, 3]

        by_week = {r["week"]: r for r in records}
        assert by_week[3]["weekly_duty_hours"] == 66
        assert by_week[3]["wellness_score_self_report"] == 3.5
        assert by_week[2]["weekly_duty_hours"] == 54
        assert by_week[2]["overtime_hours"] == 9.4
        assert by_week[1]["leave_balance"] == 12
        assert by_week[0]["days_since_last_rest"] == 6

        # window bounds: week 0 oldest, week 3 = latest observation
        assert _parse(body["window_start"]) == _utc(2026, 2, 1)
        assert _parse(body["window_end"]) == _utc(2026, 2, 22)
        assert _parse(body["latest_observation_date"]) == _utc(2026, 2, 22)

        # static personnel fields are identical across every week
        for record in records:
            for name, value in STATIC_FIELDS.items():
                assert record[name] == value, f"{name} must be consistent across the window"

        # fields never observed in a week are None (missing, not fabricated)
        assert by_week[0]["wellness_score_self_report"] is None
        assert by_week[1]["weekly_duty_hours"] is None
        assert by_week[0]["weekly_duty_hours"] is None

        # no risk material leaks into the window
        blob = json.dumps(body)
        for forbidden in ("features", "predicted_band", "confidence_basis", "date_key",
                          "is_latest", "risk_model.pkl", ".pkl"):
            assert forbidden not in blob

        del db


# ===================================================================
# 2. Fewer than 4 weeks of available data
# ===================================================================


class TestFewerThanFourWeeks:
    def test_two_weeks_of_data_leaves_other_weeks_missing(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A", extra={**STATIC_FIELDS})
        anchor = _utc(2026, 2, 22)
        _seed_record("pers-A", "wellness_logs", "wk3", anchor,
                     payload_extra={"weekly_duty_hours": 66})
        _seed_record("pers-A", "workload_records", "wk2", anchor - WEEK,
                     payload_extra={"weekly_duty_hours": 54})

        body = client.get("/personnel/pers-A/raw-window", headers=_officer_headers()).json()
        records = body["raw_records"]
        assert len(records) == 4
        assert [r["week"] for r in records] == [0, 1, 2, 3]
        assert body["week_count"] == 2
        assert body["weeks_with_data"] == [2, 3]

        for week in (0, 1):
            record = records[week]
            for field in RAW_NUMERIC_FIELDS:
                assert record[field] is None, f"week {week} {field} must be missing, not fabricated"
        assert records[3]["weekly_duty_hours"] == 66
        assert records[2]["weekly_duty_hours"] == 54

        # static consistency still holds across all 4 weeks
        for record in records:
            for name, value in STATIC_FIELDS.items():
                assert record[name] == value

    def test_single_observation_produces_one_week_of_data(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A", extra={**STATIC_FIELDS})
        _seed_record("pers-A", "wellness_logs", "only", _utc(2026, 2, 22),
                     payload_extra={"weekly_duty_hours": 66})

        body = client.get("/personnel/pers-A/raw-window", headers=_officer_headers()).json()
        assert len(body["raw_records"]) == 4
        assert body["week_count"] == 1
        assert body["weeks_with_data"] == [3]
        assert body["raw_records"][3]["weekly_duty_hours"] == 66
        assert body["raw_records"][0]["weekly_duty_hours"] is None


# ===================================================================
# 3. Missing observations are preserved, never fabricated
# ===================================================================


class TestMissingnessPreserved:
    def test_missing_fields_are_none_and_no_engineered_keys_appear(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A", extra={**STATIC_FIELDS})
        anchor = _utc(2026, 2, 22)
        # only two fields reported in the latest week
        _seed_record("pers-A", "wellness_logs", "partial", anchor,
                     payload_extra={"weekly_duty_hours": 66, "wellness_score_self_report": 3.5})

        body = client.get("/personnel/pers-A/raw-window", headers=_officer_headers()).json()
        latest = body["raw_records"][3]
        assert latest["weekly_duty_hours"] == 66
        assert latest["wellness_score_self_report"] == 3.5
        for field in RAW_NUMERIC_FIELDS:
            if field not in ("weekly_duty_hours", "wellness_score_self_report"):
                assert latest[field] is None, f"{field} must stay None"

        # the window is RAW: no rolling means, deltas, missingness flags, no features
        blob = json.dumps(body)
        for engineered in ("__roll4_mean", "__delta_wow", "__was_missing", "features"):
            assert engineered not in blob, f"engineered key {engineered} leaked into raw window"

    def test_untimestamped_records_are_not_guessed_into_a_week(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A", extra={**STATIC_FIELDS})
        _seed_record("pers-A", "wellness_logs", "timed", _utc(2026, 2, 22),
                     payload_extra={"weekly_duty_hours": 66})
        from lib.db import db
        # a document with no timestamp at all carries a measurable value
        db.wellness_logs.docs.append({
            "id": "rec-no-ts", "personnel_id": "pers-A",
            "payload": {"note": "no-ts", "weekly_duty_hours": 999, "overtime_hours": 99},
        })

        body = client.get("/personnel/pers-A/raw-window", headers=_officer_headers()).json()
        blob = json.dumps(body)
        assert "999" not in blob and "99" not in blob, "untimestamped observations must not be placed"
        assert body["week_count"] == 1
        assert body["raw_records"][3]["weekly_duty_hours"] == 66


# ===================================================================
# 4. Future / out-of-window record exclusion
# ===================================================================


class TestFutureAndOutOfWindowExclusion:
    def test_observations_outside_the_window_are_excluded(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A", extra={**STATIC_FIELDS})
        anchor = _utc(2026, 2, 22)
        _seed_record("pers-A", "wellness_logs", "latest", anchor,
                     payload_extra={"weekly_duty_hours": 66})
        # exactly 28 days before the anchor -> 4 weeks -> outside the window
        _seed_record("pers-A", "workload_records", "stale", anchor - 4 * WEEK,
                     payload_extra={"weekly_duty_hours": 999})

        body = client.get("/personnel/pers-A/raw-window", headers=_officer_headers()).json()
        blob = json.dumps(body)
        assert "999" not in blob, "stale observation must be excluded from the window"
        for record in body["raw_records"]:
            assert record["weekly_duty_hours"] in (66, None)
        # with only the anchor in-window, the window collapses onto it
        assert _parse(body["window_start"]) == _parse(body["window_end"]) == anchor
        assert body["week_count"] == 1

    def test_week_bucket_boundaries_are_exact(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A", extra={**STATIC_FIELDS})
        anchor = _utc(2026, 2, 22, 12)
        # One observation per week with distinct overtime_hours values — no same-week merge
        # collision — plus the anchor in week 3 with a different payload field.
        _seed_record("pers-A", "wellness_logs", "anchor", anchor,
                     payload_extra={"leave_balance": 0.0})
        for offset_days, note in [(6, "w-6"), (13, "w-13"), (20, "w-20"), (27, "w-27")]:
            _seed_record("pers-A", "wellness_logs", note,
                         anchor - datetime.timedelta(days=offset_days),
                         payload_extra={"overtime_hours": float(offset_days)})

        body = client.get("/personnel/pers-A/raw-window", headers=_officer_headers()).json()
        by_week = {r["week"]: r for r in body["raw_records"]}
        assert by_week[3]["overtime_hours"] == 6.0, "anchor+day-6 merge keeps overtime from day-6"
        assert by_week[3]["leave_balance"] == 0.0, "anchor supplies distinct field to week 3"
        assert by_week[2]["overtime_hours"] == 13.0
        assert by_week[1]["overtime_hours"] == 20.0
        assert by_week[0]["overtime_hours"] == 27.0

    def test_latest_observation_is_always_week_three(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A", extra={**STATIC_FIELDS})
        # the most recent record lives in a sparse older week pattern
        _seed_record("pers-A", "wellness_logs", "newest", _utc(2026, 2, 20),
                     payload_extra={"weekly_duty_hours": 66})
        _seed_record("pers-A", "leave_requests", "old", _utc(2026, 2, 1),
                     payload_extra={"leave_balance": 5})
        body = client.get("/personnel/pers-A/raw-window", headers=_officer_headers()).json()
        # 2026-02-20 is the anchor and therefore week 3 (latest)
        assert _parse(body["latest_observation_date"]) == _utc(2026, 2, 20)
        assert body["raw_records"][3]["weekly_duty_hours"] == 66
        assert _parse(body["window_end"]) == _utc(2026, 2, 20)


# ===================================================================
# 5. Chronological ordering + static consistency
# ===================================================================


class TestOrderingAndStaticConsistency:
    def test_records_are_chronological_and_start_never_after_end(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A", extra={**STATIC_FIELDS})
        anchor = _utc(2026, 2, 22)
        # seed deliberately out of chronological order
        _seed_record("pers-A", "leave_requests", "late", anchor - WEEK,
                     payload_extra={"leave_balance": 3})
        _seed_record("pers-A", "wellness_logs", "last", anchor,
                     payload_extra={"weekly_duty_hours": 70})
        body = client.get("/personnel/pers-A/raw-window", headers=_officer_headers()).json()
        weeks = [r["week"] for r in body["raw_records"]]
        assert weeks == sorted(weeks)
        assert _parse(body["window_start"]) <= _parse(body["window_end"])

    def test_static_fields_resolved_once_across_window(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        # personnel document supplies only 3 of the 4 statics
        partial = {k: v for k, v in STATIC_FIELDS.items() if k != "transfer_count_24mo"}
        _seed_personnel("pers-A", extra={**partial})
        anchor = _utc(2026, 2, 22)
        # transfer_count_24mo is only supplied inside the week-2 observation payload
        _seed_record("pers-A", "workload_records", "wk2", anchor - WEEK,
                     payload_extra={"transfer_count_24mo": 7.0})
        _seed_record("pers-A", "wellness_logs", "wk3", anchor,
                     payload_extra={"weekly_duty_hours": 66})

        body = client.get("/personnel/pers-A/raw-window", headers=_officer_headers()).json()
        for record in body["raw_records"]:
            assert record["transfer_count_24mo"] == 7.0, (
                "payload-only static must be resolved once and repeated on every week"
            )
            assert record["years_of_service"] == STATIC_FIELDS["years_of_service"]

    def test_static_fields_missing_everywhere_stay_none(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A")  # no static fields at all
        _seed_record("pers-A", "wellness_logs", "wk3", _utc(2026, 2, 22),
                     payload_extra={"weekly_duty_hours": 66})
        body = client.get("/personnel/pers-A/raw-window", headers=_officer_headers()).json()
        for record in body["raw_records"]:
            assert record["years_of_service"] is None
            assert record["hardship_posting_flag"] is None
            assert record["transfer_count_24mo"] is None
            assert record["years_in_current_posting"] is None


# ===================================================================
# 6. Duplicate handling
# ===================================================================


class TestDuplicateHandling:
    def test_duplicate_ids_deduped_deterministically(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A", extra={**STATIC_FIELDS})
        anchor = _utc(2026, 2, 22, 12)
        # two documents with the SAME id and same week, different timestamps/values
        _seed_record("pers-A", "wellness_logs", "later-dup", anchor,
                     payload_extra={"weekly_duty_hours": 66}, record_id="dup-1")
        _seed_record("pers-A", "workload_records", "earlier-dup", anchor - datetime.timedelta(hours=1),
                     payload_extra={"weekly_duty_hours": 99}, record_id="dup-1")

        body = client.get("/personnel/pers-A/raw-window", headers=_officer_headers()).json()
        # deterministic rule: earliest source occurrence wins
        assert body["raw_records"][3]["weekly_duty_hours"] == 99

    def test_same_week_records_merge_with_later_observation_winning(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A", extra={**STATIC_FIELDS})
        anchor = _utc(2026, 2, 22)
        _seed_record("pers-A", "wellness_logs", "morning", anchor,
                     payload_extra={"weekly_duty_hours": 66, "wellness_score_self_report": 8.0})
        _seed_record("pers-A", "workload_records", "afternoon", anchor + datetime.timedelta(hours=1),
                     payload_extra={"weekly_duty_hours": 54, "overtime_hours": 5.0})

        body = client.get("/personnel/pers-A/raw-window", headers=_officer_headers()).json()
        latest = body["raw_records"][3]
        assert latest["weekly_duty_hours"] == 54, "later observation wins the shared field"
        assert latest["wellness_score_self_report"] == 8.0, "fields from other records are kept"
        assert latest["overtime_hours"] == 5.0

    def test_repeated_builds_are_byte_identical(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_full_window()
        from lib.history import build_four_week_window

        first = await_result(build_four_week_window("pers-A", {"user_id": "wo-1", "role": "WELFARE_OFFICER"}))
        second = await_result(build_four_week_window("pers-A", {"user_id": "wo-1", "role": "WELFARE_OFFICER"}))
        # JSON round-trip isolates any non-serializable datetime differences
        assert json.dumps(first, default=str) == json.dumps(second, default=str)


def await_result(coro):
    import asyncio

    return asyncio.run(coro)


# ===================================================================
# 7. Raw schema validation
# ===================================================================


class TestRawSchemaValidation:
    def test_raw_records_match_feature_engineering_contract_exactly(self, client):
        from lib.db import db
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_full_window()
        _seed_assessment("pers-A", "ass-int", _utc(2026, 2, 22, 23))

        from lib.feature_engineering import REQUIRED_RAW_COLUMNS
        body = client.get("/personnel/pers-A/raw-window", headers=_officer_headers()).json()
        required = set(REQUIRED_RAW_COLUMNS)
        assert len(REQUIRED_RAW_COLUMNS) == 16  # personnel_id + week + 4 static + 10 raw
        for record in body["raw_records"]:
            assert set(record) == required
            assert record["personnel_id"] == "pers-A"
            assert isinstance(record["week"], int) and record["week"] in (0, 1, 2, 3)

        del db

    def test_no_engineered_or_sensitive_keys_in_raw_window(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A", extra={**STATIC_FIELDS})
        _seed_record("pers-A", "wellness_logs", "x", _utc(2026, 2, 22),
                     payload_extra={"weekly_duty_hours": 66})
        body = client.get("/personnel/pers-A/raw-window", headers=_officer_headers()).json()
        blob = json.dumps(body)
        for forbidden in ("__roll4_mean", "__delta_wow", "__was_missing", "features",
                          "predicted_band", "risk_probability", "confidence_basis",
                          "date_key", "is_latest", ".pkl", "risk_model"):
            assert forbidden not in blob, f"leaked forbidden token {forbidden}"


# ===================================================================
# 8. Exact 44-feature compatibility
# ===================================================================


class TestExactFeatureCompatibility:
    def test_window_feeds_existing_pipeline_yielding_44_features_in_metadata_order(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_full_window("pers-A")
        body = client.get("/personnel/pers-A/raw-window", headers=_officer_headers()).json()

        from lib.feature_engineering import (
            FEATURE_COUNT,
            features_for_latest_week,
            get_feature_columns,
            records_to_frame,
        )
        # the window's raw records must flow directly into the existing contract
        frame = records_to_frame(body["raw_records"])
        assert len(frame) == 4

        latest = features_for_latest_week(frame)
        assert latest.shape == (1, 1 + FEATURE_COUNT)
        assert latest.columns.tolist() == ["personnel_id"] + get_feature_columns()
        assert latest["personnel_id"].iloc[0] == "pers-A"
        assert get_feature_columns() == json.loads(
            (ARTIFACT_DIR / "model_metadata.json").read_text(encoding="utf-8")
        )["feature_list_in_order"]

    def test_window_records_run_through_inference_when_artifacts_available(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_full_window("pers-A")
        body = client.get("/personnel/pers-A/raw-window", headers=_officer_headers()).json()

        from lib.inference import InferenceEngine
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                engine = InferenceEngine(ARTIFACT_DIR)
                engine.load()
            except Exception:
                pytest.skip("BLOCKED: LightGBM model artifacts unavailable in this environment")

            result, ordered = engine.predict_from_raw_records(body["raw_records"], personnel_id="pers-A")

        assert set(ordered) == set(engine.feature_names) and len(ordered) == 44
        assert list(ordered) == engine.feature_names
        assert result["predicted_band"] in ("Low", "Moderate", "High")
        assert 0.0 <= result["risk_probability"] <= 1.0


# ===================================================================
# 9. RBAC / IDOR protection
# ===================================================================


class TestRbacAndIdor:
    def test_welfare_officer_is_authorized(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_full_window("pers-A")
        resp = client.get("/personnel/pers-A/raw-window", headers=_officer_headers())
        assert resp.status_code == 200

    def test_personnel_cannot_request_another_persons_window(self, client):
        _seed_user(client, "pers-A", "persona", "PERSONNEL")
        _seed_user(client, "pers-B", "personb", "PERSONNEL")
        _seed_personnel("pers-B", extra={**STATIC_FIELDS})
        _seed_record("pers-B", "wellness_logs", "B-secret", _utc(2026, 2, 22),
                     payload_extra={"weekly_duty_hours": 66})

        resp = client.get("/personnel/pers-B/raw-window",
                          headers=_headers("pers-A", "persona", "PERSONNEL"))
        assert resp.status_code == 403
        blob = resp.text
        assert "B-secret" not in blob
        assert "pers-B" not in blob

    def test_commander_is_blocked_aggregate_only(self, client):
        _seed_user(client, "cmd-1", "cmdr", "COMMANDER")
        _seed_personnel("pers-A", extra={**STATIC_FIELDS})
        _seed_record("pers-A", "wellness_logs", "x", _utc(2026, 2, 22),
                     payload_extra={"weekly_duty_hours": 66})
        resp = client.get("/personnel/pers-A/raw-window", headers=_headers("cmd-1", "cmdr", "COMMANDER"))
        assert resp.status_code == 403
        assert "pers-A" not in resp.text

    def test_unauthenticated_is_blocked(self, client):
        resp = client.get("/personnel/pers-A/raw-window")
        assert resp.status_code in (401, 403)

    def test_service_rejects_non_officer_direct_calls(self, client):
        from lib.history import HistoryAccessError, build_four_week_window
        for role in ("PERSONNEL", "COMMANDER"):
            with pytest.raises(HistoryAccessError):
                await_result(build_four_week_window("pers-A", {"user_id": "u", "role": role}))
        with pytest.raises(HistoryAccessError):
            await_result(build_four_week_window("pers-A", None))
        with pytest.raises(ValueError):
            await_result(build_four_week_window("", {"user_id": "u", "role": "WELFARE_OFFICER"}))

    def test_window_with_no_observations_raises(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        from lib.history import WindowBuilderError, build_four_week_window
        with pytest.raises(WindowBuilderError):
            await_result(build_four_week_window("ghost-id", {"user_id": "wo-1", "role": "WELFARE_OFFICER"}))


# ===================================================================
# 10. No sensitive data exposure
# ===================================================================


class TestNoSensitiveExposure:
    def test_no_credentials_or_model_internals_in_response(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A", extra={
            **STATIC_FIELDS,
            "password_hash": "hunter2",
            "secret_note": "leak",
            "api_token": "tok-123",
        })
        anchor = _utc(2026, 2, 22)
        _seed_record("pers-A", "wellness_logs", "x", anchor,
                     payload_extra={
                         "weekly_duty_hours": 66,
                         "nested": {"password": "P@ssw0rd", "jwt": "eyJhbGciOi", "ok": 1},
                         "access_token": "tok-123",
                     })
        _seed_assessment("pers-A", "ass-int", _utc(2026, 2, 22, 23))

        resp = client.get("/personnel/pers-A/raw-window", headers=_officer_headers())
        assert resp.status_code == 200, resp.text
        body = resp.json()
        blob = json.dumps(body)

        for forbidden in ("hunter2", "leak", "tok-123", "P@ssw0rd", "eyJhbGciOi",
                          "password", "jwt", "access_token", "secret", "features",
                          "predicted_band", "risk_probability", "confidence_basis",
                          "date_key", "is_latest", "risk_model.pkl", ".pkl"):
            assert forbidden not in blob, f"{forbidden} leaked in the raw-window response"

        # the raw weekly values themselves survived the scrub
        assert body["raw_records"][3]["weekly_duty_hours"] == 66
        # personnel envelope carries only safe identity + static fields
        allowed = {"id", "name", "service_number", "rank", "unit", "posting",
                   "created_at", "years_of_service", "hardship_posting_flag",
                   "transfer_count_24mo", "years_in_current_posting"}
        assert set(body["personnel"]) <= allowed


# ===================================================================
# 11. Week-bucket boundary unit tests (pure, hermetic)
# ===================================================================


class TestWeekIndexBoundaries:
    def test_week_index_maps_every_bucket_boundary_exactly(self):
        from lib.history import _week_index

        anchor = _utc(2026, 3, 1, 12)
        # first and last day of every bucket (0=oldest .. 3=latest)
        cases = {
            0: 3, 6: 3,
            7: 2, 13: 2,
            14: 1, 20: 1,
            21: 0, 27: 0,
        }
        for offset, expected in cases.items():
            mapped = _week_index(anchor - datetime.timedelta(days=offset), anchor)
            assert mapped == expected, f"{offset} days before anchor must map to week {expected}"

    def test_week_index_excludes_28_days_and_beyond(self):
        from lib.history import _week_index

        anchor = _utc(2026, 3, 1, 12)
        assert _week_index(anchor - datetime.timedelta(days=28), anchor) is None
        assert _week_index(anchor - datetime.timedelta(days=29), anchor) is None
        assert _week_index(anchor - datetime.timedelta(days=400), anchor) is None

    def test_week_index_truncates_partial_days_consistently(self):
        from lib.history import _week_index

        anchor = _utc(2026, 3, 1, 12)
        # 27d23h still falls inside week 0; 28d exact is the first excluded instant
        assert _week_index(anchor - datetime.timedelta(days=27, hours=23), anchor) == 0
        assert _week_index(anchor - datetime.timedelta(days=28), anchor) is None

    def test_week_index_excludes_observations_after_the_anchor(self):
        from lib.history import _week_index

        anchor = _utc(2026, 3, 1, 12)
        assert _week_index(anchor + datetime.timedelta(hours=1), anchor) is None
        assert _week_index(anchor + datetime.timedelta(days=5), anchor) is None


# ===================================================================
# 12. Personnel isolation at the data layer
# ===================================================================


class TestPersonnelDataIsolation:
    def test_other_personnel_records_never_enter_or_anchor_the_window(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A", extra={**STATIC_FIELDS})
        _seed_personnel("pers-B", extra={**STATIC_FIELDS})
        anchor = _utc(2026, 2, 22)

        _seed_record("pers-A", "wellness_logs", "a-own", anchor,
                     payload_extra={"weekly_duty_hours": 40})
        # pers-B's records live in the SAME collections and one is far later:
        # neither may leak into pers-A's window nor move pers-A's anchor.
        _seed_record("pers-B", "wellness_logs", "b-secret", anchor,
                     payload_extra={"weekly_duty_hours": 999})
        _seed_record("pers-B", "workload_records", "b-late",
                     anchor + datetime.timedelta(days=10),
                     payload_extra={"overtime_hours": 777})

        body = client.get("/personnel/pers-A/raw-window", headers=_officer_headers()).json()
        blob = json.dumps(body)
        assert "999" not in blob and "777" not in blob
        assert "b-secret" not in blob and "b-late" not in blob
        assert _parse(body["latest_observation_date"]) == anchor
        assert _parse(body["window_end"]) == anchor
        assert body["raw_records"][3]["weekly_duty_hours"] == 40
        assert all(record["personnel_id"] == "pers-A" for record in body["raw_records"])


# ===================================================================
# 13. Risk assessments never drive the window
# ===================================================================


class TestRiskAssessmentsExcludedFromWindow:
    def test_assessment_after_anchor_does_not_shift_or_leak(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A", extra={**STATIC_FIELDS})
        anchor = _utc(2026, 2, 22)
        _seed_record("pers-A", "wellness_logs", "obs", anchor,
                     payload_extra={"weekly_duty_hours": 66})
        # a stored assessment far AFTER the anchor, carrying an engineered vector
        _seed_assessment("pers-A", "ass-late", anchor + datetime.timedelta(days=90))

        body = client.get("/personnel/pers-A/raw-window", headers=_officer_headers()).json()
        assert _parse(body["latest_observation_date"]) == anchor
        assert _parse(body["window_end"]) == anchor
        assert body["week_count"] == 1
        for record in body["raw_records"]:
            assert record["weekly_duty_hours"] in (66, None)
        blob = json.dumps(body)
        for forbidden in ("ass-late", "INTERNAL_FEATURE_MARKER",
                          "weekly_duty_hours__roll4_mean", "predicted_band",
                          "risk_probability", "confidence_basis"):
            assert forbidden not in blob, f"assessment material {forbidden} leaked"


# ===================================================================
# 14. Raw-contract validator defense in depth
# ===================================================================


class TestRawContractDefenseInDepth:
    @staticmethod
    def _valid_record() -> dict:
        from lib.feature_engineering import REQUIRED_RAW_COLUMNS

        record = {col: None for col in REQUIRED_RAW_COLUMNS}
        record["personnel_id"] = "pers-A"
        record["week"] = 0
        return record

    def test_validator_accepts_only_the_exact_contract(self):
        from lib.history import _validate_raw_window_contract

        _validate_raw_window_contract([self._valid_record()])  # must not raise

    def test_validator_rejects_engineered_extra_columns(self):
        from lib.history import WindowBuilderError, _validate_raw_window_contract

        engineered = self._valid_record()
        engineered["weekly_duty_hours__roll4_mean"] = 40.0
        with pytest.raises(WindowBuilderError):
            _validate_raw_window_contract([engineered])

        extra_unknown = self._valid_record()
        extra_unknown["surprise_field"] = 1
        with pytest.raises(WindowBuilderError):
            _validate_raw_window_contract([extra_unknown])

    def test_validator_rejects_missing_columns(self):
        from lib.history import WindowBuilderError, _validate_raw_window_contract

        missing = self._valid_record()
        missing.pop("sleep_hours_biometric")
        with pytest.raises(WindowBuilderError):
            _validate_raw_window_contract([missing])

    def test_validator_rejects_bad_week_and_blank_personnel_id(self):
        from lib.history import WindowBuilderError, _validate_raw_window_contract

        bad_week = self._valid_record()
        bad_week["week"] = 4
        with pytest.raises(WindowBuilderError):
            _validate_raw_window_contract([bad_week])

        blank_id = self._valid_record()
        blank_id["personnel_id"] = "   "
        with pytest.raises(WindowBuilderError):
            _validate_raw_window_contract([blank_id])


# ===================================================================
# 15. Deterministic anchor independent of wall clock + gap weeks
# ===================================================================


class TestDeterministicAnchorAndGaps:
    def test_anchor_is_latest_observation_not_wall_clock(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A", extra={**STATIC_FIELDS})
        # deliberately dated in the future relative to "today"
        future = _utc(2031, 1, 15, 9)
        _seed_record("pers-A", "wellness_logs", "future-latest", future,
                     payload_extra={"weekly_duty_hours": 50})
        _seed_record("pers-A", "workload_records", "future-old",
                     future - datetime.timedelta(days=25),
                     payload_extra={"overtime_hours": 4})

        body = client.get("/personnel/pers-A/raw-window", headers=_officer_headers()).json()
        assert _parse(body["latest_observation_date"]) == future
        assert _parse(body["window_end"]) == future
        assert body["week_count"] == 2
        assert body["raw_records"][3]["weekly_duty_hours"] == 50
        assert body["raw_records"][0]["overtime_hours"] == 4

    def test_gap_week_remains_represented_all_missing(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A", extra={**STATIC_FIELDS})
        anchor = _utc(2026, 2, 22)
        # weeks 3 and 1 populated, weeks 0 and 2 have no observations at all
        _seed_record("pers-A", "wellness_logs", "wk3", anchor,
                     payload_extra={"weekly_duty_hours": 66})
        _seed_record("pers-A", "leave_requests", "wk1", anchor - 2 * WEEK,
                     payload_extra={"leave_balance": 5})

        body = client.get("/personnel/pers-A/raw-window", headers=_officer_headers()).json()
        records = {r["week"]: r for r in body["raw_records"]}
        assert [r["week"] for r in body["raw_records"]] == [0, 1, 2, 3]
        assert body["weeks_with_data"] == [1, 3]
        assert body["weeks_with_data"] == sorted(body["weeks_with_data"])
        assert records[1]["leave_balance"] == 5
        assert records[3]["weekly_duty_hours"] == 66
        for week in (0, 2):
            assert records[week] is not None, "missing week must still be emitted"
            for field in RAW_NUMERIC_FIELDS:
                assert records[week][field] is None, (
                    f"gap week {week} {field} must be missing, not fabricated"
                )


def test_module_exports_expected_entry_points():
    from lib.history import build_four_week_window, get_personnel_raw_window
    assert build_four_week_window is not None
    assert get_personnel_raw_window is build_four_week_window