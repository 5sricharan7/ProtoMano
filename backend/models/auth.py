"""Backend authentication models for Manobal-AI.

User identity, password security, and authentication metadata.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


UserRole = Literal["PERSONNEL", "WELFARE_OFFICER", "COMMANDER"]


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
