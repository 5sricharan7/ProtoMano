"""Task 5A — Commander aggregate-only unit-level overview tests.

Hermetic harness (same pattern as the 3B/3C/4A-4G suites): real routers +
auth/RBAC dependencies over an in-memory fake Mongo via FastAPI TestClient.
No live MongoDB or backend process required, and no model artifacts needed
(the aggregate endpoints never invoke inference).

Covers:
- reusable demo-account provisioning (`seed.provision_demo_accounts`)
- access control on `/overview/units`: anonymous 401, PERSONNEL 403,
  WELFARE_OFFICER and COMMANDER 200 (matches `/overview`)
- aggregate-only response shape (unit cells + cohort totals, no individuals)
- minimum-group-size suppression: small units return suppressed (None) cells
- threshold unit cells are explicit and un-suppressed
- environment-tunable threshold (`AGGREGATE_MIN_GROUP_SIZE`), clamped >= 1
- deterministic unit ordering (largest first, then name)
"""

from __future__ import annotations

import asyncio
import datetime
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
        if args:
            key = args[0]
            direction = args[1] if len(args) > 1 else 1
        else:
            key = kwargs.get("key")
            direction = kwargs.get("direction", 1)
        reverse = str(direction).strip() in ("-1", "-1.0", "desc")
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
# Harness
# ---------------------------------------------------------------------------

TZ = datetime.timezone.utc


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


def _headers(user_id: str, username: str, role: str) -> dict:
    return {
        "Authorization": f"Bearer {create_access_token(user_id=user_id, username=username, role=role)}"
    }


def _seed_user(client, user_id: str, username: str, role: str):
    from lib.db import db

    db.users.docs.append(
        {
            "id": user_id,
            "username": username,
            "role": role,
            "active": True,
            "password_hash": "unused-in-token-tests",
        }
    )


def _seed_personnel(personnel_id: str, unit: str, name: str = "Test Person"):
    from lib.db import db

    db.personnel.docs.append(
        {
            "id": personnel_id,
            "name": name,
            "service_number": f"SRV-{personnel_id}",
            "rank": "Sepoy",
            "unit": unit,
            "posting": "Field Base",
            "created_at": datetime.datetime(2026, 1, 1, tzinfo=TZ),
        }
    )


def _seed_assessment(personnel_id: str, band: str, is_latest: bool = True):
    from lib.db import db

    db.risk_assessments.docs.append(
        {
            "id": f"{personnel_id}-{band}-{is_latest}",
            "personnel_id": personnel_id,
            "predicted_band": band,
            "is_latest": is_latest,
            "assessed_at": datetime.datetime(2026, 2, 1, tzinfo=TZ),
            "date_key": "2026-02-01",
        }
    )


# ---------------------------------------------------------------------------
# Demo-account provisioning (seed script)
# ---------------------------------------------------------------------------


class TestDemoAccountSeed:
    def test_provisions_three_roles(self, client):
        from lib.db import db
        from seed import provision_demo_accounts

        created = asyncio.run(provision_demo_accounts())

        assert sorted(created) == ["demo_commander", "demo_officer", "demo_personnel"]
        users = {doc["username"]: doc for doc in db.users.docs}
        assert users["demo_personnel"]["role"] == "PERSONNEL"
        assert users["demo_officer"]["role"] == "WELFARE_OFFICER"
        assert users["demo_commander"]["role"] == "COMMANDER"
        for doc in users.values():
            assert doc["active"] is True
            assert doc["password_hash"].startswith("$2")  # real bcrypt hash

    def test_is_idempotent(self, client):
        from lib.db import db
        from seed import provision_demo_accounts

        asyncio.run(provision_demo_accounts())
        officer = next(doc for doc in db.users.docs if doc["username"] == "demo_officer")
        # Mutate the existing record: provisioning must never overwrite it.
        officer.update({"id": "keep-me", "active": False, "password_hash": "KEEP-THIS-HASH"})

        created = asyncio.run(provision_demo_accounts())

        assert created == []
        officer = next(doc for doc in db.users.docs if doc["username"] == "demo_officer")
        assert officer["id"] == "keep-me"  # existing account never overwritten
        assert officer["password_hash"] == "KEEP-THIS-HASH"
        assert officer["active"] is False

    def test_rejects_unknown_role(self, client):
        from seed import DEMO_ACCOUNTS, provision_demo_accounts

        original = list(DEMO_ACCOUNTS)
        DEMO_ACCOUNTS[:] = [{"username": "bad", "password": "Bad@Pass1", "role": "SUPERADMIN"}]
        try:
            with pytest.raises(ValueError):
                asyncio.run(provision_demo_accounts())
        finally:
            DEMO_ACCOUNTS[:] = original

    def test_demo_credentials_are_loginable(self, client):
        from seed import DEMO_ACCOUNTS, provision_demo_accounts

        asyncio.run(provision_demo_accounts())

        for account in DEMO_ACCOUNTS:
            resp = client.post(
                "/auth/login",
                json={"username": account["username"], "password": account["password"]},
            )
            assert resp.status_code == 200, account["username"]
            assert resp.json()["role"] == account["role"]


# ---------------------------------------------------------------------------
# Access control on /overview/units
# ---------------------------------------------------------------------------


