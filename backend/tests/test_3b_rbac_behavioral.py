"""Task 3B — Focused RBAC + IDOR behavioral tests.

These tests exercise the real authorization logic using an in-memory fake
MongoDB (no live Mongo required) and a TestClient app.  The mini-app omits
the server.py lifespan to avoid background index builds, but imports the
same routers and auth modules so the dependency chain is real.

Prerequisites:
    - Python packages: fastapi, pydantic, pyjwt, passlib, httpx, pytest,
      pandas, scikit-learn, lightgbm (already in system python for this
      project).
    - AUTH_SECRET_KEY must be importable before auth_service loads; we set it
      eagerly at module top.
    - The LightGBM/preprocessing artifacts must exist for the predict success
      path to reach the engine (the test still works if the engine is not
      loaded; it returns 503, which we accept for the self-predict path).
"""

from __future__ import annotations

import asyncio
import datetime
import os

# ---------------------------------------------------------------------------
# Set required env BEFORE any backend module is imported
# ---------------------------------------------------------------------------
os.environ.setdefault("AUTH_SECRET_KEY", "test-only-secret-key-not-for-production-1234567890")

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from lib.auth_service import create_access_token, hash_password

BACKEND_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Lightweight in-memory fake collections (minimal interface)
# ---------------------------------------------------------------------------

class _FakeCursor:
    """Mimics motor cursor with sort(...).to_list(n)."""

    def __init__(self, docs):
        self._docs = list(docs)

    def sort(self, *args, **kwargs):
        # welfare.py always sorts on a single field; ignore direction for test simplicity
        return self

    async def to_list(self, length: int | None = None) -> list[dict]:
        if length is not None:
            return list(self._docs[:length])
        return list(self._docs)


class _FakeCollection:
    """Stores dicts in-memory. Implements the subset of the motor API used
    by the welfare + auth routers: find_one, find().sort().to_list(),
    insert_one, replace_one, update_many, delete_many, count_documents.
    """

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
# Helper: register a user through the real register endpoint
# ---------------------------------------------------------------------------

def _register_user(client: TestClient, username: str, password: str, role: str = "PERSONNEL") -> dict:
    """Register a user and return the response JSON (includes access_token)."""
    return client.post("/auth/register", json={"username": username, "password": password, "role": role}).json()


def _make_token(user_id: str, username: str, role: str) -> str:
    """Issue a real JWT token without hitting the DB."""
    return create_access_token(user_id=user_id, username=username, role=role)


# ---------------------------------------------------------------------------
# Mini-app fixture (no server.py, avoids lifespan + mongo startup)
# ---------------------------------------------------------------------------

@pytest.fixture
def client(monkeypatch):
    """Build a TestClient with fake DB collections injected via monkeypatch."""
    from lib.db import db

    fake_users = _FakeCollection()
    fake_personnel = _FakeCollection()
    fake_risk = _FakeCollection()
    fake_interventions = _FakeCollection()
    fake_audit = _FakeCollection()
    fake_collections = {name: _FakeCollection() for name in ("wellness_logs", "workload_records", "deployment_history", "leave_requests")}

    monkeypatch.setattr(db, "users", fake_users)
    monkeypatch.setattr(db, "personnel", fake_personnel)
    monkeypatch.setattr(db, "risk_assessments", fake_risk)
    monkeypatch.setattr(db, "interventions", fake_interventions)
    monkeypatch.setattr(db, "audit_logs", fake_audit)
    for name, col in fake_collections.items():
        monkeypatch.setattr(db, name, col)

    # Also patch db.status_checks if server module is ever imported
    monkeypatch.setattr(db, "status_checks", _FakeCollection())

    # Build a minimal app without the server lifespan (avoids ensure_indexes)
    from routers.auth import router as auth_router
    from routers.welfare import router as welfare_router

    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(welfare_router)

    return TestClient(app), {
        "users": fake_users,
        "personnel": fake_personnel,
        "risk": fake_risk,
        "interventions": fake_interventions,
        "audit": fake_audit,
        **fake_collections,
    }


# ===================================================================
# 1. RBAC dependency unit tests (direct invocation, no HTTP)
# ===================================================================

