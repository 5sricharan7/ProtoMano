"""Task 4G — Welfare Intervention & Action Tracking integration tests.

Hermetic harness (same pattern as the 4A/4B/4C/4D/4E/4F and 3B/3C suites):
real routers + auth/RBAC dependencies over an in-memory fake Mongo via FastAPI
TestClient.  No live MongoDB or backend process required.  Artifact-dependent
regression tests use the real ``InferenceEngine`` and skip when artifacts are
absent.

Covers:
- officer create / list / update / close of personnel interventions
- strict schema boundary (type/status enums, required fields, extra=forbid:
  personnel_id / welfare_officer_id / role can never be smuggled in the body)
- invalid personnel and unknown intervention -> 404
- auth required; WELFARE_OFFICER allowed; PERSONNEL & COMMANDER blocked
- no cross-personnel access (no client-controlled personnel scope)
- lifecycle audit (created / updated / closed) with sensitive fields never
  logged (notes, reason, outcome, outcome_notes, request bodies)
- persistence in the single shared ``db.interventions`` collection
- legacy Phase 3 intervention documents still readable + normalized
- Commander aggregate-only overview leaks no intervention details
- Phase 4A/4F regression protection
"""

from __future__ import annotations

import asyncio
import datetime
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
        if args:
            key = args[0]
            direction = args[1] if len(args) > 1 else 1
        else:
            key = kwargs.get("key")
            direction = kwargs.get("direction", 1)
        reverse = str(direction).strip() in ("-1", "-1.0", "desc", "-1.0")
        self._docs = sorted(self._docs, key=lambda d: d.get(key), reverse=reverse)
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
ANCHOR = datetime.datetime(2026, 2, 22, tzinfo=TZ)

CREATE_BODY = {
    "intervention_type": "CHECK_IN",
    "reason": "Scheduled voluntary welfare check-in",
    "notes": "Discussed rest hygiene and workload; officer to follow up next month.",
    "status": "OPEN",
}

EXPECTED_KEYS = {
    "intervention_id",
    "personnel_id",
    "welfare_officer_id",
    "created_at",
    "intervention_type",
    "reason",
    "notes",
    "status",
    "follow_up_at",
    "outcome",
    "outcome_notes",
    "updated_at",
}


def _token(user_id: str, username: str, role: str) -> str:
    return create_access_token(user_id=user_id, username=username, role=role)


def _headers(user_id: str, username: str, role: str) -> dict:
    return {"Authorization": f"Bearer {_token(user_id, username, role)}"}


def _officer_headers():
    return _headers("wo-1", "welfareo", "WELFARE_OFFICER")


def _personnel_headers():
    return _headers("pers-A", "persona", "PERSONNEL")


def _commander_headers():
    return _headers("cmd-1", "cmdr", "COMMANDER")


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


def _seed_personnel(user_id: str, name: str = "Test Person"):
    from lib.db import db

    db.personnel.docs.append({
        "id": user_id,
        "name": name,
        "service_number": f"SRV-{user_id}",
        "rank": "Sepoy",
        "unit": "Provost Unit",
        "posting": "Field Base",
        "created_at": datetime.datetime(2026, 1, 1, tzinfo=TZ),
    })


def _audit_events():
    from lib.db import db

    return [doc for doc in db.audit_logs.docs if str(doc.get("event_type", "")).startswith("intervention_")]


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


