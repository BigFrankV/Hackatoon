from __future__ import annotations

import uuid

from fastapi import APIRouter, Body, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.database import get_db
from app.api.dependencies.permissions import require_permissions
from app.models.enums import UserRole, UserStatus
from app.models.user import User
from app.schemas.user import (
    GlobalUserCreateRequest,
    GlobalUserUpdateRequest,
    UserActionRequest,
    UserAdminResponse,
    UserCreatedResponse,
    UserResetPasswordResponse,
)
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=dict)
async def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    company_id: uuid.UUID | None = Query(default=None),
    role: UserRole | None = Query(default=None),
    status: UserStatus | None = Query(default=None),
    search: str | None = Query(default=None, max_length=200),
    _: User = Depends(require_permissions("users.read_global")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await user_service.list_users_global(
        db,
        page=page,
        page_size=page_size,
        company_id=company_id,
        role=role,
        status=status,
        search=search,
    )


@router.post("", response_model=UserCreatedResponse, status_code=201)
async def create_user(
    payload: GlobalUserCreateRequest,
    request: Request,
    current_user: User = Depends(require_permissions("users.create_global")),
    db: AsyncSession = Depends(get_db),
) -> UserCreatedResponse:
    result = await user_service.create_user_global(
        db,
        request=request,
        actor=current_user,
        payload=payload.model_dump(),
    )
    return UserCreatedResponse(**result)


@router.get("/{user_id}", response_model=UserAdminResponse)
async def get_user(
    user_id: uuid.UUID,
    _: User = Depends(require_permissions("users.read_global")),
    db: AsyncSession = Depends(get_db),
) -> UserAdminResponse:
    result = await user_service.get_user_global(db, user_id=user_id)
    return UserAdminResponse(**result)


@router.patch("/{user_id}", response_model=UserAdminResponse)
async def update_user(
    user_id: uuid.UUID,
    payload: GlobalUserUpdateRequest,
    request: Request,
    current_user: User = Depends(require_permissions("users.update_global")),
    db: AsyncSession = Depends(get_db),
) -> UserAdminResponse:
    result = await user_service.update_user_global(
        db,
        request=request,
        actor=current_user,
        user_id=user_id,
        payload=payload.model_dump(exclude_unset=True),
    )
    return UserAdminResponse(**result)


@router.post("/{user_id}/activate", response_model=UserAdminResponse)
async def activate_user(
    user_id: uuid.UUID,
    request: Request,
    payload: UserActionRequest | None = Body(default=None),
    current_user: User = Depends(require_permissions("users.activate_global")),
    db: AsyncSession = Depends(get_db),
) -> UserAdminResponse:
    body = payload.model_dump() if payload else {}
    result = await user_service.set_user_status_global(
        db,
        request=request,
        actor=current_user,
        user_id=user_id,
        active=True,
        reason=body.get("reason"),
    )
    return UserAdminResponse(**result)


@router.post("/{user_id}/deactivate", response_model=UserAdminResponse)
async def deactivate_user(
    user_id: uuid.UUID,
    request: Request,
    payload: UserActionRequest | None = Body(default=None),
    current_user: User = Depends(require_permissions("users.deactivate_global")),
    db: AsyncSession = Depends(get_db),
) -> UserAdminResponse:
    body = payload.model_dump() if payload else {}
    result = await user_service.set_user_status_global(
        db,
        request=request,
        actor=current_user,
        user_id=user_id,
        active=False,
        reason=body.get("reason"),
    )
    return UserAdminResponse(**result)


@router.post("/{user_id}/reset-password", response_model=UserResetPasswordResponse)
async def reset_user_password(
    user_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_permissions("users.reset_password_global")),
    db: AsyncSession = Depends(get_db),
) -> UserResetPasswordResponse:
    result = await user_service.reset_user_password_global(
        db,
        request=request,
        actor=current_user,
        user_id=user_id,
    )
    return UserResetPasswordResponse(**result)


@router.post("/{user_id}/revoke-sessions", response_model=dict)
async def revoke_user_sessions(
    user_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_permissions("users.revoke_sessions_global")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await user_service.revoke_user_sessions_global(
        db,
        request=request,
        actor=current_user,
        user_id=user_id,
    )