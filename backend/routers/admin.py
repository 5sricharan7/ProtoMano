"""Admin portal router (Task 5.5).

System-administration surface for the narrow ADMIN realm.  Every endpoint here
is protected by ``require_admin``: no other role (PERSONNEL, WELFARE_OFFICER,
COMMANDER) and no anonymous caller can reach any admin route.  Every
administrative mutation is audited via the shared denial/audit helpers.

Security boundaries honored in this router:
  - ADMIN accounts can NEVER be created via an API (bootstrap-only via seed.py).
  - Only WELFARE_OFFICER / COMMANDER can be provisioned (``AdminUserCreate``
    with ``extra="forbid"`` rejects role escalation at the schema boundary).
  - Listings expose only safe account metadata; password hashes, tokens and
    private welfare data are never returned.
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from lib.audit_service import audit_log
from lib.auth_deps import get_current_user
from lib.auth_service import ALGORITHM, TOKEN_EXPIRE_MINUTES, hash_password
from lib.db import db
from lib.rbac_deps import require_admin
from models.auth import (
    AdminAdminSummary,
    AdminAuditEvent,
    AdminSystemStatus,
    AdminUserCreate,
    AdminUserStatusUpdate,
    AdminUserSummary,
)
from routers.welfare import engine as welfare_engine

router = APIRouter(prefix="/admin", tags=["admin"])
logger = logging.getLogger(__name__)

# Safe projection for admin account listings: identity/access metadata only.
# password_hash, tokens and any other stored secret are never selected.
_USER_LIST_PROJECTION = {
    "id": 1,
    "username": 1,
    "role": 1,
    "active": 1,
    "created_at": 1,
    "updated_at": 1,
    "_id": 0,
}


def _to_summary(doc: dict) -> AdminUserSummary:
    return AdminUserSummary(
        id=doc["id"],
        username=doc["username"],
        role=doc["role"],
        active=doc.get("active", True),
        # ``created_at``/``updated_at`` are drift-tolerant: accounts provisioned by
        # earlier seed versions predate these fields徙 - see legacy schema, keep
        # letting ADMIN list them instead of 500'ing.
        created_at=doc.get("created_at"),
        updated_at=doc.get("updated_at"),
    )


@router.get("/me", response_model=AdminAdminSummary)
async def admin_me(current_user: dict = Depends(require_admin)) -> AdminAdminSummary:
    """ADMIN — Confirm the authenticated admin identity.

    Only the narrow realm signature (never secrets).  A non-admin caller is
    rejected by ``require_admin`` with an audited 403 before this runs.
    """
    return AdminAdminSummary(
        user_id=current_user["user_id"],
        username=current_user["username"],
        role=current_user["role"],
        active=current_user["active"],
    )


@router.get("/status", response_model=AdminSystemStatus)
async def admin_status(current_user: dict = Depends(require_admin)) -> AdminSystemStatus:
    """ADMIN — Safe system/authentication status for the admin landing page.

    Contains only non-secret operational metadata: JWT authentication config,
    database reachability and model metadata where safely available.  Never
    credentials, connection strings, private keys or welfare data.
    """
    # Database reachability: a plain ping; the connection string is never returned.
    database_state = {"status": "ok"}
    try:
        await db.client.admin.command({"ping": 1})
    except Exception:
        database_state = {"status": "unreachable"}

    authentication_state: dict = {
        "provider": "jwt",
        "algorithm": ALGORITHM,
        "token_expire_minutes": TOKEN_EXPIRE_MINUTES,
        "session_boundary_clear_on_signout": True,
        "active_accounts": await db.users.count_documents({}),
    }

    model_state: Optional[dict] = None
    try:
        info = welfare_engine.info()
        model_state = {
            "product_name": info.get("product_name"),
            "model_version": info.get("model_version"),
            "feature_version": info.get("feature_version"),
            "feature_count": info.get("feature_count"),
            "preprocessing_status": info.get("preprocessing_status"),
            "ready": welfare_engine.risk_model is not None and welfare_engine.preprocessing_pipeline is not None,
        }
    except Exception:
        model_state = {"ready": False}

    return AdminSystemStatus(
        authentication=authentication_state,
        database=database_state,
        model=model_state,
    )


@router.get("/users", response_model=list[AdminUserSummary])
async def admin_list_users(current_user: dict = Depends(require_admin)) -> list[AdminUserSummary]:
    """ADMIN — List authorized accounts.

    Safe metadata only: username, role, active state, created/updated.  Never
    password hashes, tokens, secret material or welfare records.
    """
    docs = await db.users.find({}, _USER_LIST_PROJECTION).sort("created_at", -1).to_list(1000)
    return [_to_summary(doc) for doc in docs]


@router.post("/users", response_model=AdminUserSummary, status_code=status.HTTP_201_CREATED)
async def admin_create_user(payload: AdminUserCreate, current_user: dict = Depends(require_admin)) -> AdminUserSummary:
    """ADMIN — Provision a WELFARE_OFFICER or COMMANDER account.

    The role is restricted to officer/commander by ``ProvisionRole`` with
    ``extra="forbid"``; no other role (not even ADMIN) can be requested through
    this endpoint, so provisioning can never escalate beyond the granted set.
    """
    username = payload.username.strip()
    if not username:
        raise HTTPException(status_code=422, detail="Username is required")

    existing = await db.users.find_one({"username": username})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already in use",
        )

    now = datetime.now(timezone.utc)
    user_doc = {
        "id": str(uuid4()),
        "username": username,
        "role": payload.role,
        "active": True,
        "password_hash": hash_password(payload.password),
        "created_at": now,
        "updated_at": now,
    }
    await db.users.insert_one(user_doc)

    await audit_log(
        "admin_user_created",
        user_id=current_user["user_id"],
        username=current_user["username"],
        role=current_user["role"],
        endpoint="/admin/users",
        http_method="POST",
        success=True,
        details={"provisioned_username": username, "provisioned_role": payload.role},
    )
    logger.info("ADMIN %s provisioned %s account: %s", current_user["username"], payload.role, username)

    return _to_summary(user_doc)


@router.patch("/users/{user_id}/status", response_model=AdminUserSummary)
async def admin_update_user_status(
    user_id: str,
    payload: AdminUserStatusUpdate,
    current_user: dict = Depends(require_admin),
) -> AdminUserSummary:
    """ADMIN — Activate or deactivate an account.

    The only mutation supported on an existing account in this checkpoint.
    Deactivating the acting admin's own account is refused: an ADMIN cannot
    lock themselves out of the admin realm.
    """
    if user_id == current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Administrative self-deactivation is not allowed",
        )

    user = await db.users.find_one({"id": user_id})
    if not user:
        await audit_log(
            "admin_user_status_changed",
            user_id=current_user["user_id"],
            username=current_user["username"],
            role=current_user["role"],
            endpoint=f"/admin/users/{user_id}/status",
            http_method="PATCH",
            success=False,
            reason="target_not_found",
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    await db.users.update_one({"id": user_id}, {"$set": {"active": payload.active, "updated_at": datetime.now(timezone.utc)}})
    updated = await db.users.find_one({"id": user_id}, _USER_LIST_PROJECTION)

    await audit_log(
        "admin_user_status_changed",
        user_id=current_user["user_id"],
        username=current_user["username"],
        role=current_user["role"],
        endpoint=f"/admin/users/{user_id}/status",
        http_method="PATCH",
        success=True,
        details={"target_username": user["username"], "active": payload.active},
    )
    logger.info("ADMIN %s set active=%s for %s", current_user["username"], payload.active, user["username"])

    return _to_summary(updated)


@router.get("/audit", response_model=list[AdminAuditEvent])
async def admin_audit(current_user: dict = Depends(require_admin), limit: int = 50) -> list[AdminAuditEvent]:
    """ADMIN — Recent security/audit events (safe metadata only).

    Audit records never contain passwords, hashes, tokens or raw welfare data
    (enforced by the shared audit helper), so listing them cannot leak them.
    ``limit`` is bounded server-side to prevent unbounded reads.
    """
    cap = max(1, min(int(limit), 200))
    docs = await db.audit_logs.find({}).sort("timestamp", -1).limit(cap).to_list(cap)
    return [AdminAuditEvent(**doc) for doc in docs]