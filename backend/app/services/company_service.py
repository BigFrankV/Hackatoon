from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.core.security import (
    generate_temporary_password,
    hash_password,
    normalize_email,
)
from app.models.company import Company
from app.models.enums import CompanyStatus, UserRole, UserStatus
from app.models.role import Role
from app.models.user import User
from app.services import auth_service
from app.services.audit_service import record_audit_event
from app.services.role_service import get_role


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _client_meta(request) -> tuple[str | None, str | None]:
    ip = request.client.host if request and request.client else None
    user_agent = request.headers.get("user-agent") if request else None
    if user_agent and len(user_agent) > 512:
        user_agent = user_agent[:512]
    return ip, user_agent


def _normalize_tax_id(tax_id: str | None) -> str | None:
    if tax_id is None:
        return None
    normalized = "".join(ch for ch in tax_id.strip() if ch.isalnum()).upper()
    return normalized or None


def _company_to_dict(company: Company, *, users_count: int | None = None) -> dict:
    return {
        "id": company.id,
        "legal_name": company.legal_name,
        "display_name": company.display_name,
        "tax_id": company.tax_id,
        "email": company.email,
        "phone": company.phone,
        "address": company.address,
        "status": company.status,
        "created_at": company.created_at,
        "updated_at": company.updated_at,
        "deactivated_at": company.deactivated_at,
        "users_count": users_count,
    }


def _user_to_admin_dict(user: User) -> dict:
    company_payload = None
    if user.company is not None:
        company_payload = {
            "id": user.company.id,
            "legal_name": user.company.legal_name,
            "display_name": user.company.display_name,
            "status": user.company.status.value
            if hasattr(user.company.status, "value")
            else str(user.company.status),
        }
    return {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": user.role.code,
        "status": user.status,
        "company_id": user.company_id,
        "company": company_payload,
        "must_change_password": user.must_change_password,
        "last_login_at": user.last_login_at,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "deactivated_at": user.deactivated_at,
    }


async def _get_company_or_404(db: AsyncSession, company_id: uuid.UUID) -> Company:
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if company is None:
        raise NotFoundError("Company not found", code="company_not_found")
    return company


async def _ensure_tax_id_unique(
    db: AsyncSession, *, tax_id: str | None, exclude_company_id: uuid.UUID | None = None
) -> None:
    if not tax_id:
        return
    stmt = select(Company.id).where(Company.tax_id == tax_id)
    if exclude_company_id is not None:
        stmt = stmt.where(Company.id != exclude_company_id)
    result = await db.execute(stmt)
    if result.scalar_one_or_none() is not None:
        raise ConflictError("Company tax_id already exists", code="company_tax_id_exists")


async def _ensure_email_available(db: AsyncSession, *, email: str) -> None:
    stmt = select(User.id).where(User.email == normalize_email(email))
    result = await db.execute(stmt)
    if result.scalar_one_or_none() is not None:
        raise ConflictError("Email already exists", code="email_exists")


