"""Task 3A — Backend authentication foundation tests."""

import os

# auth_service requires AUTH_SECRET_KEY at import time; the repo .env may not
# carry one, so tests bootstrap a throwaway key before any backend import.
os.environ.setdefault("AUTH_SECRET_KEY", "test-only-secret-key-not-for-production-1234567890")

import pytest
from datetime import datetime, timezone


def test_password_hashing_is_secure():
    """Verify passwords are hashed, not stored plaintext."""
    from lib.auth_service import hash_password, verify_password
    
    plaintext = "TestPassword123!"
    hashed = hash_password(plaintext)
    
    assert hashed != plaintext, "Password must be hashed, not plaintext"
    assert verify_password(plaintext, hashed), "Correct password must verify"
    assert not verify_password("WrongPassword", hashed), "Incorrect password must fail"


def test_jwt_token_creation_and_validation():
    """Verify JWT tokens are created and validated correctly."""
    from lib.auth_service import create_access_token, decode_access_token
    
    token = create_access_token(
        user_id="test-user-1",
        username="testuser",
        role="PERSONNEL",
    )
    
    assert isinstance(token, str), "Token must be a string"
    assert len(token) > 0, "Token must not be empty"
    
    payload = decode_access_token(token)
    assert payload is not None, "Valid token must decode"
    assert payload["user_id"] == "test-user-1"
    assert payload["username"] == "testuser"
    assert payload["role"] == "PERSONNEL"


def test_jwt_token_expiration():
    """Verify expired JWT tokens are rejected."""
    from lib.auth_service import create_access_token, decode_access_token
    from datetime import timedelta
    
    # Create token with very short expiration
    token = create_access_token(
        user_id="test-user-1",
        username="testuser",
        role="PERSONNEL",
        expires_delta=timedelta(seconds=-1),  # Already expired
    )
    
    payload = decode_access_token(token)
    assert payload is None, "Expired token must return None"


def test_jwt_token_tampering_rejected():
    """Verify tampered JWT tokens are rejected."""
    from lib.auth_service import create_access_token, decode_access_token
    
    token = create_access_token(
        user_id="test-user-1",
        username="testuser",
        role="PERSONNEL",
    )
    
    # Tamper with token
    tampered = token[:-5] + "XXXXX"
    payload = decode_access_token(tampered)
    assert payload is None, "Tampered token must return None"


def test_user_model_has_no_password():
    """Verify User model does not expose password hash."""
    from models.auth import User
    
    user = User(
        id="user-1",
        username="testuser",
        role="PERSONNEL",
        active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    
    assert not hasattr(user, "password_hash"), "User model must not have password_hash field"
    assert not hasattr(user, "password"), "User model must not have password field"


def test_authenticated_user_response_safe():
    """Verify AuthenticatedUser response does not expose secrets."""
    from models.auth import AuthenticatedUser
    
    user_info = AuthenticatedUser(
        user_id="user-1",
        username="testuser",
        role="PERSONNEL",
        active=True,
        created_at=datetime.now(timezone.utc),
    )
    
    user_dict = user_info.model_dump()
    assert "password" not in user_dict, "Response must not contain password"
    assert "password_hash" not in user_dict, "Response must not contain password_hash"
    assert "token" not in user_dict, "Response must not contain token"
    assert "secret" not in user_dict, "Response must not contain secrets"


def test_roles_are_valid():
    """Verify only valid roles are accepted."""
    from models.auth import UserCreate
    from pydantic import ValidationError
    
    # Valid roles should be accepted
    valid = UserCreate(username="user1", password="Pass123!", role="PERSONNEL")
    assert valid.role == "PERSONNEL"
    
    valid = UserCreate(username="user2", password="Pass123!", role="WELFARE_OFFICER")
    assert valid.role == "WELFARE_OFFICER"
    
    valid = UserCreate(username="user3", password="Pass123!", role="COMMANDER")
    assert valid.role == "COMMANDER"
    
    # Invalid roles should be rejected
    try:
        invalid = UserCreate(username="user4", password="Pass123!", role="INVALID_ROLE")
        pytest.fail("Invalid role should be rejected")
    except (ValidationError, ValueError):
        pass  # Expected


def test_password_requirements():
    """Verify password meets minimum requirements."""
    from models.auth import UserCreate
    from pydantic import ValidationError
    
    # Too short
    try:
        UserCreate(username="user", password="short", role="PERSONNEL")
        pytest.fail("Password too short should be rejected")
    except ValidationError:
        pass  # Expected
    
    # Valid
    valid = UserCreate(username="user", password="ValidPass123!", role="PERSONNEL")
    assert valid.password == "ValidPass123!"


def test_username_requirements():
    """Verify username meets minimum requirements."""
    from models.auth import UserCreate
    from pydantic import ValidationError
    
    # Too short
    try:
        UserCreate(username="a", password="ValidPass123!", role="PERSONNEL")
        pytest.fail("Username too short should be rejected")
    except ValidationError:
        pass  # Expected
    
    # Valid
    valid = UserCreate(username="testuser", password="ValidPass123!", role="PERSONNEL")
    assert valid.username == "testuser"
