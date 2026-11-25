from __future__ import annotations

import uuid
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.database import get_db
from app.core.config import get_settings
from app.core.exceptions import PermissionDeniedError
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    ProfileUpdateRequest,
    RefreshResponse,
    SessionResponse,
    UserPublic,
)
from app.schemas.common import MessageResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=refresh_token,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        expires=settings.refresh_token_expire_days * 24 * 60 * 60,
        path=settings.refresh_cookie_path,
        secure=settings.refresh_cookie_secure,
        httponly=True,
        samesite=settings.refresh_cookie_samesite,
        domain=settings.refresh_cookie_domain,
    )


def _clear_refresh_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=settings.refresh_cookie_name,
        path=settings.refresh_cookie_path,
        domain=settings.refresh_cookie_domain,
        secure=settings.refresh_cookie_secure,
        httponly=True,
        samesite=settings.refresh_cookie_samesite,
    )


def _origin_allowed(origin: str, allowed_origins: list[str]) -> bool:
    return origin in allowed_origins


def _enforce_cookie_csrf(request: Request) -> None:
    """Mitigate CSRF for cookie-authenticated endpoints.

    Strategy: SameSite cookie + Origin/Referer allowlist validation when present.
    Requests without Origin/Referer are allowed to support non-browser clients.
    """
    settings = get_settings()
    origin = request.headers.get("origin")
    if origin:
        if not _origin_allowed(origin, settings.cors_origins):
            raise PermissionDeniedError("Invalid request origin", code="csrf_origin_denied")
        return

    referer = request.headers.get("referer")
    if referer:
        parsed = urlparse(referer)
        referer_origin = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else ""
        if not _origin_allowed(referer_origin, settings.cors_origins):
            raise PermissionDeniedError("Invalid request origin", code="csrf_origin_denied")


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    result = await auth_service.login(
        db,
        request=request,
        email=str(payload.email),
        password=payload.password,
    )
    refresh_token = result.pop("refresh_token")
    _set_refresh_cookie(response, refresh_token)
    return LoginResponse(**result)


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> RefreshResponse:
    _enforce_cookie_csrf(request)
    settings = get_settings()
    raw_refresh_token = request.cookies.get(settings.refresh_cookie_name)
    result = await auth_service.refresh_session(db, request=request, raw_refresh_token=raw_refresh_token)
    refresh_token = result.pop("refresh_token")
    _set_refresh_cookie(response, refresh_token)
    return RefreshResponse(**result)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    _enforce_cookie_csrf(request)
    settings = get_settings()
    raw_refresh_token = request.cookies.get(settings.refresh_cookie_name)
    await auth_service.logout(db, request=request, raw_refresh_token=raw_refresh_token)
    _clear_refresh_cookie(response)
    return MessageResponse(message="Logged out")


@router.get("/me", response_model=UserPublic)
async def get_me(current_user: User = Depends(get_current_user)) -> UserPublic:
    payload = await auth_service.get_current_user_profile(current_user)
    return UserPublic(**payload)


@router.patch("/me", response_model=UserPublic)
async def update_me(
    payload: ProfileUpdateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserPublic:
    updated = await auth_service.update_profile(
        db,
        request=request,
        user=current_user,
        first_name=payload.first_name,
        last_name=payload.last_name,
    )
    return UserPublic(**updated)


@router.post("/change-password")
async def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await auth_service.change_password(
        db,
        request=request,
        user=current_user,
        current_password=payload.current_password,
        new_password=payload.new_password,
    )
    refresh_token = result.pop("refresh_token")
    _set_refresh_cookie(response, refresh_token)
    return result


@router.get("/sessions", response_model=list[SessionResponse])
async def get_sessions(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SessionResponse]:
    settings = get_settings()
    raw_refresh_token = request.cookies.get(settings.refresh_cookie_name)
    sessions = await auth_service.list_sessions(db, user=current_user, raw_refresh_token=raw_refresh_token)
    return [SessionResponse(**session) for session in sessions]


@router.delete("/sessions/{session_id}", response_model=MessageResponse)
async def revoke_session(
    session_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    result = await auth_service.revoke_session(
        db, request=request, user=current_user, session_id=session_id
    )
    return MessageResponse(**result)