async def list_companies(
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 20,
    status: CompanyStatus | None = None,
    search: str | None = None,
) -> dict:
    stmt = select(Company)
    count_stmt = select(func.count()).select_from(Company)
    if status is not None:
        stmt = stmt.where(Company.status == status)
        count_stmt = count_stmt.where(Company.status == status)
    if search:
        pattern = f"%{search.strip().lower()}%"
        search_filter = func.lower(Company.legal_name).like(pattern) | func.lower(
            func.coalesce(Company.display_name, "")
        ).like(pattern) | func.lower(func.coalesce(Company.tax_id, "")).like(pattern)
        stmt = stmt.where(search_filter)
        count_stmt = count_stmt.where(search_filter)

    total = int((await db.execute(count_stmt)).scalar_one())
    stmt = stmt.order_by(Company.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    companies = list((await db.execute(stmt)).scalars().all())

    # User counts in one query.
    counts: dict[uuid.UUID, int] = {}
    if companies:
        ids = [c.id for c in companies]
        counts_stmt = (
            select(User.company_id, func.count(User.id))
            .where(User.company_id.in_(ids))
            .group_by(User.company_id)
        )
        for company_id, count in (await db.execute(counts_stmt)).all():
            if company_id is not None:
                counts[company_id] = int(count)

    return {
        "items": [_company_to_dict(c, users_count=counts.get(c.id, 0)) for c in companies],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def create_company(
    db: AsyncSession,
    *,
    request,
    actor: User,
    payload: dict,
) -> dict:
    ip_address, user_agent = _client_meta(request)
    tax_id = _normalize_tax_id(payload.get("tax_id"))
    initial_admin = payload["initial_admin"]
    admin_email = normalize_email(str(initial_admin["email"]))

    await _ensure_tax_id_unique(db, tax_id=tax_id)
    await _ensure_email_available(db, email=admin_email)

    temporary_password = generate_temporary_password(20)
    company = Company(
        legal_name=payload["legal_name"].strip(),
        display_name=(payload.get("display_name") or "").strip() or None,
        tax_id=tax_id,
        email=str(payload["email"]).strip().lower() if payload.get("email") else None,
        phone=(payload.get("phone") or "").strip() or None,
        address=(payload.get("address") or "").strip() or None,
        status=CompanyStatus.ACTIVE,
    )
    db.add(company)
    await db.flush()

    admin_role = await get_role(db, UserRole.ADMIN)
    admin_user = User(
        company_id=company.id,
        email=admin_email,
        first_name=initial_admin["first_name"].strip(),
        last_name=initial_admin["last_name"].strip(),
        password_hash=hash_password(temporary_password),
        role=admin_role,
        status=UserStatus.ACTIVE,
        must_change_password=True,
    )
    db.add(admin_user)
    await db.flush()

    await record_audit_event(
        db,
        action="company.created",
        entity_type="company",
        entity_id=company.id,
        actor_user_id=actor.id,
        company_id=company.id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={
            "legal_name": company.legal_name,
            "tax_id": company.tax_id,
            "initial_admin_user_id": str(admin_user.id),
        },
    )
    await record_audit_event(
        db,
        action="user.created",
        entity_type="user",
        entity_id=admin_user.id,
        actor_user_id=actor.id,
        company_id=company.id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={
            "role": admin_user.role.code,
            "status": admin_user.status.value,
            "source": "company_initial_admin",
        },
    )

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("Company or user already exists", code="conflict") from exc

    await db.refresh(company)
    await db.refresh(admin_user)

    return {
        "company": _company_to_dict(company, users_count=1),
        "initial_admin": {
            "id": admin_user.id,
            "email": admin_user.email,
            "first_name": admin_user.first_name,
            "last_name": admin_user.last_name,
            "role": admin_user.role.code,
            "status": admin_user.status.value,
            "must_change_password": admin_user.must_change_password,
            "temporary_password": temporary_password,
        },
        "delivery": {
            "method": "manual_temporary_password",
            "note": "Email provider is not configured. Share the temporary password through a secure channel and require password change on first login.",
        },
    }


async def get_company(db: AsyncSession, *, company_id: uuid.UUID) -> dict:
    company = await _get_company_or_404(db, company_id)
    count_stmt = select(func.count(User.id)).where(User.company_id == company.id)
    users_count = int((await db.execute(count_stmt)).scalar_one())
    return _company_to_dict(company, users_count=users_count)


async def update_company(
    db: AsyncSession,
    *,
    request,
    actor: User,
    company_id: uuid.UUID,
    payload: dict,
) -> dict:
    ip_address, user_agent = _client_meta(request)
    company = await _get_company_or_404(db, company_id)

    changes: dict[str, dict[str, object]] = {}
    if "legal_name" in payload and payload["legal_name"] is not None:
        new_value = payload["legal_name"].strip()
        if new_value != company.legal_name:
            changes["legal_name"] = {"from": company.legal_name, "to": new_value}
            company.legal_name = new_value
    if "display_name" in payload:
        new_value = (payload.get("display_name") or "").strip() or None
        if new_value != company.display_name:
            changes["display_name"] = {"from": company.display_name, "to": new_value}
            company.display_name = new_value
    if "tax_id" in payload:
        new_value = _normalize_tax_id(payload.get("tax_id"))
        if new_value != company.tax_id:
            await _ensure_tax_id_unique(db, tax_id=new_value, exclude_company_id=company.id)
            changes["tax_id"] = {"from": company.tax_id, "to": new_value}
            company.tax_id = new_value
    if "email" in payload:
        new_value = str(payload["email"]).strip().lower() if payload.get("email") else None
        if new_value != company.email:
            changes["email"] = {"from": company.email, "to": new_value}
            company.email = new_value
    if "phone" in payload:
        new_value = (payload.get("phone") or "").strip() or None
        if new_value != company.phone:
            changes["phone"] = {"from": company.phone, "to": new_value}
            company.phone = new_value
    if "address" in payload:
        new_value = (payload.get("address") or "").strip() or None
        if new_value != company.address:
            changes["address"] = {"from": company.address, "to": new_value}
            company.address = new_value

    if changes:
        await record_audit_event(
            db,
            action="company.updated",
            entity_type="company",
            entity_id=company.id,
            actor_user_id=actor.id,
            company_id=company.id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"changes": changes},
        )
        try:
            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            raise ConflictError("Company update conflicts with existing data", code="conflict") from exc
        await db.refresh(company)
    else:
        await db.commit()

    return await get_company(db, company_id=company.id)


async def suspend_company(
    db: AsyncSession,
    *,
    request,
    actor: User,
    company_id: uuid.UUID,
    reason: str | None = None,
) -> dict:
    ip_address, user_agent = _client_meta(request)
    company = await _get_company_or_404(db, company_id)
    if company.status == CompanyStatus.SUSPENDED:
        return await get_company(db, company_id=company.id)

    company.status = CompanyStatus.SUSPENDED
    company.deactivated_at = _utcnow()
    revoked = await auth_service.revoke_company_sessions(db, company_id=company.id)

    await record_audit_event(
        db,
        action="company.suspended",
        entity_type="company",
        entity_id=company.id,
        actor_user_id=actor.id,
        company_id=company.id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={"reason": reason, "revoked_sessions": revoked},
    )
    await record_audit_event(
        db,
        action="sessions.revoked",
        entity_type="company",
        entity_id=company.id,
        actor_user_id=actor.id,
        company_id=company.id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={"scope": "company_suspend", "revoked_sessions": revoked},
    )
    await db.commit()
    await db.refresh(company)
    return await get_company(db, company_id=company.id)


async def activate_company(
    db: AsyncSession,
    *,
    request,
    actor: User,
    company_id: uuid.UUID,
    reason: str | None = None,
) -> dict:
    ip_address, user_agent = _client_meta(request)
    company = await _get_company_or_404(db, company_id)
    if company.status == CompanyStatus.ACTIVE:
        return await get_company(db, company_id=company.id)

    company.status = CompanyStatus.ACTIVE
    company.deactivated_at = None
    await record_audit_event(
        db,
        action="company.activated",
        entity_type="company",
        entity_id=company.id,
        actor_user_id=actor.id,
        company_id=company.id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={"reason": reason},
    )
    await db.commit()
    await db.refresh(company)
    return await get_company(db, company_id=company.id)


async def get_company_profile(db: AsyncSession, *, company_id: uuid.UUID) -> dict:
    company = await _get_company_or_404(db, company_id)
    return _company_to_dict(company)


async def update_company_profile(
    db: AsyncSession,
    *,
    request,
    actor: User,
    company_id: uuid.UUID,
    payload: dict,
) -> dict:
    ip_address, user_agent = _client_meta(request)
    company = await _get_company_or_404(db, company_id)
    changes: dict[str, dict[str, object]] = {}

    if "display_name" in payload:
        new_value = (payload.get("display_name") or "").strip() or None
        if new_value != company.display_name:
            changes["display_name"] = {"from": company.display_name, "to": new_value}
            company.display_name = new_value
    if "email" in payload:
        new_value = str(payload["email"]).strip().lower() if payload.get("email") else None
        if new_value != company.email:
            changes["email"] = {"from": company.email, "to": new_value}
            company.email = new_value
    if "phone" in payload:
        new_value = (payload.get("phone") or "").strip() or None
        if new_value != company.phone:
            changes["phone"] = {"from": company.phone, "to": new_value}
            company.phone = new_value
    if "address" in payload:
        new_value = (payload.get("address") or "").strip() or None
        if new_value != company.address:
            changes["address"] = {"from": company.address, "to": new_value}
            company.address = new_value

    if changes:
        await record_audit_event(
            db,
            action="company.updated",
            entity_type="company",
            entity_id=company.id,
            actor_user_id=actor.id,
            company_id=company.id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"changes": changes, "source": "company_profile"},
        )
        await db.commit()
        await db.refresh(company)
    else:
        await db.commit()

    return _company_to_dict(company)


