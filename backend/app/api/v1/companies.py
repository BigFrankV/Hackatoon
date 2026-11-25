from __future__ import annotations

import uuid

from fastapi import APIRouter, Body, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.database import get_db
from app.api.dependencies.permissions import require_permissions
from app.models.enums import CompanyStatus, UserRole, UserStatus
from app.models.user import User
from app.schemas.company import (
    CompanyCreateRequest,
    CompanyCreateResponse,
    CompanyResponse,
    CompanyStatusActionRequest,
    CompanyUpdateRequest,
)
from app.schemas.user import CompanyUserCreateRequest, UserCreatedResponse
from app.services import company_service

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("", response_model=dict)
async def list_companies(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: CompanyStatus | None = Query(default=None),
    search: str | None = Query(default=None, max_length=200),
    _: User = Depends(require_permissions("companies.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await company_service.list_companies(
        db, page=page, page_size=page_size, status=status, search=search
    )


@router.post("", response_model=CompanyCreateResponse, status_code=201)
async def create_company(
    payload: CompanyCreateRequest,
    request: Request,
    current_user: User = Depends(require_permissions("companies.create")),
    db: AsyncSession = Depends(get_db),
) -> CompanyCreateResponse:
    result = await company_service.create_company(
        db,
        request=request,
        actor=current_user,
        payload=payload.model_dump(),
    )
    return CompanyCreateResponse(**result)


@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company(
    company_id: uuid.UUID,
    _: User = Depends(require_permissions("companies.read")),
    db: AsyncSession = Depends(get_db),
) -> CompanyResponse:
    result = await company_service.get_company(db, company_id=company_id)
    return CompanyResponse(**result)


@router.patch("/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: uuid.UUID,
    payload: CompanyUpdateRequest,
    request: Request,
    current_user: User = Depends(require_permissions("companies.update")),
    db: AsyncSession = Depends(get_db),
) -> CompanyResponse:
    result = await company_service.update_company(
        db,
        request=request,
        actor=current_user,
        company_id=company_id,
        payload=payload.model_dump(exclude_unset=True),
    )
    return CompanyResponse(**result)


@router.post("/{company_id}/suspend", response_model=CompanyResponse)
async def suspend_company(
    company_id: uuid.UUID,
    request: Request,
    payload: CompanyStatusActionRequest | None = Body(default=None),
    current_user: User = Depends(require_permissions("companies.deactivate")),
    db: AsyncSession = Depends(get_db),
) -> CompanyResponse:
    body = payload.model_dump() if payload else {}
    result = await company_service.suspend_company(
        db,
        request=request,
        actor=current_user,
        company_id=company_id,
        reason=body.get("reason"),
    )
    return CompanyResponse(**result)


@router.post("/{company_id}/activate", response_model=CompanyResponse)
async def activate_company(
    company_id: uuid.UUID,
    request: Request,
    payload: CompanyStatusActionRequest | None = Body(default=None),
    current_user: User = Depends(require_permissions("companies.activate")),
    db: AsyncSession = Depends(get_db),
) -> CompanyResponse:
    body = payload.model_dump() if payload else {}
    result = await company_service.activate_company(
        db,
        request=request,
        actor=current_user,
        company_id=company_id,
        reason=body.get("reason"),
    )
    return CompanyResponse(**result)


@router.get("/{company_id}/users", response_model=dict)
async def list_company_users(
    company_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    role: UserRole | None = Query(default=None),
    status: UserStatus | None = Query(default=None),
    search: str | None = Query(default=None, max_length=200),
    _: User = Depends(require_permissions("users.read_global")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await company_service.list_company_users(
        db,
        company_id=company_id,
        page=page,
        page_size=page_size,
        role=role,
        status=status,
        search=search,
    )


@router.post("/{company_id}/users", response_model=UserCreatedResponse, status_code=201)
async def create_company_user(
    company_id: uuid.UUID,
    payload: CompanyUserCreateRequest,
    request: Request,
    current_user: User = Depends(require_permissions("users.create_global")),
    db: AsyncSession = Depends(get_db),
) -> UserCreatedResponse:
    # Super admin global endpoint - creates user in specified company.
    # Role is enforced by backend: default user; super_admin may create admin/user via global /users.
    # This endpoint is company-targeted convenience; we keep role=user unless using /users.
    result = await company_service.create_company_user(
        db,
        request=request,
        actor=current_user,
        company_id=company_id,
        payload=payload.model_dump(),
        enforced_role=UserRole.USER,
    )
    return UserCreatedResponse(**result)