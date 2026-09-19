"""Backend authentication models for Manobal-AI.

User identity, password security, and authentication metadata.
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


UserRole = Literal["PERSONNEL", "WELFARE_OFFICER", "COMMANDER", "ADMIN"]

# Roles an ADMIN is allowed to provision. Public signup never receives a role
# channel at all; ADMIN bootstrap is handled solely by the controlled seed.py
# provisioning path (never by an API).
ProvisionRole = Literal["WELFARE_OFFICER", "COMMANDER"]


class UserBase(BaseModel):
    """Base user fields."""

    username: str = Field(min_length=2, max_length=120)
    role: UserRole
    active: bool = True


class UserCreate(UserBase):
    """User creation with plaintext password (only at registration boundary)."""

    password: str = Field(min_length=8, max_length=255)


class User(UserBase):
    """Persisted user (no password field in responses)."""

    id: str
    created_at: datetime
    updated_at: datetime


class UserInDB(User):
    """Internal user record with password hash (never exposed in API)."""

    password_hash: str


class AuthToken(BaseModel):
    """Successful login response."""

    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    role: UserRole


class AuthenticatedUser(BaseModel):
    """Current authenticated user (GET /api/auth/me)."""

    user_id: str
    username: str
    role: UserRole
    active: bool
    created_at: datetime


# --- ADMIN portal models (Task 5.5) ---


class AdminUserCreate(BaseModel):
    """ADMIN — Provision an authorized WELFARE_OFFICER or COMMANDER account.

    ``extra="forbid"`` rejects any unknown field at the schema boundary
    (including an attempted ``ADMIN`` role or smuggled secrets), so a client
    can never escalate the grant through the request body.  ADMIN accounts are
    bootstrap-only (seed.py) and have no API creation surface.
    """

    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=8, max_length=255)
    role: ProvisionRole


class AdminUserStatusUpdate(BaseModel):
    """ADMIN — Toggle only the active/inactive flag of an account.

    The only mutation an admin may make to an existing account in this
    checkpoint.  ``extra="forbid"`` prevents any other field (role, username,
    password) from being changed through this surface.
    """

    model_config = ConfigDict(extra="forbid")

    active: bool


class AdminUserSummary(BaseModel):
    """ADMIN — Safe account metadata row.

    Deliberately excludes password hashes, tokens, secrets, wellness records
    and any private welfare data.  Only what an access manager needs to
    administer authorized access.
    """

    id: str
    username: str
    role: UserRole
    active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AdminSystemStatus(BaseModel):
    """ADMIN — Safe system/authentication status for the admin landing page.

    Only non-secret, non-sensitive operational metadata.  No credentials,
    connection strings, private keys, raw welfare data or model artifacts.
    """

    authentication: dict[str, Any]
    database: dict[str, Any]
    model: dict[str, Any] | None = None


class AdminAuditEvent(BaseModel):
    """ADMIN — One safe recent audit event.

    Mirrors the stored audit record envelope (which never contains passwords,
    hashes, tokens or raw welfare data).  ``details`` is forwarded only from
    the safe reason/details fields the audit helper already permits.
    """

    id: str
    event_type: str
    timestamp: datetime
    user_id: str | None = None
    username: str | None = None
    role: str | None = None
    endpoint: str | None = None
    http_method: str | None = None
    success: bool
    reason: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class AdminAdminSummary(BaseModel):
    """ADMIN — Verified admin identity (GET /api/admin/me)."""

    user_id: str
    username: str
    role: UserRole
    active: bool
    realm: str = "admin"
