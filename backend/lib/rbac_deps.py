"""Backend authorization dependencies for Task 3B RBAC.

Role-based access control enforced at the dependency level.  Every denial is
audited (event_type ``rbac_denial``) via the shared audit helper before the
403 is raised; auditing is additive and never weakens the authorization
decision.
"""

from fastapi import Depends, HTTPException, Request, status
from lib.audit_service import log_denial
from lib.auth_deps import get_current_user

_RBAC_REASON = "insufficient_role"


async def require_personnel(current_user: dict = Depends(get_current_user), request: Request = None):
    """Require PERSONNEL role."""
    if current_user.get("role") != "PERSONNEL":
        await log_denial(
            "rbac_denial",
            request,
            current_user,
            reason=_RBAC_REASON,
            details={"required_roles": ["PERSONNEL"]},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    return current_user


async def require_welfare_officer(current_user: dict = Depends(get_current_user), request: Request = None):
    """Require WELFARE_OFFICER role."""
    if current_user.get("role") != "WELFARE_OFFICER":
        await log_denial(
            "rbac_denial",
            request,
            current_user,
            reason=_RBAC_REASON,
            details={"required_roles": ["WELFARE_OFFICER"]},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    return current_user


async def require_commander(current_user: dict = Depends(get_current_user), request: Request = None):
    """Require COMMANDER role."""
    if current_user.get("role") != "COMMANDER":
        await log_denial(
            "rbac_denial",
            request,
            current_user,
            reason=_RBAC_REASON,
            details={"required_roles": ["COMMANDER"]},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    return current_user


def require_any_role(*roles: str):
    """Factory: require any of the specified roles.

    Deliberately a synchronous factory: FastAPI needs a callable it can
    inspect, not a coroutine object, so the factory itself must not be
    ``async def``.
    """
    async def check_role(current_user: dict = Depends(get_current_user), request: Request = None):
        if current_user.get("role") not in roles:
            await log_denial(
                "rbac_denial",
                request,
                current_user,
                reason=_RBAC_REASON,
                details={"required_roles": list(roles)},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user
    return check_role