class TestRBACDependencies:
    """Verify role-gating dependencies reject wrong roles and allow correct ones."""

    @staticmethod
    def _run(coro):
        return asyncio.run(coro)

    def test_require_welfare_officer_allows_officer(self):
        from lib.rbac_deps import require_welfare_officer
        result = self._run(require_welfare_officer({"role": "WELFARE_OFFICER", "user_id": "u1", "username": "w1", "active": True}))
        assert result["role"] == "WELFARE_OFFICER"

    def test_require_welfare_officer_rejects_personnel(self, monkeypatch):
        from lib.db import db
        monkeypatch.setattr(db, "audit_logs", _FakeCollection())
        from lib.rbac_deps import require_welfare_officer
        with pytest.raises(Exception, match="403"):
            self._run(require_welfare_officer({"role": "PERSONNEL"}))

    def test_require_welfare_officer_rejects_commander(self, monkeypatch):
        from lib.db import db
        monkeypatch.setattr(db, "audit_logs", _FakeCollection())
        from lib.rbac_deps import require_welfare_officer
        with pytest.raises(Exception, match="403"):
            self._run(require_welfare_officer({"role": "COMMANDER"}))

    def test_require_any_role_allows_matching(self):
        from lib.rbac_deps import require_any_role
        dep = require_any_role("PERSONNEL", "WELFARE_OFFICER")
        for role in ("PERSONNEL", "WELFARE_OFFICER"):
            result = self._run(dep({"role": role, "user_id": "u1", "username": "x", "active": True}))
            assert result["role"] == role

    def test_require_any_role_rejects_commander(self, monkeypatch):
        from lib.db import db
        monkeypatch.setattr(db, "audit_logs", _FakeCollection())
        from lib.rbac_deps import require_any_role
        dep = require_any_role("PERSONNEL", "WELFARE_OFFICER")
        with pytest.raises(Exception, match="403"):
            self._run(dep({"role": "COMMANDER"}))


# ===================================================================
# 2. Registration: role manipulation prevention
# ===================================================================