class TestCreate:
    def test_officer_can_create_intervention(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A")
        resp = client.post("/personnel/pers-A/interventions", json=CREATE_BODY, headers=_officer_headers())
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert set(body.keys()) == EXPECTED_KEYS
        assert body["personnel_id"] == "pers-A"
        assert body["welfare_officer_id"] == "wo-1"
        assert body["intervention_type"] == "CHECK_IN"
        assert body["status"] == "OPEN"
        assert body["reason"] == CREATE_BODY["reason"]
        assert body["notes"] == CREATE_BODY["notes"]
        assert body["updated_at"] is None

    def test_officer_identity_comes_from_token_not_body(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A")
        resp = client.post(
            "/personnel/pers-A/interventions",
            json={**CREATE_BODY, "welfare_officer_id": "wo-999"},
            headers=_officer_headers(),
        )
        assert resp.status_code == 422, resp.text

    def test_invalid_intervention_type_rejected(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A")
        resp = client.post(
            "/personnel/pers-A/interventions",
            json={**CREATE_BODY, "intervention_type": "PROMOTION"},
            headers=_officer_headers(),
        )
        assert resp.status_code == 422, resp.text

    def test_invalid_status_rejected(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A")
        resp = client.post(
            "/personnel/pers-A/interventions",
            json={**CREATE_BODY, "status": "INVALID"},
            headers=_officer_headers(),
        )
        assert resp.status_code == 422, resp.text

    @pytest.mark.parametrize("bad_body", [
        {key: value for key, value in CREATE_BODY.items() if key != "intervention_type"},
        {key: value for key, value in CREATE_BODY.items() if key != "reason"},
        {key: value for key, value in CREATE_BODY.items() if key != "notes"},
        {**CREATE_BODY, "notes": "x"},
        {**CREATE_BODY, "reason": ""},
    ])
    def test_missing_or_short_required_fields_rejected(self, client, bad_body):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A")
        resp = client.post("/personnel/pers-A/interventions", json=bad_body, headers=_officer_headers())
        assert resp.status_code == 422, resp.text

    def test_extra_body_fields_rejected(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A")
        for smuggled in ({**CREATE_BODY, "personnel_id": "pers-B"},
                          {**CREATE_BODY, "role": "COMMANDER"},
                          {**CREATE_BODY, "user_id": "pers-B"}):
            resp = client.post("/personnel/pers-A/interventions", json=smuggled, headers=_officer_headers())
            assert resp.status_code == 422, resp.text

    def test_malformed_follow_up_date_rejected(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A")
        resp = client.post(
            "/personnel/pers-A/interventions",
            json={**CREATE_BODY, "follow_up_at": "not-a-date"},
            headers=_officer_headers(),
        )
        assert resp.status_code == 422, resp.text

    def test_valid_follow_up_date_accepted(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A")
        resp = client.post(
            "/personnel/pers-A/interventions",
            json={**CREATE_BODY, "follow_up_at": "2026-03-20T09:00:00Z"},
            headers=_officer_headers(),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["follow_up_at"] is not None

    def test_unknown_personnel_rejected_404(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        resp = client.post("/personnel/ghost-id/interventions", json=CREATE_BODY, headers=_officer_headers())
        assert resp.status_code == 404, resp.text

    def test_persisted_in_interventions_collection(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A")
        created = client.post("/personnel/pers-A/interventions", json=CREATE_BODY, headers=_officer_headers()).json()
        from lib.db import db

        stored = [d for d in db.interventions.docs if d.get("intervention_id") == created["intervention_id"]]
        assert len(stored) == 1
        assert stored[0]["id"] == stored[0]["intervention_id"]
        assert stored[0]["personnel_id"] == "pers-A"
        assert stored[0]["welfare_officer_id"] == "wo-1"
        assert stored[0]["status"] == "OPEN"


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------


class TestList:
    def test_officer_can_list_interventions_for_personnel(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A")
        first = client.post("/personnel/pers-A/interventions", json=CREATE_BODY, headers=_officer_headers()).json()
        second = client.post(
            "/personnel/pers-A/interventions",
            json={**CREATE_BODY, "intervention_type": "COUNSELLING_REFERRAL"},
            headers=_officer_headers(),
        ).json()
        resp = client.get("/personnel/pers-A/interventions", headers=_officer_headers())
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert len(body) == 2
        assert body[0]["intervention_id"] == second["intervention_id"]
        assert body[1]["intervention_id"] == first["intervention_id"]
        for item in body:
            assert item["personnel_id"] == "pers-A"
            assert item["welfare_officer_id"] == "wo-1"

    def test_list_isolated_between_personnel(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A")
        _seed_personnel("pers-B")
        client.post("/personnel/pers-A/interventions", json=CREATE_BODY, headers=_officer_headers())
        body = client.get("/personnel/pers-B/interventions", headers=_officer_headers())
        assert body.status_code == 200
        assert body.json() == []

    def test_list_unknown_personnel_404(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        resp = client.get("/personnel/ghost-id/interventions", headers=_officer_headers())
        assert resp.status_code == 404, resp.text

    def test_legacy_documents_normalized_on_read(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A")
        legacy = client.post(
            "/interventions",
            json={"personnel_id": "pers-A", "intervention_type": "Voluntary check-in", "notes": "legacy note", "status": "NEW"},
            headers=_officer_headers(),
        )
        assert legacy.status_code == 200, legacy.text
        body = client.get("/personnel/pers-A/interventions", headers=_officer_headers()).json()
        assert len(body) == 1
        assert body[0]["intervention_type"] == "OTHER"
        assert body[0]["status"] == "OPEN"
        assert body[0]["welfare_officer_id"] is None
        assert "Voluntary check-in" not in {k: v for k, v in body[0].items()}.get("intervention_type", "")

    def test_legacy_list_endpoint_still_works_with_4g_doc(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A")
        client.post("/personnel/pers-A/interventions", json=CREATE_BODY, headers=_officer_headers())
        resp = client.get("/interventions", headers=_officer_headers())
        assert resp.status_code == 200, resp.text
        assert len(resp.json()) == 1


# ---------------------------------------------------------------------------
# Update / close
# ---------------------------------------------------------------------------


class TestUpdate:
    def _create(self, client) -> str:
        client.post("/personnel/pers-A/interventions", json=CREATE_BODY, headers=_officer_headers())
        return client.get("/personnel/pers-A/interventions", headers=_officer_headers()).json()[0]["intervention_id"]

    def test_officer_can_update_intervention_fields(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A")
        intervention_id = self._create(client)
        resp = client.patch(
            f"/interventions/{intervention_id}",
            json={"status": "FOLLOW_UP", "follow_up_at": "2026-03-20T09:00:00Z"},
            headers=_officer_headers(),
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "FOLLOW_UP"
        assert body["follow_up_at"] is not None
        assert body["updated_at"] is not None
        assert body["intervention_id"] == intervention_id

    def test_officer_can_close_intervention(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A")
        intervention_id = self._create(client)
        resp = client.patch(
            f"/interventions/{intervention_id}",
            json={"status": "CLOSED", "outcome": "Support plan completed", "outcome_notes": "Personnel engaged positively."},
            headers=_officer_headers(),
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "CLOSED"
        assert body["outcome"] == "Support plan completed"
        assert body["outcome_notes"] == "Personnel engaged positively."

    def test_update_unknown_intervention_404(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        resp = client.patch("/interventions/no-such-id", json={"status": "CLOSED"}, headers=_officer_headers())
        assert resp.status_code == 404, resp.text

    def test_update_empty_body_422(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A")
        intervention_id = self._create(client)
        resp = client.patch(f"/interventions/{intervention_id}", json={}, headers=_officer_headers())
        assert resp.status_code == 422, resp.text

    def test_update_invalid_status_422(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A")
        intervention_id = self._create(client)
        resp = client.patch(f"/interventions/{intervention_id}", json={"status": "RESOLVED"}, headers=_officer_headers())
        assert resp.status_code == 422, resp.text

    def test_update_identity_fields_rejected(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A")
        intervention_id = self._create(client)
        resp = client.patch(
            f"/interventions/{intervention_id}",
            json={"status": "CLOSED", "welfare_officer_id": "wo-attacker"},
            headers=_officer_headers(),
        )
        assert resp.status_code == 422, resp.text

    def test_update_legacy_intervention_by_id(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A")
        legacy = client.post(
            "/interventions",
            json={"personnel_id": "pers-A", "intervention_type": "check-in", "notes": "legacy", "status": "NEW"},
            headers=_officer_headers(),
        ).json()
        resp = client.patch(f"/interventions/{legacy['id']}", json={"status": "CLOSED"}, headers=_officer_headers())
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "CLOSED"


# ---------------------------------------------------------------------------
# Auth / RBAC / isolation
# ---------------------------------------------------------------------------


class TestAccessControl:
    @pytest.mark.parametrize("method,path,tries_body", [
        ("POST", "/personnel/pers-A/interventions", CREATE_BODY),
        ("GET", "/personnel/pers-A/interventions", None),
        ("PATCH", "/interventions/any-id", {"status": "CLOSED"}),
    ])
    def test_no_token_blocked(self, client, method, path, tries_body):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A")
        resp = client.request(method, path, json=tries_body)
        assert resp.status_code in (401, 403), resp.text

    @pytest.mark.parametrize("method,path,tries_body", [
        ("POST", "/personnel/pers-A/interventions", CREATE_BODY),
        ("GET", "/personnel/pers-A/interventions", None),
    ])
    def test_personnel_blocked_from_individual_records(self, client, method, path, tries_body):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_user(client, "pers-A", "persona", "PERSONNEL")
        _seed_personnel("pers-A")
        resp = client.request(method, path, json=tries_body, headers=_personnel_headers())
        assert resp.status_code == 403, resp.text

    def test_personnel_cannot_update_another_persons_intervention(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_user(client, "pers-A", "persona", "PERSONNEL")
        _seed_personnel("pers-A")
        client.post("/personnel/pers-A/interventions", json=CREATE_BODY, headers=_officer_headers())
        intervention_id = client.get("/personnel/pers-A/interventions", headers=_officer_headers()).json()[0]["intervention_id"]
        resp = client.patch(f"/interventions/{intervention_id}", json={"status": "CLOSED"}, headers=_personnel_headers())
        assert resp.status_code == 403, resp.text

    def test_commander_blocked_from_individual_records(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_user(client, "cmd-1", "cmdr", "COMMANDER")
        _seed_personnel("pers-A")
        resp = client.post("/personnel/pers-A/interventions", json=CREATE_BODY, headers=_commander_headers())
        assert resp.status_code == 403, resp.text
        resp = client.get("/personnel/pers-A/interventions", headers=_commander_headers())
        assert resp.status_code == 403, resp.text

    def test_denials_are_audited_as_rbac_denial(self, client):
        from lib.db import db

        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_user(client, "pers-A", "persona", "PERSONNEL")
        _seed_personnel("pers-A")
        client.get("/personnel/pers-A/interventions", headers=_personnel_headers())
        denials = [d for d in db.audit_logs.docs if d.get("event_type") == "rbac_denial"]
        assert any(d.get("user_id") == "pers-A" for d in denials)


# ---------------------------------------------------------------------------
# Audit lifecycle
# ---------------------------------------------------------------------------


class TestAuditLifecycle:
    def test_create_updated_and_closed_events(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A")
        created = client.post("/personnel/pers-A/interventions", json=CREATE_BODY, headers=_officer_headers()).json()
        intervention_id = created["intervention_id"]

        events = _audit_events()
        assert [e["event_type"] for e in events] == ["intervention_created"]
        created_event = events[0]
        assert created_event["user_id"] == "wo-1"
        assert created_event["success"] is True
        assert created_event["details"]["intervention_id"] == intervention_id
        assert created_event["details"]["personnel_id"] == "pers-A"

        client.patch(f"/interventions/{intervention_id}", json={"status": "FOLLOW_UP"}, headers=_officer_headers())
        client.patch(f"/interventions/{intervention_id}", json={"status": "CLOSED"}, headers=_officer_headers())
        events = _audit_events()
        assert [e["event_type"] for e in events] == ["intervention_created", "intervention_updated", "intervention_closed"]
        assert events[1]["details"]["status"] == "FOLLOW_UP"
        assert events[2]["details"]["status"] == "CLOSED"
        assert events[2]["details"]["personnel_id"] == "pers-A"

    def test_audit_records_never_log_sensitive_fields(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_personnel("pers-A")
        created = client.post("/personnel/pers-A/interventions", json=CREATE_BODY, headers=_officer_headers()).json()
        client.patch(
            f"/interventions/{created['intervention_id']}",
            json={"status": "CLOSED", "outcome": "secret outcome", "outcome_notes": "secret notes"},
            headers=_officer_headers(),
        )
        for event in _audit_events():
            assert "notes" not in event.get("details", {})
            assert "reason" not in event.get("details", {})
            assert "outcome" not in event.get("details", {})
            assert "outcome_notes" not in event.get("details", {})
            assert "follow_up_at" not in event.get("details", {})
        assert all(set(e.get("details", {}).keys()) <= {"intervention_id", "personnel_id", "intervention_type", "status"} for e in _audit_events())


# ---------------------------------------------------------------------------
# Commander aggregate-only overview
# ---------------------------------------------------------------------------


class TestCommanderOverview:
    def test_overview_leaks_no_intervention_details(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_user(client, "cmd-1", "cmdr", "COMMANDER")
        _seed_personnel("pers-A")
        client.post(
            "/personnel/pers-A/interventions",
            json={**CREATE_BODY, "notes": "sensitive support narrative"},
            headers=_officer_headers(),
        )
        resp = client.get("/overview", headers=_commander_headers())
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert set(body.keys()) == {"personnel_count", "assessments_today", "open_interventions", "high_risk_latest"}
        blob = json.dumps(body)
        assert "sensitive support narrative" not in blob
        assert "welfare_officer_id" not in blob


# ---------------------------------------------------------------------------
# Phase 4A-4F regression protection
# ---------------------------------------------------------------------------


STATIC_FIELDS = {
    "years_of_service": 12.0,
    "hardship_posting_flag": 1,
    "transfer_count_24mo": 3.0,
    "years_in_current_posting": 2.5,
}


def _complete_stress_payloads():
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


def _seed_complete_window(personnel_id: str = "pers-A"):
    from lib.db import db

    _seed_personnel(personnel_id)
    db.personnel.docs[-1].update({**STATIC_FIELDS})
    for week, payload in enumerate(_complete_stress_payloads()):
        db.wellness_logs.docs.append({
            "id": f"rec-{personnel_id}-w{week}",
            "personnel_id": personnel_id,
            "created_at": ANCHOR - (3 - week) * WEEK,
            "payload": {**payload, "week": week},
        })


import json


class TestRegressionProtection:
    def test_4c_welfare_prediction_still_works(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_complete_window("pers-A")
        resp = client.get("/personnel/pers-A/welfare-prediction", headers=_officer_headers())
        assert resp.status_code == 200, resp.text
        assert resp.json()["predicted_band"] in ("Low", "Moderate", "High")

    def test_4f_decision_support_still_works(self, client, inference_engine):
        _require_engine(inference_engine)
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        _seed_complete_window("pers-A")
        resp = client.get("/personnel/pers-A/welfare-decision-support", headers=_officer_headers())
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["decision_state"] in ("SUPPORTED", "LIMITED_EVIDENCE", "INSUFFICIENT_EVIDENCE")
        assert "model_version" not in body

    def test_route_registry_includes_4g_routes(self):
        from routers.welfare import router

        paths = {route.path for route in router.routes}
        assert "/personnel/{personnel_id}/interventions" in paths
        assert "/interventions/{intervention_id}" in paths