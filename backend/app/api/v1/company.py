from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Body, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.database import get_db
from app.api.dependencies.permissions import require_permissions
from app.core.exceptions import PermissionDeniedError
from app.models.enums import UserRole, UserStatus
from app.models.user import User
from app.schemas.audit import AuditLogListResponse
from app.schemas.company import CompanyProfileResponse, CompanyProfileUpdateRequest
from app.schemas.user import (
    CompanyUserCreateRequest,
    CompanyUserUpdateRequest,
    UserActionRequest,
    UserAdminResponse,
    UserCreatedResponse,
    UserResetPasswordResponse,
)
from app.services import audit_service, company_service, user_service

router = APIRouter(prefix="/company", tags=["company"])


def _require_admin_company(current_user: User) -> uuid.UUID:
    if current_user.company_id is None:
        raise PermissionDeniedError("Company context required", code="company_context_required")
    return current_user.company_id


@router.get("/profile", response_model=CompanyProfileResponse)
async def get_company_profile(
    current_user: User = Depends(require_permissions("company.profile.read")),
    db: AsyncSession = Depends(get_db),
) -> CompanyProfileResponse:
    company_id = _require_admin_company(current_user)
    result = await company_service.get_company_profile(db, company_id=company_id)
    return CompanyProfileResponse(**result)


@router.patch("/profile", response_model=CompanyProfileResponse)
async def update_company_profile(
    payload: CompanyProfileUpdateRequest,
    request: Request,
    current_user: User = Depends(require_permissions("company.profile.update")),
    db: AsyncSession = Depends(get_db),
) -> CompanyProfileResponse:
    company_id = _require_admin_company(current_user)
    result = await company_service.update_company_profile(
        db,
        request=request,
        actor=current_user,
        company_id=company_id,
        payload=payload.model_dump(exclude_unset=True),
    )
    return CompanyProfileResponse(**result)


@router.get("/users", response_model=dict)
async def list_company_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    role: UserRole | None = Query(default=None),
    status: UserStatus | None = Query(default=None),
    search: str | None = Query(default=None, max_length=200),
    current_user: User = Depends(require_permissions("users.read_company")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    company_id = _require_admin_company(current_user)
    return await user_service.list_company_users_scoped(
        db,
        company_id=company_id,
        page=page,
        page_size=page_size,
        role=role,
        status=status,
        search=search,
    )


@router.post("/users", response_model=UserCreatedResponse, status_code=201)
async def create_company_user(
    payload: CompanyUserCreateRequest,
    request: Request,
    current_user: User = Depends(require_permissions("users.create_company")),
    db: AsyncSession = Depends(get_db),
) -> UserCreatedResponse:
    company_id = _require_admin_company(current_user)
    # Backend enforces role=user and company_id=current_user.company_id.
    result = await user_service.create_company_user_scoped(
        db,
        request=request,
        actor=current_user,
        company_id=company_id,
        payload=payload.model_dump(),
    )
    return UserCreatedResponse(**result)


@router.get("/users/{user_id}", response_model=UserAdminResponse)
async def get_company_user(
    user_id: uuid.UUID,
    current_user: User = Depends(require_permissions("users.read_company")),
    db: AsyncSession = Depends(get_db),
) -> UserAdminResponse:
    company_id = _require_admin_company(current_user)
    result = await user_service.get_company_user_scoped(db, company_id=company_id, user_id=user_id)
    return UserAdminResponse(**result)


@router.patch("/users/{user_id}", response_model=UserAdminResponse)
async def update_company_user(
    user_id: uuid.UUID,
    payload: CompanyUserUpdateRequest,
    request: Request,
    current_user: User = Depends(require_permissions("users.update_company")),
    db: AsyncSession = Depends(get_db),
) -> UserAdminResponse:
    company_id = _require_admin_company(current_user)
    result = await user_service.update_company_user_scoped(
        db,
        request=request,
        actor=current_user,
        company_id=company_id,
        user_id=user_id,
        payload=payload.model_dump(exclude_unset=True),
    )
    return UserAdminResponse(**result)


@router.post("/users/{user_id}/activate", response_model=UserAdminResponse)
async def activate_company_user(
    user_id: uuid.UUID,
    request: Request,
    payload: UserActionRequest | None = Body(default=None),
    current_user: User = Depends(require_permissions("users.activate_company")),
    db: AsyncSession = Depends(get_db),
) -> UserAdminResponse:
    company_id = _require_admin_company(current_user)
    body = payload.model_dump() if payload else {}
    result = await user_service.set_company_user_status_scoped(
        db,
        request=request,
        actor=current_user,
        company_id=company_id,
        user_id=user_id,
        active=True,
        reason=body.get("reason"),
    )
    return UserAdminResponse(**result)


@router.post("/users/{user_id}/deactivate", response_model=UserAdminResponse)
async def deactivate_company_user(
    user_id: uuid.UUID,
    request: Request,
    payload: UserActionRequest | None = Body(default=None),
    current_user: User = Depends(require_permissions("users.deactivate_company")),
    db: AsyncSession = Depends(get_db),
) -> UserAdminResponse:
    company_id = _require_admin_company(current_user)
    body = payload.model_dump() if payload else {}
    result = await user_service.set_company_user_status_scoped(
        db,
        request=request,
        actor=current_user,
        company_id=company_id,
        user_id=user_id,
        active=False,
        reason=body.get("reason"),
    )
    return UserAdminResponse(**result)


@router.post("/users/{user_id}/reset-password", response_model=UserResetPasswordResponse)
async def reset_company_user_password(
    user_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_permissions("users.reset_password_company")),
    db: AsyncSession = Depends(get_db),
) -> UserResetPasswordResponse:
    company_id = _require_admin_company(current_user)
    result = await user_service.reset_company_user_password_scoped(
        db,
        request=request,
        actor=current_user,
        company_id=company_id,
        user_id=user_id,
    )
    return UserResetPasswordResponse(**result)


@router.post("/users/{user_id}/revoke-sessions", response_model=dict)
async def revoke_company_user_sessions(
    user_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_permissions("users.revoke_sessions_company")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    company_id = _require_admin_company(current_user)
    return await user_service.revoke_company_user_sessions_scoped(
        db,
        request=request,
        actor=current_user,
        company_id=company_id,
        user_id=user_id,
    )


@router.get("/audit-logs", response_model=AuditLogListResponse)
async def list_company_audit_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    action: str | None = Query(default=None, max_length=100),
    entity_type: str | None = Query(default=None, max_length=100),
    entity_id: str | None = Query(default=None, max_length=36),
    actor_user_id: uuid.UUID | None = Query(default=None),
    from_date: datetime | None = Query(default=None),
    to_date: datetime | None = Query(default=None),
    current_user: User = Depends(require_permissions("audit.read_company")),
    db: AsyncSession = Depends(get_db),
) -> AuditLogListResponse:
    company_id = _require_admin_company(current_user)
    result = await audit_service.list_audit_logs(
        db,
        page=page,
        page_size=page_size,
        company_id=company_id,
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        from_date=from_date,
        to_date=to_date,
    )
    return AuditLogListResponse(**result)