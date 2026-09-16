"""Task 3D finalization — RBAC/IDOR authorization-denial audit behavioral tests.

Proves the missing pieces from Task 3D:
- A. RBAC denial creates an audit event (authenticated wrong-role user).
- B. Personnel IDOR attempt creates an audit event identifying the requester.
- C. Welfare Officer / Commander forbidden-access denials create audit events.
- D. Denial audit events never contain secrets / wellness / biometric /
      feature-vector / stack-trace / artifact-path data from the request.
- E. Existing login/registration audit behavior is preserved.
- F. Audit logs are not exposed through any API (public or authenticated).

Same hermetic harness as the 3B/3C suites: real routers + auth/RBAC
dependencies over an in-memory fake Mongo via FastAPI TestClient.  No live
MongoDB is required.
"""

from __future__ import annotations

import datetime
import json
import os

# auth_service requires AUTH_SECRET_KEY before import. Test-only secret,
# >= 32 bytes to silence PyJWT's InsecureKeyLengthWarning for HS256.
os.environ.setdefault("AUTH_SECRET_KEY", "test-only-secret-key-not-for-production-1234567890")

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lib.auth_service import create_access_token, hash_password


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

    async def replace_one(self, query, replacement, upsert=False):
        new_doc = dict(replacement)
        for i, doc in enumerate(self.docs):
            if all(doc.get(k) == v for k, v in query.items()):
                self.docs[i] = new_doc
                return
        if upsert:
            self.docs.append(new_doc)

    async def update_many(self, query, update: dict):
        set_fields = update.get("$set", {})
        for doc in self.docs:
            if all(doc.get(k) == v for k, v in query.items()):
                doc.update(set_fields)

    async def delete_many(self, query):
        self.docs[:] = [d for d in self.docs if not all(d.get(k) == v for k, v in query.items())]

    async def count_documents(self, query):
        return sum(1 for d in self.docs if all(d.get(k) == v for k, v in query.items()))

    def find(self, query=None):
        q = query or {}
        matches = [d for d in self.docs if all(d.get(k) == v for k, v in q.items())]
        return _FakeCursor(matches)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _token(user_id: str, username: str, role: str) -> dict:
    return {"Authorization": f"Bearer {create_access_token(user_id=user_id, username=username, role=role)}"}


def _headers(user_id: str, username: str, role: str) -> dict:
    return _token(user_id, username, role)


def _seed_user(users_col, user_id: str, username: str, role: str) -> None:
    users_col.docs.append({
        "id": user_id,
        "username": username,
        "role": role,
        "active": True,
        "password_hash": hash_password("StrongPass123!"),
    })


def _scenario_payload() -> list[dict]:
    """Distinctive, clearly-sensitive request bodies that must never be logged."""
    return [
        {
            "personnel_id": "pers-B",
            "raw_records": [
                {
                    "personnel_id": "pers-B",
                    "week": 0,
                    "wellness_score_self_report": "SENSITIVE_MARKER_WELLNESS_9876543210",
                    "resting_hr_trend_biometric": "SENSITIVE_MARKER_BIOMETRIC_9876543210",
                    "sleep_hours_biometric": "SENSITIVE_MARKER_FEATURE_9876543210",
                    "weekly_duty_hours": "C:/artifacts/risk_model.pkl",
                }
            ],
        },
        {
            "personnel_id": "pers-B",
            "note": "SENSITIVE_MARKER_NOTE_9876543210",
            "sleep_hr_biometric": "9876543210.5566778",
        },
    ]


@pytest.fixture
def client(monkeypatch):
    """TestClient over the real routers with fake DB collections injected."""
    from lib.db import db

    fake_users = _FakeCollection()
    fake_audit = _FakeCollection()
    monkeypatch.setattr(db, "users", fake_users)
    monkeypatch.setattr(db, "personnel", _FakeCollection())
    monkeypatch.setattr(db, "risk_assessments", _FakeCollection())
    monkeypatch.setattr(db, "interventions", _FakeCollection())
    monkeypatch.setattr(db, "audit_logs", fake_audit)
    for name in ("wellness_logs", "workload_records", "deployment_history", "leave_requests", "status_checks"):
        monkeypatch.setattr(db, name, _FakeCollection())

    from routers.auth import router as auth_router
    from routers.welfare import router as welfare_router

    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(welfare_router)
    return TestClient(app), fake_audit, fake_users