class TestAccess:
    def test_anonymous_401(self, client):
        resp = client.get("/overview/units")
        assert resp.status_code == 401

    def test_personnel_blocked_403(self, client):
        _seed_user(client, "pers-A", "persona", "PERSONNEL")
        resp = client.get("/overview/units", headers=_headers("pers-A", "persona", "PERSONNEL"))
        assert resp.status_code == 403

    def test_officer_allowed_200(self, client):
        _seed_user(client, "wo-1", "welfareo", "WELFARE_OFFICER")
        resp = client.get("/overview/units", headers=_headers("wo-1", "welfareo", "WELFARE_OFFICER"))
        assert resp.status_code == 200

    def test_commander_allowed_200(self, client):
        _seed_user(client, "cmd-1", "cmdr", "COMMANDER")
        resp = client.get("/overview/units", headers=_headers("cmd-1", "cmdr", "COMMANDER"))
        assert resp.status_code == 200

    def test_commander_overview_companion_200(self, client):
        _seed_user(client, "cmd-1", "cmdr", "COMMANDER")
        over = client.get("/overview", headers=_headers("cmd-1", "cmdr", "COMMANDER"))
        units = client.get("/overview/units", headers=_headers("cmd-1", "cmdr", "COMMANDER"))
        assert over.status_code == 200 and units.status_code == 200


# ---------------------------------------------------------------------------
# Aggregation + minimum-group-size suppression
# ---------------------------------------------------------------------------


class TestAggregation:
    def test_empty_database(self, client):
        _seed_user(client, "cmd-1", "cmdr", "COMMANDER")
        resp = client.get("/overview/units", headers=_headers("cmd-1", "cmdr", "COMMANDER"))
        assert resp.status_code == 200
        body = resp.json()
        assert body["units"] == []
        assert body["total_personnel_count"] == 0
        assert body["high_risk_latest_total"] == 0
        assert body["suppressed_units"] == 0
        assert body["min_group_size"] == 3

    def test_small_unit_is_suppressed(self, client):
        _seed_user(client, "cmd-1", "cmdr", "COMMANDER")
        _seed_personnel("pers-1", "Northern Support Group")
        _seed_assessment("pers-1", "High", is_latest=True)

        resp = client.get("/overview/units", headers=_headers("cmd-1", "cmdr", "COMMANDER"))
        body = resp.json()

        assert body["total_personnel_count"] == 1
        assert body["high_risk_latest_total"] == 1
        assert body["suppressed_units"] == 1
        assert body["units"] == [
            {
                "unit": "Northern Support Group",
                "personnel_count": None,
                "high_risk_latest": None,
                "suppressed": True,
            }
        ]

    def test_unit_at_threshold_is_reported(self, client):
        _seed_user(client, "cmd-1", "cmdr", "COMMANDER")
        for index in range(3):
            _seed_personnel(f"pers-{index}", "Alpha Unit")
        _seed_assessment("pers-0", "High", is_latest=True)
        _seed_assessment("pers-1", "Low", is_latest=True)
        _seed_assessment("pers-2", "Moderate", is_latest=True)

        resp = client.get("/overview/units", headers=_headers("cmd-1", "cmdr", "COMMANDER"))
        body = resp.json()

        assert body["min_group_size"] == 3
        assert body["suppressed_units"] == 0
        assert body["total_personnel_count"] == 3
        assert body["high_risk_latest_total"] == 1
        assert body["units"] == [
            {
                "unit": "Alpha Unit",
                "personnel_count": 3,
                "high_risk_latest": 1,
                "suppressed": False,
            }
        ]

    def test_mixed_units_sorted_largest_first(self, client):
        _seed_user(client, "cmd-1", "cmdr", "COMMANDER")
        # Beta has threshold count; Zulu and Alpha are small (suppressed).
        for index in range(3):
            _seed_personnel(f"beta-{index}", "Beta Unit")
        _seed_personnel("zulu-1", "Zulu Unit")
        _seed_personnel("alpha-1", "Alpha Unit")
        _seed_assessment("beta-0", "High", is_latest=True)
        _seed_assessment("zulu-1", "High", is_latest=True)

        resp = client.get("/overview/units", headers=_headers("cmd-1", "cmdr", "COMMANDER"))
        body = resp.json()

        # Beta (3) first, then the two single-person units by name.
        assert [u["unit"] for u in body["units"]] == ["Beta Unit", "Alpha Unit", "Zulu Unit"]
        visible = [u for u in body["units"] if not u["suppressed"]]
        assert [u["unit"] for u in visible] == ["Beta Unit"]
        assert body["suppressed_units"] == 2
        assert body["total_personnel_count"] == 5
        assert body["high_risk_latest_total"] == 2

    @pytest.mark.parametrize(
        ("threshold", "expected_suppressed", "expected_personnel"),
        [
            ("2", False, 2),   # below-default cell now visible at threshold 2
            ("5", True, None),  # previously visible cell now suppressed at 5
            ("0", False, 2),    # clamped to >= 1, so threshold 1 reveals the cell
        ],
    )
    def test_threshold_is_tunable_and_clamped(self, client, monkeypatch, threshold, expected_suppressed, expected_personnel):
        _seed_user(client, "cmd-1", "cmdr", "COMMANDER")
        for index in range(2):
            _seed_personnel(f"pers-{index}", "Tango Unit")
        _seed_assessment("pers-0", "Low", is_latest=True)

        monkeypatch.setenv("AGGREGATE_MIN_GROUP_SIZE", threshold)
        resp = client.get("/overview/units", headers=_headers("cmd-1", "cmdr", "COMMANDER"))
        body = resp.json()

        (unit,) = body["units"]
        assert unit["suppressed"] is expected_suppressed
        assert unit["personnel_count"] is expected_personnel

    def test_invalid_threshold_falls_back_to_default(self, client, monkeypatch):
        _seed_user(client, "cmd-1", "cmdr", "COMMANDER")
        monkeypatch.setenv("AGGREGATE_MIN_GROUP_SIZE", "not-a-number")

        resp = client.get("/overview/units", headers=_headers("cmd-1", "cmdr", "COMMANDER"))
        assert resp.status_code == 200
        assert resp.json()["min_group_size"] == 3