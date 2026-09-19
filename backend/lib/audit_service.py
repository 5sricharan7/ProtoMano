"""Audit logging service for Task 3D.

Records security-relevant events (login, registration, RBAC denials, IDOR attempts)
to a persistent MongoDB collection without exposing sensitive data.
"""

from datetime import datetime, timezone
from typing import Any, Literal, Optional

from fastapi import Request

from lib.db import db


AuditEventType = Literal[
    "login_success",
    "login_failure",
    "registration",
    "rbac_denial",
    "idor_denial",
    "logout",
    "intervention_created",
    "intervention_updated",
    "intervention_closed",
]


async def audit_log(
    event_type: AuditEventType,
    user_id: Optional[str] = None,
    username: Optional[str] = None,
    role: Optional[str] = None,
    endpoint: Optional[str] = None,
    http_method: Optional[str] = None,
    reason: Optional[str] = None,
    success: bool = True,
    details: Optional[dict[str, Any]] = None,
) -> None:
    """Record a security-relevant audit event.

    Safe audit helper: never logs passwords, hashes, tokens, or raw sensitive data.
    All audit records are stored server-side only and inaccessible via API.

    Args:
        event_type: Category of security event
        user_id: Authenticated user ID (if available)
        username: Username (if available, never password)
        role: User role (if available)
        endpoint: Route/action that triggered the event
        http_method: HTTP method (or None for non-HTTP actions)
        reason: Safe reason/category (e.g., "password_mismatch", "invalid_token")
        success: Whether the action succeeded (denials are recorded as False)
        details: Optional safe contextual dict (e.g., attempted_role if RBAC denied)
    """
    record = {
        "id": f"{event_type}-{datetime.now(timezone.utc).timestamp()}",
        "event_type": event_type,
        "timestamp": datetime.now(timezone.utc),
        "user_id": user_id,
        "username": username,
        "role": role,
        "endpoint": endpoint,
        "http_method": http_method,
        "success": success,
        "reason": reason,
        "details": details or {},
    }
    try:
        await db.audit_logs.insert_one(record)
    except Exception as exc:
        # Audit failure should not break the app; log locally
        import logging
        logger = logging.getLogger(__name__)
        logger.error("audit_log insertion failed: %s", exc)


async def log_denial(
    event_type: AuditEventType,
    request: Optional[Request] = None,
    user: Optional[dict[str, Any]] = None,
    *,
    reason: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> None:
    """Reusable authorization/IDOR denial audit helper.

    Derives safe request context (endpoint, HTTP method) and the authenticated
    user identity from the request/current_user, then records a denial event
    with ``success=False``.  Never logs passwords, tokens, request bodies, or
    resource contents.  May be called with a ``None`` request (non-HTTP, e.g.
    direct-call tests); endpoint/method are simply omitted in that case.
    """
    user = user or {}
    await audit_log(
        event_type=event_type,
        user_id=user.get("user_id"),
        username=user.get("username"),
        role=user.get("role"),
        endpoint=request.url.path if request else None,
        http_method=request.method if request else None,
        success=False,
        reason=reason,
        details=details,
    )