DEFAULT_MARKERS = (
    "SENSITIVE_MARKER_WELLNESS_9876543210",
    "SENSITIVE_MARKER_BIOMETRIC_9876543210",
    "SENSITIVE_MARKER_FEATURE_9876543210",
    "SENSITIVE_MARKER_NOTE_9876543210",
    "9876543210.5566778",
    "C:/artifacts/risk_model.pkl",
    "risk_model.pkl",
    "Traceback",
    "  File ",
)


def _serialize_event(event: dict) -> str:
    """Serialization-safe event dump.

    Audit events carry a required timezone-aware ``timestamp`` datetime; the
    project convention is to serialize such records with ``default=str`` (see
    ``test_denial_events_contain_expected_safe_fields``). This preserves the
    timestamp metadata while letting secret/body inspection read the full
    event. It never weakens the sensitive-data assertions: datetimes are the
    only non-primitive values in audit records, so ``default=str`` cannot mask
    a leaked payload, password, or marker.
    """
    return json.dumps(event, default=str)


def _assert_no_secret_markers(event_bodies: str, extra: tuple[str, ...] = ()) -> None:
    blob = event_bodies.lower()
    forbidden = DEFAULT_MARKERS + extra + ("password", "access_token", "auth_secret_key", "secret", "bcrypt", "sha256")
    for marker in forbidden:
        assert marker.lower() not in blob, f"Audit event leaked forbidden marker '{marker}'"


# ===================================================================
# A. RBAC denial creates an audit event
# ===================================================================

class TestRBACDenialAudited:
    def test_personnel_blocked_from_welfare_officer_list_audited(self, client):
        tc, audit, users = client
        _seed_user(users, "pers-A", "persona", "PERSONNEL")
        resp = tc.get("/personnel", headers=_headers("pers-A", "persona", "PERSONNEL"))
        assert resp.status_code == 403

        events = audit.docs
        assert any(e["event_type"] == "rbac_denial" for e in events)
        event = events[0]
        assert event["user_id"] == "pers-A"
        assert event["username"] == "persona"
        assert event["role"] == "PERSONNEL"
        assert event["endpoint"] == "/personnel"
        assert event["http_method"] == "GET"
        assert event["success"] is False
        assert event["reason"] == "insufficient_role"
        assert event["details"] == {"required_roles": ["WELFARE_OFFICER"]}

    def test_personnel_blocked_from_overview_audited(self, client):
        tc, audit, users = client
        _seed_user(users, "pers-A", "persona", "PERSONNEL")
        resp = tc.get("/overview", headers=_headers("pers-A", "persona", "PERSONNEL"))
        assert resp.status_code == 403
        assert audit.docs[0]["event_type"] == "rbac_denial"
        assert audit.docs[0]["details"] == {"required_roles": ["WELFARE_OFFICER", "COMMANDER"]}

    def test_commander_blocked_from_individual_assessments_audited(self, client):
        tc, audit, users = client
        _seed_user(users, "cmd-1", "cmdr", "COMMANDER")
        resp = tc.get("/assessments", headers=_headers("cmd-1", "cmdr", "COMMANDER"))
        assert resp.status_code == 403
        event = audit.docs[0]
        assert event["event_type"] == "rbac_denial"
        assert event["user_id"] == "cmd-1"
        assert event["role"] == "COMMANDER"
        assert event["success"] is False

    def test_commander_blocked_from_personnel_self_endpoints_audited(self, client):
        tc, audit, users = client
        _seed_user(users, "cmd-1", "cmdr", "COMMANDER")
        for path in ("/my/records", "/my/assessments"):
            audit.docs.clear()
            resp = tc.get(path, headers=_headers("cmd-1", "cmdr", "COMMANDER"))
            assert resp.status_code == 403
            event = audit.docs[0]
            assert event["event_type"] == "rbac_denial"
            assert event["endpoint"] == path
            assert event["details"] == {"required_roles": ["PERSONNEL"]}

    def test_personnel_blocked_from_post_predict_via_role_gate_audited(self, client):
        # COMMANDER is denied by the role gate (not ownership): rbac_denial, not idor_denial.
        tc, audit, users = client
        _seed_user(users, "cmd-1", "cmdr", "COMMANDER")
        resp = tc.post("/predict", json={"personnel_id": "pers-B", "raw_records": [{"a": 1}]},
                       headers=_headers("cmd-1", "cmdr", "COMMANDER"))
        assert resp.status_code == 403
        event = audit.docs[0]
        assert event["event_type"] == "rbac_denial"
        assert event["http_method"] == "POST"
        assert "idor" not in event["event_type"]


