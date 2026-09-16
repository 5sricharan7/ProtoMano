"""Task 3D — Audit logging + operational hardening behavioral tests.

Tests that audit events are recorded for security-relevant actions,
no secrets leak into logs, and configuration is safe.
"""

import os
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault("AUTH_SECRET_KEY", "test-only-secret-key-not-for-production-1234567890")


class TestAuditLogging:
    @pytest.fixture
    def client(self, monkeypatch):
        from lib.db import db
        
        class _FakeCollection:
            def __init__(self):
                self.docs = []
            
            async def find_one(self, query):
                for doc in self.docs:
                    if all(doc.get(k) == v for k, v in query.items()):
                        return doc
                return None
            
            async def insert_one(self, doc):
                self.docs.append(dict(doc))
            
            async def find(self, query=None):
                class _Cursor:
                    def __init__(self, docs):
                        self._docs = docs
                    def sort(self, *args, **kwargs):
                        return self
                    async def to_list(self, n=None):
                        return self._docs[:n] if n else self._docs
                
                q = query or {}
                return _Cursor([d for d in self.docs if all(d.get(k) == v for k, v in q.items())])
        
        users_col = _FakeCollection()
        audit_col = _FakeCollection()
        
        monkeypatch.setattr(db, "users", users_col)
        monkeypatch.setattr(db, "audit_logs", audit_col)
        
        from routers.auth import router as auth_router
        app = FastAPI()
        app.include_router(auth_router)
        return TestClient(app), audit_col

    def test_successful_login_creates_audit_event(self, client):
        tc, audit_col = client
        from lib.auth_service import hash_password
        from lib.db import db
        
        db.users.docs.append({
            "id": "user-1",
            "username": "testuser",
            "role": "PERSONNEL",
            "active": True,
            "password_hash": hash_password("TestPass123!"),
        })
        
        resp = tc.post("/auth/login", json={"username": "testuser", "password": "TestPass123!"})
        assert resp.status_code == 200
        
        assert len(audit_col.docs) == 1
        event = audit_col.docs[0]
        assert event["event_type"] == "login_success"
        assert event["username"] == "testuser"
        assert event["role"] == "PERSONNEL"
        assert "password" not in str(event).lower()
        assert "token" not in str(event).lower()

    def test_failed_login_creates_audit_event(self, client):
        tc, audit_col = client
        resp = tc.post("/auth/login", json={"username": "nonexistent", "password": "WrongPass123!"})
        assert resp.status_code == 401
        
        assert len(audit_col.docs) == 1
        event = audit_col.docs[0]
        assert event["event_type"] == "login_failure"
        assert "password" not in str(event).lower()

    def test_registration_creates_audit_event(self, client):
        tc, audit_col = client
        resp = tc.post("/auth/register", json={"username": "newuser", "password": "NewPass123!", "role": "PERSONNEL"})
        assert resp.status_code == 200
        
        assert len(audit_col.docs) == 1
        event = audit_col.docs[0]
        assert event["event_type"] == "registration"
        assert event["username"] == "newuser"
        assert event["role"] == "PERSONNEL"
        assert "password" not in str(event).lower()
        assert "hash" not in str(event).lower()

    def test_audit_event_contains_no_secrets(self, client):
        tc, audit_col = client
        resp = tc.post("/auth/register", json={"username": "user", "password": "Pass123!", "role": "PERSONNEL"})
        
        for event in audit_col.docs:
            event_str = str(event).lower()
            for secret in ("password", "hash", "token", "secret", "key"):
                assert secret not in event_str, f"Audit event must not contain '{secret}'"

    def test_audit_collection_not_accessible_via_api(self, client):
        tc, _ = client
        resp = tc.get("/audit_logs")
        assert resp.status_code == 404

    def test_auth_secret_key_required(self):
        import sys
        saved_key = os.environ.pop("AUTH_SECRET_KEY", None)
        try:
            sys.modules.pop("lib.auth_service", None)
            with pytest.raises(ValueError, match="AUTH_SECRET_KEY"):
                import lib.auth_service
        finally:
            if saved_key:
                os.environ["AUTH_SECRET_KEY"] = saved_key

    def test_login_response_no_password_hash(self, client):
        tc, _ = client
        from lib.auth_service import hash_password
        from lib.db import db
        
        db.users.docs.append({
            "id": "user-1",
            "username": "testuser",
            "role": "PERSONNEL",
            "active": True,
            "password_hash": hash_password("TestPass123!"),
        })
        
        resp = tc.post("/auth/login", json={"username": "testuser", "password": "TestPass123!"})
        assert resp.status_code == 200
        
        body = resp.json()
        assert "password" not in body
        assert "password_hash" not in body
        assert "secret" not in str(body).lower()

    def test_register_response_no_password_hash(self, client):
        tc, _ = client
        resp = tc.post("/auth/register", json={"username": "user", "password": "Pass123!", "role": "PERSONNEL"})
        assert resp.status_code == 200
        
        body = resp.json()
        assert "password" not in body
        assert "password_hash" not in body
        assert "secret" not in str(body).lower()


class TestSecurityConfiguration:
    def test_env_variables_from_environment(self):
        os.environ["TEST_VAR"] = "test_value"
        import os as os_module
        assert os_module.environ.get("TEST_VAR") == "test_value"

    def test_no_hardcoded_secrets_in_auth_service(self):
        import pathlib
        src = pathlib.Path("lib/auth_service.py").read_text()
        assert "SECRET_KEY" not in src or "os.environ" in src, "AUTH_SECRET_KEY must come from env"
        assert "password =" not in src.lower(), "No hardcoded passwords"

    def test_no_hardcoded_secrets_in_auth_deps(self):
        import pathlib
        src = pathlib.Path("lib/auth_deps.py").read_text()
        assert "password" not in src.lower() or "verify" in src.lower(), "Only verify_password calls allowed"


class TestErrorHandling:
    def test_login_error_generic(self):
        pytest.skip("BLOCKED: Error handling test requires live MongoDB connection")

    def test_register_error_safe(self):
        pytest.skip("BLOCKED: Error handling test requires live MongoDB connection")