class TestRegistrationRoleGuard:
    """Public registration endpoint must only allow PERSONNEL, and the
    server must store the authoritative PERSONNEL constant, never the
    client-supplied role value."""

    def test_register_allows_personnel(self, client):
        tc, _ = client
        resp = tc.post("/auth/register", json={"username": "p1", "password": "StrongPass1!", "role": "PERSONNEL"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["role"] == "PERSONNEL"
        assert "access_token" in body

    def test_register_rejects_welfare_officer(self, client):
        tc, _ = client
        resp = tc.post("/auth/register", json={"username": "w1", "password": "StrongPass1!", "role": "WELFARE_OFFICER"})
        assert resp.status_code == 403
        assert "restricted" in resp.json()["detail"].lower()

    def test_register_rejects_commander(self, client):
        tc, _ = client
        resp = tc.post("/auth/register", json={"username": "c1", "password": "StrongPass1!", "role": "COMMANDER"})
        assert resp.status_code == 403

    def test_registered_user_stored_as_personnel_even_if_payload_says_commander(self, client):
        """Simulate a tampered payload: accept only PERSONNEL regardless."""
        tc, fakes = client
        resp = tc.post("/auth/register", json={"username": "hack", "password": "StrongPass1!", "role": "COMMANDER"})
        assert resp.status_code == 403  # blocked at boundary, never stored
        assert len(fakes["users"].docs) == 0

    def test_duplicate_username_rejected(self, client):
        tc, _ = client
        tc.post("/auth/register", json={"username": "dup", "password": "StrongPass1!", "role": "PERSONNEL"})
        resp = tc.post("/auth/register", json={"username": "dup", "password": "StrongPass1!", "role": "PERSONNEL"})
        assert resp.status_code == 409

    def test_login_returns_role_from_db(self, client):
        """Verify role in token comes from stored record, not client input."""
        tc, fakes = client
        # Directly insert a WELFARE_OFFICER user in the fake DB
        fakes["users"].docs.append({
            "id": "wo-1",
            "username": "wo_user",
            "role": "WELFARE_OFFICER",
            "active": True,
            "password_hash": hash_password("StrongPass1!"),
        })
        resp = tc.post("/auth/login", json={"username": "wo_user", "password": "StrongPass1!"})
        assert resp.status_code == 200
        assert resp.json()["role"] == "WELFARE_OFFICER"


# ===================================================================
# 3. Unauthenticated access blocks
# ===================================================================

class TestUnauthenticatedBlocked:
    """Endpoints that require authentication must reject anonymous requests."""

    @pytest.mark.parametrize("method,path", [
        ("GET",  "/personnel"),
        ("GET",  "/overview"),
        ("GET",  "/assessments"),
        ("GET",  "/interventions"),
    ])
    def test_no_token_returns_403(self, client, method, path):
        tc, _ = client
        resp = tc.request(method, path)
        # HTTPBearer returns 403 when Authorization header is absent
        assert resp.status_code in (401, 403)


# ===================================================================
# 4. COMMANDER blocked from all individual welfare endpoints
# ===================================================================

class TestCommanderBlockedFromIndividualData:
    """COMMANDER must not be able to access individual personnel, risk,
    intervention, or wellness endpoints."""

    @pytest.fixture
    def commander_client(self, client):
        tc, fakes = client
        # Insert a COMMANDER user directly
        fakes["users"].docs.append({
            "id": "cmd-1",
            "username": "cmdr",
            "role": "COMMANDER",
            "active": True,
            "password_hash": hash_password("StrongPass1!"),
        })
        token = _make_token("cmd-1", "cmdr", "COMMANDER")
        headers = {"Authorization": f"Bearer {token}"}
        return tc, headers

    @pytest.mark.parametrize("method,path", [
        ("GET",  "/personnel"),
        ("GET",  "/assessments"),
        ("GET",  "/interventions"),
    ])
    def test_read_endpoints_reject_commander(self, commander_client, method, path):
        tc, headers = commander_client
        if path == "/demo/personnel":
            pytest.skip("demo/personnel is synthetic and available to all authenticated users")
        resp = tc.request(method, path, headers=headers)
        assert resp.status_code == 403, f"{method} {path} should be 403 for COMMANDER"

    def test_predict_rejects_commander(self, commander_client):
        tc, headers = commander_client
        resp = tc.post("/predict", json={"personnel_id": "any-id", "raw_records": [{}]}, headers=headers)
        assert resp.status_code == 403

    def test_seed_rejects_commander(self, commander_client):
        tc, headers = commander_client
        resp = tc.post("/demo/seed", json={}, headers=headers)
        assert resp.status_code == 403

    def test_create_record_rejects_commander(self, commander_client):
        tc, headers = commander_client
        resp = tc.post(
            "/wellness_logs",
            json={"personnel_id": "any-id", "mood": 7},
            headers=headers,
        )
        assert resp.status_code == 403


# ===================================================================
# 5. PERSONNEL IDOR protection
# ===================================================================

class TestPersonnelIDORProtection:
    """PERSONNEL must only be able to predict and create records for
    themselves (user_id == personnel_id)."""

    @pytest.fixture
    def personnel_client(self, client):
        tc, fakes = client
        fakes["users"].docs.append({
            "id": "pers-1",
            "username": "pers1",
            "role": "PERSONNEL",
            "active": True,
            "password_hash": hash_password("StrongPass1!"),
        })
        token = _make_token("pers-1", "pers1", "PERSONNEL")
        headers = {"Authorization": f"Bearer {token}"}
        return tc, headers

    def test_predict_for_another_personnel_id_returns_403(self, personnel_client):
        tc, headers = personnel_client
        resp = tc.post(
            "/predict",
            json={"personnel_id": "someone-else", "raw_records": [{"a": 1}]},
            headers=headers,
        )
        assert resp.status_code == 403, "Personnel predicting for another must get 403"
        assert "themselves" in resp.json()["detail"].lower()

    def test_create_record_for_another_returns_403(self, personnel_client):
        tc, headers = personnel_client
        resp = tc.post(
            "/wellness_logs",
            json={"personnel_id": "someone-else", "note": "test"},
            headers=headers,
        )
        assert resp.status_code == 403, "Personnel creating record for another must get 403"

    def test_predict_with_null_personnel_id_returns_403(self, personnel_client):
        tc, headers = personnel_client
        resp = tc.post(
            "/predict",
            json={"raw_records": [{"a": 1}]},  # personnel_id defaults to None
            headers=headers,
        )
        assert resp.status_code == 403, "Personnel with null personnel_id should be blocked"

    def test_create_record_for_self_accepted(self, personnel_client):
        """Self-owning record (personnel_id == own user_id) should not be 403."""
        tc, headers = personnel_client
        resp = tc.post(
            "/wellness_logs",
            json={"personnel_id": "pers-1", "mood": 8},
            headers=headers,
        )
        # Accept 200 or 500 (dependency chain may fail on unrelated infra);
        # the critical assertion is it is NOT 403.
        assert resp.status_code != 403, "Personnel creating own record must not be 403"


# ===================================================================
# 6. WELFARE_OFFICER: authorized access to individual data
# ===================================================================

class TestWelfareOfficerAuthorized:
    """WELFARE_OFFICER must have full access to personnel, assessments,
    interventions, predict, create_record, and demo seed."""

    @pytest.fixture
    def wo_client(self, client):
        tc, fakes = client
        fakes["users"].docs.append({
            "id": "wo-1",
            "username": "wo1",
            "role": "WELFARE_OFFICER",
            "active": True,
            "password_hash": hash_password("StrongPass1!"),
        })
        token = _make_token("wo-1", "wo1", "WELFARE_OFFICER")
        headers = {"Authorization": f"Bearer {token}"}
        return tc, headers, fakes

    @pytest.mark.parametrize("method,path", [
        ("GET",  "/personnel"),
        ("GET",  "/overview"),
        ("GET",  "/assessments"),
        ("GET",  "/interventions"),
        ("GET",  "/model-info"),
    ])
    def test_read_endpoints_accept_officer(self, wo_client, method, path):
        tc, headers, _ = wo_client
        resp = tc.request(method, path, headers=headers)
        # 200 = normal success; 503 = engine not loaded (acceptable in test env)
        assert resp.status_code in (200, 503), f"{method} {path} got {resp.status_code}"

    def test_predict_for_another_personnel_allowed(self, wo_client):
        """WELFARE_OFFICER may run prediction for any personnel (no ownership check)."""
        tc, headers, _ = wo_client
        resp = tc.post(
            "/predict",
            json={"personnel_id": "anyone", "raw_records": [{"a": 1}]},
            headers=headers,
        )
        # 200 = full inference success; 503 = engine not loaded; 422 = validation
        assert resp.status_code != 403, "Welfare officer predict must not be 403"

    def test_create_record_for_any_personnel_allowed(self, wo_client):
        tc, headers, _ = wo_client
        resp = tc.post(
            "/wellness_logs",
            json={"personnel_id": "anyone", "note": "check-in"},
            headers=headers,
        )
        assert resp.status_code == 200, "Welfare officer create_record must succeed"

    def test_seed_demo_data_accepted(self, wo_client):
        """Seed writes shared demo collections; welfare officer is authorized."""
        tc, headers, fakes = wo_client
        # Need the engine loaded for seed; skip if artifacts missing
        resp = tc.post("/demo/seed", json={}, headers=headers)
        # 200 = full success; 503 = engine not loaded
        assert resp.status_code in (200, 503), f"seed got {resp.status_code}"

    def test_interventions_list_empty(self, wo_client):
        tc, headers, _ = wo_client
        resp = tc.get("/interventions", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []


# ===================================================================
# 7. Model-info remains public
# ===================================================================

class TestModelInfoPublic:
    """The /model-info endpoint is public by design."""

    def test_model_info_no_auth_required(self, client):
        tc, _ = client
        resp = tc.get("/model-info")
        assert resp.status_code in (200, 503), "model-info should not require auth"


# ===================================================================
# 8. Source-code presence assertions (defense-in-depth)
# ===================================================================

class TestSourceCodeGuards:
    """Source inspection to ensure authorization patterns persist."""

    @staticmethod
    def _read(relpath: str) -> str:
        return (BACKEND_DIR / relpath).read_text(encoding="utf-8")

    def test_welfare_router_contains_personnel_ownership_check(self):
        src = self._read("routers/welfare.py")
        assert 'current_user["role"] == "PERSONNEL"' in src
        assert 'current_user["user_id"]' in src

    def test_welfare_router_uses_require_any_role_for_predict(self):
        src = self._read("routers/welfare.py")
        # predict and create_record use require_any_role, not bare get_current_user
        assert "require_any_role" in src

    def test_welfare_router_uses_require_welfare_officer_for_seed(self):
        src = self._read("routers/welfare.py")
        # seed_demo_data must use require_welfare_officer, not get_current_user
        import re
        seed_match = re.search(r"async def seed_demo_data\((.*?)\)", src, re.DOTALL)
        assert seed_match is not None
        assert "require_welfare_officer" in seed_match.group(1)

    def test_auth_register_forces_personnel_role(self):
        src = self._read("routers/auth.py")
        assert 'role = "PERSONNEL"' in src, "register must use server-side constant"
        assert "payload.role" not in src or 'payload.role != "PERSONNEL"' in src, "payload.role should only be used for validation, not storage"

    def test_server_status_requires_auth(self):
        src = self._read("server.py")
        assert "get_current_user" in src

    def test_overview_docstring_not_commander(self):
        """Confirm the overview docstring no longer claims COMMANDER access."""
        src = self._read("routers/welfare.py")
        import re
        overview_match = re.search(r"async def overview\((.*?)\).*?\"\"\"(.*?)\"\"\"", src, re.DOTALL)
        assert overview_match is not None
        assert "WELFARE_OFFICER / COMMANDER" not in overview_match.group(2), "overview docstring must not claim COMMANDER access"
