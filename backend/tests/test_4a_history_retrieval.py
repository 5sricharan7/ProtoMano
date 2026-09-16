"""Task 4A — Welfare intelligence historical data retrieval tests.

Hermetic harness (same pattern as the 3B/3C suites): real routers + auth/RBAC
dependencies over an in-memory fake Mongo via FastAPI TestClient, plus direct
service-level calls.  No live MongoDB or backend process is required.

Covers:
- successful historical retrieval (all six data sources)
- deterministic chronological ordering per section
- missing data is absent, never fabricated
- zero-valued data is present and distinct from missing
- personnel ID isolation (no cross-person bleed)
- Welfare Officer authorization
- Commander restriction (aggregate-only)
- Personnel cannot retrieve other personnel's history
- no sensitive auth fields / model internals exposed
"""

from __future__ import annotations

import datetime
import json
import os

# auth_service requires AUTH_SECRET_KEY before import. Test-only secret.
os.environ.setdefault("AUTH_SECRET_KEY", "test-only-secret-key-not-for-production-1234567890")

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lib.auth_service import create_access_token

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


def _utc(y, m, d, h=0):
    return datetime.datetime(y, m, d, h, tzinfo=TZ)


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


def _seed_record(user_id: str, collection: str, note: str, created_at, payload_extra: dict | None = None):
    from lib.db import db

    doc = {
        "id": f"rec-{collection}-{note}",
        "personnel_id": user_id,
        "created_at": created_at,
        "payload": {"note": note, **(payload_extra or {})},
    }
    getattr(db, collection).docs.append(doc)