# ===================================================================
# B. Personnel IDOR attempt creates an audit event
# ===================================================================

class TestIDORDenialAudited:
    @pytest.fixture
    def ab_personnel(self, client):
        tc, audit, users = client
        _seed_user(users, "pers-A", "persona", "PERSONNEL")
        _seed_user(users, "pers-B", "personb", "PERSONNEL")
        headers_a = _headers("pers-A", "persona", "PERSONNEL")
        return tc, audit, headers_a

    def test_predict_for_another_personnel_403_and_audit(self, ab_personnel):
        tc, audit, headers_a = ab_personnel
        resp = tc.post("/predict", json={"personnel_id": "pers-B", "raw_records": [{"a": 1}]}, headers=headers_a)
        assert resp.status_code == 403

        event = audit.docs[0]
        assert event["event_type"] == "idor_denial"
        assert event["user_id"] == "pers-A"
        assert event["username"] == "persona"
        assert event["role"] == "PERSONNEL"
        assert event["endpoint"] == "/predict"
        assert event["http_method"] == "POST"
        assert event["success"] is False
        assert event["reason"] == "personnel_scope_violation"
        assert event["details"] == {"target_personnel_id": "pers-B"}
        # The denial response itself leaks no target id or resource content.
        assert "pers-B" not in json.dumps(resp.json())

    def test_create_record_for_another_personnel_403_and_audit(self, ab_personnel):
        tc, audit, headers_a = ab_personnel
        resp = tc.post("/wellness_logs", json={"personnel_id": "pers-B", "note": "private"}, headers=headers_a)
        assert resp.status_code == 403

        event = audit.docs[0]
        assert event["event_type"] == "idor_denial"
        assert event["endpoint"] == "/wellness_logs"
        assert event["http_method"] == "POST"
        assert event["reason"] == "personnel_scope_violation"
        assert event["details"] == {"target_personnel_id": "pers-B"}
        assert "private" not in json.dumps(resp.json())

    def test_personnel_null_personnel_id_403_and_audit(self, ab_personnel):
        tc, audit, headers_a = ab_personnel
        resp = tc.post("/predict", json={"raw_records": [{"a": 1}]}, headers=headers_a)
        assert resp.status_code == 403
        event = audit.docs[0]
        assert event["event_type"] == "idor_denial"
        assert event["reason"] == "personnel_scope_violation"


# ===================================================================
# C. Welfare Officer / Commander forbidden-access denials are audited
# ===================================================================

