from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends

from app.api.dependencies.auth import get_current_user
from app.core.exceptions import PermissionDeniedError
from app.core.permissions import roles_for_permission
from app.models.user import User


def _role_value(user: User) -> str:
    role = user.role
    return role.value if hasattr(role, "value") else str(role)


def require_permissions(*permissions: str) -> Callable:
    """Require that the current user's role grants all listed permissions.

    The check is enforced on the backend for every protected endpoint.
    """
    required = tuple(permissions)

    async def dependency(current_user: User = Depends(get_current_user)) -> User:
        role = _role_value(current_user)
        for permission in required:
            allowed_roles = roles_for_permission(permission)
            if not allowed_roles or role not in allowed_roles:
                raise PermissionDeniedError("Not enough permissions", code="forbidden")
        return current_user

    return dependency


def require_roles(*roles: str) -> Callable:
    """Require that the current user has one of the allowed roles."""
    allowed = set(roles)

    async def dependency(current_user: User = Depends(get_current_user)) -> User:
        if _role_value(current_user) not in allowed:
            raise PermissionDeniedError("Not enough permissions", code="forbidden")
        return current_user

    return dependency