def _seed_assessment(user_id: str, assessment_id: str, assessed_at, band: str = "High", probability: float = 0.9):
    from lib.db import db

    db.risk_assessments.docs.append({
        "id": assessment_id,
        "personnel_id": user_id,
        "assessed_at": assessed_at,
        "date_key": assessed_at.date().isoformat(),
        "is_latest": True,
        "features": {"weekly_duty_hours__roll4_mean": 40.0, "INTERNAL_FEATURE_MARKER": 1.0},
        "confidence_basis": "Maximum calibrated class probability from risk_model.pkl",
        "data_trust": {"score": 80.0, "threshold": 60.0, "label": "High", "basis": "x",
                       "components": {"completeness": 80.0, "recency": 100.0, "source_reliability": 85.0, "consistency": 75.0}},
        "decision_support": {"state": "MONITOR", "abstained": False, "basis": "y"},
        "predicted_band": band,
        "risk_probability": probability,
        "prediction_confidence": probability,
        "class_probabilities": [{"band": "Low", "probability": (1 - probability) / 2},
                                {"band": "Moderate", "probability": (1 - probability) / 2},
                                {"band": band, "probability": probability}],
        "top_contributing_factors": [{"feature": "weekly_duty_hours", "contribution": 0.5, "direction": "increases"}],
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


def _parse(event_at: str) -> datetime.datetime:
    return datetime.datetime.fromisoformat(event_at.replace("Z", "+00:00"))


# ===================================================================
# 1. Successful historical retrieval
# ===================================================================


class TestSuccessfulRetrieval:
    def test_officer_retrieves_all_six_sources(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A", name="Anita Rawat", extra={"is_demo_data": True})
        _seed_record("pers-A", "wellness_logs", "wellness-one", _utc(2026, 2, 1))
        _seed_record("pers-A", "workload_records", "workload-one", _utc(2026, 2, 2))
        _seed_record("pers-A", "deployment_history", "deploy-one", _utc(2026, 2, 3))
        _seed_record("pers-A", "leave_requests", "leave-one", _utc(2026, 2, 4))
        _seed_assessment("pers-A", "ass-A-1", _utc(2026, 2, 5))

        resp = client.get("/personnel/pers-A/history", headers=_headers("wo-1", "welfareo", "WELFARE_OFFICER"))
        assert resp.status_code == 200, resp.text
        body = resp.json()

        assert body["personnel_id"] == "pers-A"
        assert body["personnel"]["name"] == "Anita Rawat"
        assert body["personnel"]["id"] == "pers-A"
        assert body["personnel"]["is_demo_data"] is True

        sections = body["sections"]
        assert list(sections.keys()) == [
            "wellness_logs", "workload_records", "deployment_history",
            "leave_requests", "risk_assessments",
        ]
        assert sections["wellness_logs"]["present"] is True
        assert sections["wellness_logs"]["record_count"] == 1
        assert sections["workload_records"]["present"] is True
        assert sections["deployment_history"]["present"] is True
        assert sections["leave_requests"]["present"] is True
        assert sections["risk_assessments"]["present"] is True
        assert sections["risk_assessments"]["record_count"] == 1

        assert body["generated_at"]
        assert isinstance(body["notes"], list) and len(body["notes"]) == 3

    def test_formatted_envelope_types(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A")
        _seed_record("pers-A", "wellness_logs", "x", _utc(2026, 1, 1))
        resp = client.get("/personnel/pers-A/history", headers=_headers("wo-1", "welfareo", "WELFARE_OFFICER"))
        assert resp.status_code == 200
        item = resp.json()["sections"]["wellness_logs"]["records"][0]
        assert set(item.keys()) == {"id", "collection", "event_at", "payload"}
        assert item["collection"] == "wellness_logs"
        assert _parse(item["event_at"]) == _utc(2026, 1, 1)
        assert item["payload"]["note"] == "x"


# ===================================================================
# 2. Deterministic chronological ordering
# ===================================================================


class TestChronologicalOrdering:
    def test_records_returned_oldest_first(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A")
        _seed_record("pers-A", "wellness_logs", "third", _utc(2026, 3, 1))
        _seed_record("pers-A", "wellness_logs", "first", _utc(2026, 1, 1))
        _seed_record("pers-A", "wellness_logs", "second", _utc(2026, 2, 1))

        body = client.get("/personnel/pers-A/history", headers=_headers("wo-1", "welfareo", "WELFARE_OFFICER")).json()
        notes = [r["payload"]["note"] for r in body["sections"]["wellness_logs"]["records"]]
        assert notes == ["first", "second", "third"]

    def test_assessments_returned_by_assessed_at_oldest_first(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A")
        _seed_assessment("pers-A", "ass-latest", _utc(2026, 3, 1), band="Low", probability=0.3)
        _seed_assessment("pers-A", "ass-oldest", _utc(2026, 1, 1), band="High", probability=0.9)
        _seed_assessment("pers-A", "ass-middle", _utc(2026, 2, 1), band="Moderate", probability=0.5)

        body = client.get("/personnel/pers-A/history", headers=_headers("wo-1", "welfareo", "WELFARE_OFFICER")).json()
        ids = [r["id"] for r in body["sections"]["risk_assessments"]["records"]]
        assert ids == ["ass-oldest", "ass-middle", "ass-latest"]

    def test_untimestamped_records_sort_last_deterministically(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A")
        _seed_record("pers-A", "leave_requests", "timed", _utc(2026, 1, 1))
        from lib.db import db
        db.leave_requests.docs.append({"id": "b-no-ts", "personnel_id": "pers-A", "payload": {"note": "no-ts-b"}})
        db.leave_requests.docs.append({"id": "a-no-ts", "personnel_id": "pers-A", "payload": {"note": "no-ts-a"}})

        body = client.get("/personnel/pers-A/history", headers=_headers("wo-1", "welfareo", "WELFARE_OFFICER")).json()
        records = body["sections"]["leave_requests"]["records"]
        notes = [r["payload"]["note"] for r in records]
        assert notes == ["timed", "no-ts-a", "no-ts-b"]
        assert [r["event_at"] for r in records[-2:]] == [None, None]


# ===================================================================
# 3. Missing data — never fabricated, distinct from zero-valued
# ===================================================================


class TestMissingData:
    def test_unknown_personnel_returns_empty_not_fabricated(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        resp = client.get("/personnel/ghost-id/history", headers=_headers("wo-1", "welfareo", "WELFARE_OFFICER"))
        assert resp.status_code == 200
        body = resp.json()
        assert body["personnel"] is None
        for section in body["sections"].values():
            assert section["present"] is False
            assert section["record_count"] == 0
            assert section["records"] == []

    def test_personnel_with_no_welfare_history(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-wo-here")
        body = client.get("/personnel/pers-wo-here/history", headers=_headers("wo-1", "welfareo", "WELFARE_OFFICER")).json()
        assert body["personnel"]["id"] == "pers-wo-here"
        for name, section in body["sections"].items():
            assert section["present"] is False, f"{name} should be absent"

    def test_zero_valued_records_are_present_but_missing_is_not(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-zero")
        _seed_record("pers-zero", "workload_records", "all-zero", _utc(2026, 1, 1),
                     payload_extra={"weekly_duty_hours": 0, "overtime_hours": 0, "leave_balance": 0})

        body = client.get("/personnel/pers-zero/history", headers=_headers("wo-1", "welfareo", "WELFARE_OFFICER")).json()
        workload = body["sections"]["workload_records"]
        assert workload["present"] is True, "zero-valued records are real data"
        assert workload["record_count"] == 1
        assert workload["records"][0]["payload"]["weekly_duty_hours"] == 0
        assert body["sections"]["wellness_logs"]["present"] is False, "absent section stays absent"

    def test_missing_collection_degrades_gracefully(self, client, monkeypatch):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-colmissing")
        from lib.db import db
        monkeypatch.setattr(db, "wellness_logs", None)
        resp = client.get("/personnel/pers-colmissing/history", headers=_headers("wo-1", "welfareo", "WELFARE_OFFICER"))
        assert resp.status_code == 200
        assert resp.json()["sections"]["wellness_logs"] == {"present": False, "record_count": 0, "records": []}


# ===================================================================
# 4. Personnel ID isolation
# ===================================================================


class TestPersonnelIdIsolation:
    def test_no_cross_personnel_bleed(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A", name="Person A")
        _seed_personnel("pers-B", name="Person B")
        _seed_record("pers-A", "wellness_logs", "A-private-note", _utc(2026, 1, 1))
        _seed_record("pers-B", "wellness_logs", "B-private-note", _utc(2026, 1, 2))
        _seed_assessment("pers-B", "ass-B-1", _utc(2026, 1, 3))

        body = client.get("/personnel/pers-B/history", headers=_headers("wo-1", "welfareo", "WELFARE_OFFICER")).json()
        blob = json.dumps(body)
        assert body["personnel"]["name"] == "Person B"
        assert "A-private-note" not in blob
        assert "Person A" not in blob

        body_a = client.get("/personnel/pers-A/history", headers=_headers("wo-1", "welfareo", "WELFARE_OFFICER")).json()
        blob_a = json.dumps(body_a)
        assert "B-private-note" not in blob_a
        assert "ass-B-1" not in blob_a
        assert body_a["sections"]["risk_assessments"]["present"] is False


# ===================================================================
# 5. RBAC: Welfare Officer authorization / Commander restriction
# ===================================================================


class TestRbac:
    def test_welfare_officer_authorized(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A")
        resp = client.get("/personnel/pers-A/history", headers=_headers("wo-1", "welfareo", "WELFARE_OFFICER"))
        assert resp.status_code == 200

    def test_commander_blocked_aggregate_only(self, client):
        _seed_user(client, "cmd-1", "cmdr", "COMMANDER")
        _seed_personnel("pers-A")
        resp = client.get("/personnel/pers-A/history", headers=_headers("cmd-1", "cmdr", "COMMANDER"))
        assert resp.status_code == 403
        assert "pers-A" not in resp.text

    def test_personnel_cannot_retrieve_anyone(self, client):
        _seed_user(client, "pers-A", "persona", "PERSONNEL")
        _seed_user(client, "pers-B", "personb", "PERSONNEL")
        _seed_record("pers-B", "wellness_logs", "secret-B-note", _utc(2026, 1, 1))
        resp = client.get("/personnel/pers-B/history", headers=_headers("pers-A", "persona", "PERSONNEL"))
        assert resp.status_code == 403
        assert "secret-B-note" not in resp.text

    def test_unauthenticated_blocked(self, client):
        resp = client.get("/personnel/pers-A/history")
        assert resp.status_code in (401, 403)

    def test_service_requires_officer_role(self, client, monkeypatch):
        from lib.db import db
        from lib.history import get_personnel_history, HistoryAccessError

        for role in ("PERSONNEL", "COMMANDER"):
            with pytest.raises(HistoryAccessError):
                asyncio_run(get_personnel_history("pers-A", {"user_id": "u", "role": role}))
        with pytest.raises(HistoryAccessError):
            asyncio_run(get_personnel_history("pers-A", None))
        with pytest.raises(ValueError):
            asyncio_run(get_personnel_history("", {"user_id": "u", "role": "WELFARE_OFFICER"}))


def asyncio_run(coro):
    import asyncio

    return asyncio.run(coro)


# ===================================================================
# 6. No sensitive auth fields / model internals exposed
# ===================================================================


class TestNoSensitiveExposure:
    def test_credential_like_payload_keys_scrubbed(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A")
        _seed_record("pers-A", "wellness_logs", "nested", _utc(2026, 1, 1), payload_extra={
            "nested": {"password": "P@ssw0rd", "jwt": "eyJhbGciOi", "ok_value": 7},
            "access_token": "tok-123",
        })
        body = client.get("/personnel/pers-A/history", headers=_headers("wo-1", "welfareo", "WELFARE_OFFICER")).json()
        blob = json.dumps(body)
        for forbidden in ("P@ssw0rd", "tok-123", "eyJhbGciOi", "password", "access_token", "jwt", "secret"):
            assert forbidden not in blob, f"{forbidden} leaked in history response"
        payload = body["sections"]["wellness_logs"]["records"][0]["payload"]
        assert payload["nested"] == {"ok_value": 7}

    def test_assessments_minimized_no_model_internals(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A")
        _seed_assessment("pers-A", "ass-A-1", _utc(2026, 1, 1))
        body = client.get("/personnel/pers-A/history", headers=_headers("wo-1", "welfareo", "WELFARE_OFFICER")).json()
        record = body["sections"]["risk_assessments"]["records"][0]["payload"]
        record_blob = json.dumps(record)
        for forbidden in ("features", "INTERNAL_FEATURE_MARKER", "date_key", "is_latest",
                          "confidence_basis", "risk_model.pkl", ".pkl"):
            assert forbidden not in record_blob, f"assessment exposed internal field/marker {forbidden}"
        assert set(record.keys()) == {
            "id", "personnel_id", "assessed_at", "predicted_band", "risk_probability",
            "prediction_confidence", "class_probabilities", "top_contributing_factors",
            "data_trust", "decision_support", "model_version", "feature_version",
        }
        assert record["predicted_band"] == "High"

    def test_personnel_static_record_excludes_unknown_fields(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A", extra={"password_hash": "hunter2", "secret_note": "leak"})
        body = client.get("/personnel/pers-A/history", headers=_headers("wo-1", "welfareo", "WELFARE_OFFICER")).json()
        blob = json.dumps(body)
        assert "hunter2" not in blob
        assert "secret_note" not in blob
        personnel = body["personnel"]
        assert set(personnel.keys()) == {"id", "name", "service_number", "rank", "unit", "posting", "created_at"}