class TestOfficerCommanderForbiddenAudited:
    def test_welfare_officer_blocked_from_personnel_self_endpoints_audited(self, client):
        tc, audit, users = client
        _seed_user(users, "wo-1", "welfareo", "WELFARE_OFFICER")
        resp = tc.get("/my/records", headers=_headers("wo-1", "welfareo", "WELFARE_OFFICER"))
        assert resp.status_code == 403
        event = audit.docs[0]
        assert event["event_type"] == "rbac_denial"
        assert event["user_id"] == "wo-1"
        assert event["role"] == "WELFARE_OFFICER"
        assert event["reason"] == "insufficient_role"

    def test_welfare_officer_blocked_from_my_assessments_audited(self, client):
        tc, audit, users = client
        _seed_user(users, "wo-1", "welfareo", "WELFARE_OFFICER")
        resp = tc.get("/my/assessments", headers=_headers("wo-1", "welfareo", "WELFARE_OFFICER"))
        assert resp.status_code == 403
        assert audit.docs[0]["event_type"] == "rbac_denial"

    def test_commander_blocked_from_predict_audited(self, client):
        tc, audit, users = client
        _seed_user(users, "cmd-1", "cmdr", "COMMANDER")
        resp = tc.post("/predict", json={"personnel_id": "any", "raw_records": [{"a": 1}]},
                       headers=_headers("cmd-1", "cmdr", "COMMANDER"))
        assert resp.status_code == 403
        assert audit.docs[0]["event_type"] == "rbac_denial"
        assert audit.docs[0]["endpoint"] == "/predict"

    def test_commander_blocked_from_record_write_audited(self, client):
        tc, audit, users = client
        _seed_user(users, "cmd-1", "cmdr", "COMMANDER")
        resp = tc.post("/wellness_logs", json={"personnel_id": "any", "mood": 5},
                       headers=_headers("cmd-1", "cmdr", "COMMANDER"))
        assert resp.status_code == 403
        assert audit.docs[0]["event_type"] == "rbac_denial"

    def test_commander_blocked_from_demo_seed_audited(self, client):
        tc, audit, users = client
        _seed_user(users, "cmd-1", "cmdr", "COMMANDER")
        resp = tc.post("/demo/seed", json={}, headers=_headers("cmd-1", "cmdr", "COMMANDER"))
        assert resp.status_code == 403
        assert audit.docs[0]["event_type"] == "rbac_denial"

    def test_non_personnel_registration_403_and_anonymous_audit(self, client):
        """Unauthenticated RBAC denial: anonymous safe metadata, no invented identity."""
        tc, audit, _ = client
        resp = tc.post("/auth/register", json={"username": "wanna-be-officer", "password": "SuperSecret123!", "role": "WELFARE_OFFICER"})
        assert resp.status_code == 403
        event = audit.docs[0]
        assert event["event_type"] == "rbac_denial"
        assert event["user_id"] is None
        assert event["role"] is None
        assert event["username"] == "wanna-be-officer"
        assert event["endpoint"] == "/auth/register"
        assert event["http_method"] == "POST"
        assert event["success"] is False
        assert event["reason"] == "public_registration_role_restricted"
        blob = _serialize_event(event).lower()
        assert "SuperSecret123!" not in blob
        assert "password" not in blob


# ===================================================================
# D. Denial audit events never contain secrets / sensitive request data
# ===================================================================

class TestDenialAuditNoSecrets:
    def _scenario_requests(self, client):
        tc, audit, users = client
        _seed_user(users, "pers-A", "persona", "PERSONNEL")
        _seed_user(users, "pers-B", "personb", "PERSONNEL")
        _seed_user(users, "cmd-1", "cmdr", "COMMANDER")
        _seed_user(users, "wo-1", "welfareo", "WELFARE_OFFICER")
        payloads = _scenario_payload()

        # IDOR deny — predict for B with a poisoned body that would be an
        # attractive place to leak wellness/biometric/artifact-path values.
        tc.post("/predict", json=payloads[0], headers=_headers("pers-A", "persona", "PERSONNEL"))
        # IDOR deny — create record for B with a poisoned body.
        tc.post("/wellness_logs", json=payloads[1], headers=_headers("pers-A", "persona", "PERSONNEL"))
        # Commander role-gate deny on predict with a poisoned body.
        tc.post("/predict", json={"personnel_id": "pers-B", "raw_records": [{"wellness_score_self_report": "SENSITIVE_MARKER_WELLNESS_9876543210"}]},
                headers=_headers("cmd-1", "cmdr", "COMMANDER"))
        # Commander role-gate deny on record write with a poisoned body.
        tc.post("/wellness_logs", json={"personnel_id": "pers-B", "note": "SENSITIVE_MARKER_NOTE_9876543210", "mood": 5},
                headers=_headers("cmd-1", "cmdr", "COMMANDER"))
        # Welfare Officer role-gate deny on /my/records (personnel-only).
        tc.get("/my/records", headers=_headers("wo-1", "welfareo", "WELFARE_OFFICER"))
        # Unauthenticated non-PERSONNEL registration rejection.
        tc.post("/auth/register", json={"username": "intruder", "password": "SENSITIVE_MARKER_PW_9876543210", "role": "COMMANDER"})

        return audit

    def test_denial_events_contain_no_secrets(self, client):
        audit = self._scenario_requests(client)
        assert len(audit.docs) >= 6, "Expected multiple denial events"
        for event in audit.docs:
            blob = _serialize_event(event)
            for marker in DEFAULT_MARKERS:
                assert marker.lower() not in blob.lower(), f"Leaked '{marker}' in {event['event_type']}"
            # Structural secret checks on each denial event.
            _assert_no_secret_markers(blob, extra=("SENSITIVE_MARKER_PW_9876543210",))
            assert event["event_type"] in ("rbac_denial", "idor_denial")
            assert event["success"] is False

    def test_denial_events_never_include_request_body(self, client):
        audit = self._scenario_requests(client)
        for event in audit.docs:
            # Only safe scalar metadata may appear; never raw bodies or payload dicts.
            assert "raw_records" not in _serialize_event(event)
            assert "note" not in _serialize_event(event)
            assert "features" not in _serialize_event(event)

    def test_denial_events_contain_expected_safe_fields(self, client):
        audit = self._scenario_requests(client)
        for event in audit.docs:
            body = json.loads(json.dumps(event, default=str))
            assert set(body.keys()) == {
                "id", "event_type", "timestamp", "user_id", "username", "role",
                "endpoint", "http_method", "success", "reason", "details",
            }
            assert isinstance(body["details"], dict)