def _validate_status_for_create(status: UserStatus) -> None:
    if status not in {UserStatus.ACTIVE, UserStatus.INVITED, UserStatus.INACTIVE}:
        raise BadRequestError("Invalid user status", code="invalid_user_status")


async def list_company_users(
    db: AsyncSession,
    *,
    company_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
    role: UserRole | None = None,
    status: UserStatus | None = None,
    search: str | None = None,
) -> dict:
    await _get_company_or_404(db, company_id)
    stmt = (
        select(User)
        .options(selectinload(User.company), selectinload(User.role))
        .where(User.company_id == company_id)
    )
    count_stmt = select(func.count()).select_from(User).where(User.company_id == company_id)

    if role is not None:
        stmt = stmt.where(User.role.has(Role.code == role.value))
        count_stmt = count_stmt.where(User.role.has(Role.code == role.value))
    if status is not None:
        stmt = stmt.where(User.status == status)
        count_stmt = count_stmt.where(User.status == status)
    if search:
        pattern = f"%{search.strip().lower()}%"
        filter_ = (
            func.lower(User.email).like(pattern)
            | func.lower(User.first_name).like(pattern)
            | func.lower(User.last_name).like(pattern)
        )
        stmt = stmt.where(filter_)
        count_stmt = count_stmt.where(filter_)

    total = int((await db.execute(count_stmt)).scalar_one())
    stmt = stmt.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    users = list((await db.execute(stmt)).scalars().all())
    return {
        "items": [_user_to_admin_dict(u) for u in users],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def create_company_user(
    db: AsyncSession,
    *,
    request,
    actor: User,
    company_id: uuid.UUID,
    payload: dict,
    enforced_role: UserRole = UserRole.USER,
) -> dict:
    ip_address, user_agent = _client_meta(request)
    company = await _get_company_or_404(db, company_id)
    if company.status != CompanyStatus.ACTIVE:
        raise BadRequestError("Company is not active", code="company_inactive")

    email = normalize_email(str(payload["email"]))
    await _ensure_email_available(db, email=email)
    status = payload.get("status", UserStatus.INVITED)
    _validate_status_for_create(status)

    temporary_password = generate_temporary_password(20)
    role_record = await get_role(db, enforced_role)
    user = User(
        company_id=company.id,
        email=email,
        first_name=payload["first_name"].strip(),
        last_name=payload["last_name"].strip(),
        password_hash=hash_password(temporary_password),
        role=role_record,
        status=status,
        must_change_password=True,
    )
    db.add(user)
    await db.flush()

    await record_audit_event(
        db,
        action="user.created",
        entity_type="user",
        entity_id=user.id,
        actor_user_id=actor.id,
        company_id=company.id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={"role": role_record.code, "status": user.status.value},
    )

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("Email already exists", code="email_exists") from exc

    created = await db.execute(
        select(User).options(selectinload(User.company)).where(User.id == user.id)
    )
    created_user = created.scalar_one()
    return {
        "user": _user_to_admin_dict(created_user),
        "delivery": {
            "method": "manual_temporary_password",
            "note": "Email provider is not configured. Share the temporary password through a secure channel and require password change on first login.",
        },
        "temporary_password": temporary_password,
    }