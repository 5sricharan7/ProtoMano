"""Provision the demo accounts that drive the demo workspace flow.

Flow: Demo Access -> choose workspace -> REAL login -> backend verifies the
JWT role -> correct dashboard (Personnel / Welfare Officer / Commander / Admin).

We deliberately do NOT invent a second authentication mechanism: the backend
already models and enforces every role (`models/auth.py` UserRole =
PERSONNEL | WELFARE_OFFICER | COMMANDER | ADMIN) and `/auth/register`
intentionally supports only PERSONNEL self-service.  These accounts simply give
the demo real, password-authenticated identities for each workspace.

ADMIN is bootstrap-only: provisioned HERE (seed.py), never via any API.  The
admin router (`routers/admin.py`) can only provision WELFARE_OFFICER /
COMMANDER accounts, so no API surface — not even ADMIN — can mint a second
ADMIN.  Re-running is idempotent: an existing username is never modified.

Accounts (documented demo credentials, printed on every run):

    demo_personnel / Demo@Personnel1   -> PERSONNEL
    demo_officer   / Demo@Officer1     -> WELFARE_OFFICER
    demo_commander / Demo@Commander1   -> COMMANDER
    demo_admin     / Demo@Admin1       -> ADMIN   (bootstrap-only, seed.py)
"""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv

# Load .env BEFORE importing code that requires AUTH_SECRET_KEY: lib.auth_service
# reads the secret at import time (same load-bearing order as server.py).
load_dotenv(Path(__file__).resolve().parent / ".env")

from lib.auth_service import hash_password
from lib.db import db
from models.auth import UserRole

DEMO_ACCOUNTS: list[dict[str, str]] = [
    {"username": "demo_personnel", "password": "Demo@Personnel1", "role": "PERSONNEL"},
    {"username": "demo_officer", "password": "Demo@Officer1", "role": "WELFARE_OFFICER"},
    {"username": "demo_commander", "password": "Demo@Commander1", "role": "COMMANDER"},
    {"username": "demo_admin", "password": "Demo@Admin1", "role": "ADMIN"},
]


def _validate_accounts() -> None:
    allowed = set(UserRole.__args__)
    for account in DEMO_ACCOUNTS:
        if account["role"] not in allowed:
            raise ValueError(f"Invalid demo role in seed: {account['role']}")


async def provision_demo_accounts() -> list[str]:
    """Create any missing demo accounts; returns the usernames it created.

    Existing usernames are left untouched so a demo whose officer changed the
    demo credentials is never silently reset on re-run.
    """
    _validate_accounts()
    now = datetime.now(timezone.utc)
    created: list[str] = []
    for account in DEMO_ACCOUNTS:
        existing = await db.users.find_one({"username": account["username"]})
        if existing is not None:
            continue
        await db.users.insert_one(
            {
                "id": str(uuid4()),
                "username": account["username"],
                "role": account["role"],
                "active": True,
                "password_hash": hash_password(account["password"]),
                "is_demo_user": True,
                "created_at": now,
                "updated_at": now,
            }
        )
        created.append(account["username"])
    return created


async def main() -> None:
    created = await provision_demo_accounts()
    print("Demo accounts ready (idempotent provisioning):")
    for account in DEMO_ACCOUNTS:
        print(f"  {account['username']:<16} {account['password']:<20} {account['role']}")
    status = ", ".join(created) if created else "none (all already present)"
    print(f"Created now: {status}")


if __name__ == "__main__":
    asyncio.run(main())