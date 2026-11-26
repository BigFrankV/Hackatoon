from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends

from app.api.dependencies.auth import get_current_user
from app.core.exceptions import PermissionDeniedError
from app.models.user import User


def require_permissions(*permissions: str) -> Callable:
    """Require that the current user's role grants all listed permissions.

    The check is enforced on the backend for every protected endpoint.
    """
    required = tuple(permissions)

    async def dependency(current_user: User = Depends(get_current_user)) -> User:
        granted = {permission.code for permission in current_user.role.permissions}
        if not set(required).issubset(granted):
            raise PermissionDeniedError("Not enough permissions", code="forbidden")
        return current_user

    return dependency


def require_roles(*roles: str) -> Callable:
    """Require that the current user has one of the allowed roles."""
    allowed = set(roles)

    async def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role.code not in allowed:
            raise PermissionDeniedError("Not enough permissions", code="forbidden")
        return current_user

    return dependency