# ===================================================================
# E. Existing login/registration audit behavior preserved
# ===================================================================

class TestExistingAuditBehaviorPreserved:
    def test_successful_login_still_audits(self, client):
        tc, audit, users = client
        _seed_user(users, "user-1", "testuser", "PERSONNEL")
        resp = tc.post("/auth/login", json={"username": "testuser", "password": "StrongPass123!"})
        assert resp.status_code == 200
        assert len(audit.docs) == 1
        event = audit.docs[0]
        assert event["event_type"] == "login_success"
        assert event["username"] == "testuser"
        assert event["role"] == "PERSONNEL"
        assert event["success"] is True

    def test_failed_login_still_audits(self, client):
        tc, audit, _ = client
        resp = tc.post("/auth/login", json={"username": "nobody", "password": "WrongPass123!"})
        assert resp.status_code == 401
        event = audit.docs[0]
        assert event["event_type"] == "login_failure"
        assert event["success"] is False

    def test_registration_still_audits(self, client):
        tc, audit, _ = client
        resp = tc.post("/auth/register", json={"username": "newpers", "password": "NewPass123!", "role": "PERSONNEL"})
        assert resp.status_code == 200
        event = audit.docs[0]
        assert event["event_type"] == "registration"
        assert event["role"] == "PERSONNEL"
        assert event["success"] is True


# ===================================================================
# F. Audit logs are never exposed through APIs
# ===================================================================

class TestAuditLogsNotExposed:
    @pytest.mark.parametrize("role,user_id,username", [
        (None, None, None),
        ("PERSONNEL", "pers-A", "persona"),
        ("WELFARE_OFFICER", "wo-1", "welfareo"),
        ("COMMANDER", "cmd-1", "cmdr"),
    ])
    def test_audit_logs_endpoint_unreachable(self, client, role, user_id, username):
        tc, audit, users = client
        if role:
            _seed_user(users, user_id, username, role)
            headers = _headers(user_id, username, role)
        else:
            headers = {}
        for path in ("/audit_logs", "/api/audit_logs", "/auth/audit_logs", "/overview/audit_logs"):
            resp = tc.get(path, headers=headers)
            assert resp.status_code == 404, f"{path} must not resolve for {role}"

    def test_audit_events_never_returned_in_responses(self, client):
        tc, audit, users = client
        _seed_user(users, "pers-A", "persona", "PERSONNEL")
        _seed_user(users, "pers-B", "personb", "PERSONNEL")
        # Trigger a few denial events, then verify no legitimate endpoint returns them.
        tc.post("/predict", json={"personnel_id": "pers-B", "raw_records": [{"a": 1}]},
                headers=_headers("pers-A", "persona", "PERSONNEL"))
        tc.get("/personnel", headers=_headers("pers-A", "persona", "PERSONNEL"))
        assert len(audit.docs) >= 2
        for path, method in (("/my/records", "GET"), ("/my/assessments", "GET"), ("/profile", "GET"), ("/me", "GET")):
            resp = tc.request(method, path, headers=_headers("pers-A", "persona", "PERSONNEL"))
            assert "event_type" not in resp.text
            assert "audit" not in resp.text.lower()