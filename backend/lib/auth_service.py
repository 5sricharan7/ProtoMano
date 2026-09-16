"""Backend authentication service.

Password hashing, token generation, and credential validation.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from passlib.context import CryptContext

# Password hashing context (bcrypt with reasonable parameters)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT configuration
SECRET_KEY = os.environ.get("AUTH_SECRET_KEY", "")
if not SECRET_KEY:
    raise ValueError("AUTH_SECRET_KEY environment variable is required")

ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 1440  # 24 hours


def hash_password(password: str) -> str:
    """Hash a plaintext password securely."""
    return pwd_context.hash(password)


def verify_password(plaintext: str, password_hash: str) -> bool:
    """Verify a plaintext password against a stored hash."""
    return pwd_context.verify(plaintext, password_hash)


def create_access_token(user_id: str, username: str, role: str, expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT token for authenticated user."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRE_MINUTES)

    payload = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token.

    Returns the payload if valid, None if invalid/expired.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except (jwt.InvalidTokenError, jwt.ExpiredSignatureError):
        return None
