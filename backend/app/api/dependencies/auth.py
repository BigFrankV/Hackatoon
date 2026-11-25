from __future__ import annotations

import uuid
from collections.abc import Callable

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies.database import get_db
from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.security import decode_access_token
from app.models.enums import CompanyStatus, UserStatus
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None or not credentials.scheme.lower() == "bearer":
        raise AuthenticationError("Missing authentication token", code="missing_token")

    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError("Token has expired", code="token_expired") from exc
    except jwt.InvalidTokenError as exc:
        raise AuthenticationError("Invalid authentication token", code="invalid_token") from exc

    if payload.get("type") != "access":
        raise AuthenticationError("Invalid token type", code="invalid_token_type")

    subject = payload.get("sub")
    try:
        user_id = uuid.UUID(str(subject))
    except (TypeError, ValueError) as exc:
        raise AuthenticationError("Invalid token subject", code="invalid_token_subject") from exc

    stmt = select(User).options(selectinload(User.company)).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise AuthenticationError("User not found", code="user_not_found")

    if user.status != UserStatus.ACTIVE:
        raise PermissionDeniedError("User account is not active", code="user_inactive")

    if user.company_id is not None:
        company = user.company
        if company is None or company.status != CompanyStatus.ACTIVE:
            raise PermissionDeniedError("Company is not active", code="company_inactive")

    request.state.current_user = user
    return user


def require_roles(*roles: str) -> Callable:
    allowed = set(roles)

    async def dependency(current_user: User = Depends(get_current_user)) -> User:
        role_value = (
            current_user.role.value
            if hasattr(current_user.role, "value")
            else str(current_user.role)
        )
        if role_value not in allowed:
            raise PermissionDeniedError("Not enough permissions", code="forbidden")
        return current_user

    return dependency
