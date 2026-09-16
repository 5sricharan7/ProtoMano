"""FastAPI authentication dependency.

Reusable dependency that validates tokens and identifies authenticated users.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from lib.auth_service import decode_access_token
from lib.db import db

security = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """FastAPI dependency: validate token and return authenticated user.

    Raises HTTPException(401) if token is missing, invalid, or expired.
    """
    token = credentials.credentials

    # Decode token
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Load user from database to verify still active
    user = await db.users.find_one({"id": user_id})
    if not user or not user.get("active"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is not active",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "user_id": user_id,
        "username": user.get("username"),
        "role": user.get("role"),
        "active": user.get("active"),
    }
