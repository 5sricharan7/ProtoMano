"""Backend authentication router.

Login endpoint and authenticated user info endpoint.
"""

import logging
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from lib.auth_service import hash_password, verify_password, create_access_token
from lib.auth_deps import get_current_user
from lib.audit_service import audit_log
from lib.db import db
from models.auth import AuthToken, AuthenticatedUser, UserCreate, UserInDB

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


@router.post("/login", response_model=AuthToken)
async def login(payload: dict):
    """Authenticate with username and password.

    Returns a signed JWT token on success.
    Returns generic 401 on failure (does not reveal whether username or password was incorrect).
    """
    username = payload.get("username", "").strip()
    password = payload.get("password", "")

    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    # Lookup user by username
    user = await db.users.find_one({"username": username})
    if not user:
        await audit_log("login_failure", username=username, endpoint="/auth/login", http_method="POST", success=False, reason="user_not_found")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    # Verify password
    if not verify_password(password, user.get("password_hash", "")):
        await audit_log("login_failure", username=username, endpoint="/auth/login", http_method="POST", success=False, reason="password_mismatch")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    # Check user is active
    if not user.get("active"):
        await audit_log("login_failure", user_id=user["id"], username=username, endpoint="/auth/login", http_method="POST", success=False, reason="user_disabled")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    # Create and return token
    token = create_access_token(
        user_id=user["id"],
        username=user["username"],
        role=user["role"],
    )

    await audit_log("login_success", user_id=user["id"], username=username, role=user["role"], endpoint="/auth/login", http_method="POST", success=True)
    logger.info(f"User {username} (role={user['role']}) authenticated successfully")

    return AuthToken(
        access_token=token,
        user_id=user["id"],
        username=user["username"],
        role=user["role"],
    )


@router.post("/register", response_model=AuthToken)
async def register(payload: UserCreate):
    """Register a new PERSONNEL account only.

    Public self-registration is restricted to PERSONNEL to prevent privilege
    escalation. WELFARE_OFFICER and COMMANDER accounts must be provisioned by
    an administrator (future Task 3C admin lifecycle). The server always
    stores role=PERSONNEL regardless of the client-supplied value: a client
    cannot manipulate the role via the request body.
    """
    # Reject any non-PERSONNEL registration at the API boundary
    if payload.role != "PERSONNEL":
        # Anonymous RBAC denial audit: user is not yet authenticated, so only
        # safe metadata (the client-supplied username and attempted role) is
        # recorded.  No user identity is invented.
        await audit_log(
            "rbac_denial",
            username=payload.username.strip(),
            endpoint="/auth/register",
            http_method="POST",
            success=False,
            reason="public_registration_role_restricted",
            details={"attempted_role": payload.role},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Self-registration is restricted to PERSONNEL role only",
        )
    
    username = payload.username.strip()

    # Check username not already in use
    existing = await db.users.find_one({"username": username})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already in use",
        )

    # Server-authoritative role: never trust a client-supplied role value.
    role = "PERSONNEL"

    # Hash password (never store plaintext)
    password_hash = hash_password(payload.password)

    now = datetime.now(timezone.utc)

    # Create user document
    user_id = str(uuid4())
    user_doc = {
        "id": user_id,
        "username": username,
        "role": role,
        "active": payload.active,
        "password_hash": password_hash,
        "created_at": now,
        "updated_at": now,
    }

    await db.users.insert_one(user_doc)

    await audit_log("registration", user_id=user_id, username=username, role=role, endpoint="/auth/register", http_method="POST", success=True)

    # Create token for new user
    token = create_access_token(
        user_id=user_id,
        username=username,
        role=role,
    )

    logger.info("New PERSONNEL account registered: %s", username)

    return AuthToken(
        access_token=token,
        user_id=user_id,
        username=username,
        role=role,
    )


@router.get("/me", response_model=AuthenticatedUser)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current authenticated user info.

    Protected endpoint: requires valid authentication token.
    Returns only safe public fields, never passwords, hashes, tokens, or secrets.
    """
    # Fetch full user record to get created_at
    user = await db.users.find_one({"id": current_user["user_id"]})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return AuthenticatedUser(
        user_id=current_user["user_id"],
        username=current_user["username"],
        role=current_user["role"],
        active=current_user["active"],
        created_at=user["created_at"],
    )
