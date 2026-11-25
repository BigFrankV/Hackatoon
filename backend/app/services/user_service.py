from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
)
from app.core.security import (
    generate_temporary_password,
    hash_password,
    normalize_email,
)
from app.models.company import Company
from app.models.enums import CompanyStatus, UserRole, UserStatus
from app.models.user import User
from app.services import auth_service
from app.services.audit_service import record_audit_event


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _client_meta(request) -> tuple[str | None, str | None]:
    ip = request.client.host if request and request.client else None
    user_agent = request.headers.get("user-agent") if request else None
    if user_agent and len(user_agent) > 512:
        user_agent = user_agent[:512]
    return ip, user_agent


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
        "role": user.role,
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


async def _ensure_email_available(
    db: AsyncSession, *, email: str, exclude_user_id: uuid.UUID | None = None
) -> None:
    stmt = select(User.id).where(User.email == normalize_email(email))
    if exclude_user_id is not None:
        stmt = stmt.where(User.id != exclude_user_id)
    result = await db.execute(stmt)
    if result.scalar_one_or_none() is not None:
        raise ConflictError("Email already exists", code="email_exists")


async def _get_user_global_or_404(db: AsyncSession, user_id: uuid.UUID) -> User:
    stmt = select(User).options(selectinload(User.company)).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise NotFoundError("User not found", code="user_not_found")
    return user


async def _get_user_in_company_or_404(
    db: AsyncSession, *, user_id: uuid.UUID, company_id: uuid.UUID
) -> User:
    stmt = (
        select(User)
        .options(selectinload(User.company))
        .where(User.id == user_id, User.company_id == company_id)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        # 404 to avoid existence leak across companies.
        raise NotFoundError("User not found", code="user_not_found")
    return user


def _validate_role_company_constraints(*, role: UserRole, company_id: uuid.UUID | None) -> None:
    if role == UserRole.SUPER_ADMIN and company_id is not None:
        raise BadRequestError(
            "super_admin must not have company_id", code="invalid_role_company"
        )
    if role in {UserRole.ADMIN, UserRole.USER} and company_id is None:
        raise BadRequestError("admin/user must have company_id", code="invalid_role_company")


async def _ensure_company_active_for_membership(db: AsyncSession, company_id: uuid.UUID) -> Company:
    company = await _get_company_or_404(db, company_id)
    if company.status != CompanyStatus.ACTIVE:
        raise BadRequestError("Company is not active", code="company_inactive")
    return company


async def _count_active_admins(db: AsyncSession, *, company_id: uuid.UUID, exclude_user_id: uuid.UUID | None = None) -> int:
    stmt = select(func.count(User.id)).where(
        User.company_id == company_id,
        User.role == UserRole.ADMIN,
        User.status == UserStatus.ACTIVE,
    )
    if exclude_user_id is not None:
        stmt = stmt.where(User.id != exclude_user_id)
    return int((await db.execute(stmt)).scalar_one())


async def _ensure_not_last_active_admin(
    db: AsyncSession, *, user: User, actor: User, allow_super_admin_override: bool
) -> None:
    if user.role != UserRole.ADMIN or user.status != UserStatus.ACTIVE or user.company_id is None:
        return
    remaining = await _count_active_admins(db, company_id=user.company_id, exclude_user_id=user.id)
    if remaining > 0:
        return
    if allow_super_admin_override and actor.role == UserRole.SUPER_ADMIN:
        return
    raise ConflictError(
        "Cannot deactivate or demote the last active admin of the company",
        code="last_active_admin",
    )


def _assert_not_self_action(*, actor: User, target: User, action: str) -> None:
    if actor.id == target.id:
        raise BadRequestError(f"Cannot {action} your own account", code="self_action_not_allowed")


async def list_users_global(
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 20,
    company_id: uuid.UUID | None = None,
    role: UserRole | None = None,
    status: UserStatus | None = None,
    search: str | None = None,
) -> dict:
    stmt = select(User).options(selectinload(User.company))
    count_stmt = select(func.count()).select_from(User)

    if company_id is not None:
        stmt = stmt.where(User.company_id == company_id)
        count_stmt = count_stmt.where(User.company_id == company_id)
    if role is not None:
        stmt = stmt.where(User.role == role)
        count_stmt = count_stmt.where(User.role == role)
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


async def create_user_global(
    db: AsyncSession,
    *,
    request,
    actor: User,
    payload: dict,
) -> dict:
    ip_address, user_agent = _client_meta(request)
    role = payload["role"]
    company_id = payload.get("company_id")
    status = payload.get("status", UserStatus.INVITED)
    email = normalize_email(str(payload["email"]))

    _validate_role_company_constraints(role=role, company_id=company_id)
    await _ensure_email_available(db, email=email)
    if company_id is not None:
        await _ensure_company_active_for_membership(db, company_id)

    if role == UserRole.SUPER_ADMIN:
        # Restricted procedure: allowed for super_admin endpoint but audited.
        pass

    temporary_password = generate_temporary_password(20)
    user = User(
        company_id=company_id,
        email=email,
        first_name=payload["first_name"].strip(),
        last_name=payload["last_name"].strip(),
        password_hash=hash_password(temporary_password),
        role=role,
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
        company_id=user.company_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={"role": role.value, "status": status.value, "scope": "global"},
    )

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("User could not be created", code="conflict") from exc

    created = await _get_user_global_or_404(db, user.id)
    return {
        "user": _user_to_admin_dict(created),
        "delivery": {
            "method": "manual_temporary_password",
            "note": "Email provider is not configured. Share the temporary password through a secure channel and require password change on first login.",
        },
        "temporary_password": temporary_password,
    }


async def get_user_global(db: AsyncSession, *, user_id: uuid.UUID) -> dict:
    user = await _get_user_global_or_404(db, user_id)
    return _user_to_admin_dict(user)


async def update_user_global(
    db: AsyncSession,
    *,
    request,
    actor: User,
    user_id: uuid.UUID,
    payload: dict,
) -> dict:
    ip_address, user_agent = _client_meta(request)
    user = await _get_user_global_or_404(db, user_id)

    old_role = user.role
    old_company_id = user.company_id
    old_status = user.status
    changes: dict[str, dict[str, object]] = {}

    next_role = payload.get("role", user.role)
    next_company_id = payload.get("company_id", user.company_id)
    _validate_role_company_constraints(role=next_role, company_id=next_company_id)

    if "first_name" in payload and payload["first_name"] is not None:
        new_value = payload["first_name"].strip()
        if new_value != user.first_name:
            changes["first_name"] = {"from": user.first_name, "to": new_value}
            user.first_name = new_value
    if "last_name" in payload and payload["last_name"] is not None:
        new_value = payload["last_name"].strip()
        if new_value != user.last_name:
            changes["last_name"] = {"from": user.last_name, "to": new_value}
            user.last_name = new_value

    if "role" in payload and payload["role"] is not None and payload["role"] != user.role:
        if actor.id == user.id:
            raise BadRequestError("Cannot change your own role", code="self_role_change_forbidden")
        await _ensure_not_last_active_admin(db, user=user, actor=actor, allow_super_admin_override=True)
        user.role = payload["role"]
        changes["role"] = {"from": old_role.value, "to": user.role.value}

    if "company_id" in payload and payload["company_id"] != user.company_id:
        if actor.id == user.id:
            raise BadRequestError(
                "Cannot change your own company", code="self_company_change_forbidden"
            )
        if payload["company_id"] is not None:
            await _ensure_company_active_for_membership(db, payload["company_id"])
        if old_role == UserRole.ADMIN and old_company_id is not None:
            remaining = await _count_active_admins(db, company_id=old_company_id, exclude_user_id=user.id)
            if remaining == 0 and not (actor.role == UserRole.SUPER_ADMIN):
                raise ConflictError(
                    "Cannot transfer the last active admin of the company",
                    code="last_active_admin",
                )
        user.company_id = payload["company_id"]
        changes["company_id"] = {
            "from": str(old_company_id) if old_company_id else None,
            "to": str(user.company_id) if user.company_id else None,
        }
        # Transfer is controlled: revoke sessions and keep historical resources untouched.
        await auth_service.revoke_user_sessions(db, user_id=user.id)
        await record_audit_event(
            db,
            action="sessions.revoked",
            entity_type="user",
            entity_id=user.id,
            actor_user_id=actor.id,
            company_id=user.company_id or old_company_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"scope": "company_transfer"},
        )

    if "status" in payload and payload["status"] is not None and payload["status"] != user.status:
        if payload["status"] in {UserStatus.INACTIVE, UserStatus.LOCKED}:
            await _ensure_not_last_active_admin(db, user=user, actor=actor, allow_super_admin_override=True)
        user.status = payload["status"]
        changes["status"] = {"from": old_status.value, "to": user.status.value}
        if user.status == UserStatus.ACTIVE:
            user.deactivated_at = None
        else:
            user.deactivated_at = _utcnow()
            revoked = await auth_service.revoke_user_sessions(db, user_id=user.id)
            await record_audit_event(
                db,
                action="sessions.revoked",
                entity_type="user",
                entity_id=user.id,
                actor_user_id=actor.id,
                company_id=user.company_id,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={"scope": "status_change", "revoked_sessions": revoked},
            )

    if (
        "must_change_password" in payload
        and payload["must_change_password"] is not None
        and bool(payload["must_change_password"]) != user.must_change_password
    ):
        changes["must_change_password"] = {
            "from": user.must_change_password,
            "to": bool(payload["must_change_password"]),
        }
        user.must_change_password = bool(payload["must_change_password"])

    _validate_role_company_constraints(role=user.role, company_id=user.company_id)

    if changes:
        await record_audit_event(
            db,
            action="user.updated",
            entity_type="user",
            entity_id=user.id,
            actor_user_id=actor.id,
            company_id=user.company_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"changes": changes, "scope": "global"},
        )
        if "role" in changes:
            await record_audit_event(
                db,
                action="user.role_changed",
                entity_type="user",
                entity_id=user.id,
                actor_user_id=actor.id,
                company_id=user.company_id,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={"from": old_role.value, "to": user.role.value},
            )
        if "status" in changes:
            if user.status == UserStatus.ACTIVE:
                await record_audit_event(
                    db,
                    action="user.activated",
                    entity_type="user",
                    entity_id=user.id,
                    actor_user_id=actor.id,
                    company_id=user.company_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    metadata={"scope": "global"},
                )
            else:
                await record_audit_event(
                    db,
                    action="user.deactivated",
                    entity_type="user",
                    entity_id=user.id,
                    actor_user_id=actor.id,
                    company_id=user.company_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    metadata={"status": user.status.value, "scope": "global"},
                )

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("User update conflicts with existing data", code="conflict") from exc

    return await get_user_global(db, user_id=user.id)


async def set_user_status_global(
    db: AsyncSession,
    *,
    request,
    actor: User,
    user_id: uuid.UUID,
    active: bool,
    reason: str | None = None,
) -> dict:
    ip_address, user_agent = _client_meta(request)
    user = await _get_user_global_or_404(db, user_id)

    if actor.id == user.id and not active:
        raise BadRequestError("Cannot deactivate your own account", code="self_action_not_allowed")

    if not active:
        await _ensure_not_last_active_admin(db, user=user, actor=actor, allow_super_admin_override=True)

    old_status = user.status
    new_status = UserStatus.ACTIVE if active else UserStatus.INACTIVE
    if user.status == new_status:
        return _user_to_admin_dict(user)

    user.status = new_status
    user.deactivated_at = None if active else _utcnow()

    revoked = 0
    if not active:
        revoked = await auth_service.revoke_user_sessions(db, user_id=user.id)

    action = "user.activated" if active else "user.deactivated"
    await record_audit_event(
        db,
        action=action,
        entity_type="user",
        entity_id=user.id,
        actor_user_id=actor.id,
        company_id=user.company_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={
            "from": old_status.value,
            "to": new_status.value,
            "reason": reason,
            "revoked_sessions": revoked,
            "scope": "global",
        },
    )
    if not active:
        await record_audit_event(
            db,
            action="sessions.revoked",
            entity_type="user",
            entity_id=user.id,
            actor_user_id=actor.id,
            company_id=user.company_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"scope": "user_deactivation", "revoked_sessions": revoked},
        )

    await db.commit()
    return await get_user_global(db, user_id=user.id)


async def reset_user_password_global(
    db: AsyncSession,
    *,
    request,
    actor: User,
    user_id: uuid.UUID,
) -> dict:
    ip_address, user_agent = _client_meta(request)
    user = await _get_user_global_or_404(db, user_id)

    temporary_password = generate_temporary_password(20)
    user.password_hash = hash_password(temporary_password)
    user.must_change_password = True
    revoked = await auth_service.revoke_user_sessions(db, user_id=user.id)

    await record_audit_event(
        db,
        action="sessions.revoked",
        entity_type="user",
        entity_id=user.id,
        actor_user_id=actor.id,
        company_id=user.company_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={"scope": "password_reset", "revoked_sessions": revoked},
    )
    await record_audit_event(
        db,
        action="user.updated",
        entity_type="user",
        entity_id=user.id,
        actor_user_id=actor.id,
        company_id=user.company_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={"changes": {"password_reset_initiated": {"from": False, "to": True}}, "scope": "global"},
    )
    await db.commit()

    return {
        "message": "Password reset initiated. Email provider is not configured; a temporary password was generated for secure manual delivery.",
        "reset_initiated": True,
        "delivery": "manual_temporary_password",
        "temporary_password": temporary_password,
        "must_change_password": True,
    }


async def revoke_user_sessions_global(
    db: AsyncSession,
    *,
    request,
    actor: User,
    user_id: uuid.UUID,
) -> dict:
    ip_address, user_agent = _client_meta(request)
    user = await _get_user_global_or_404(db, user_id)
    revoked = await auth_service.revoke_user_sessions(db, user_id=user.id)
    await record_audit_event(
        db,
        action="sessions.revoked",
        entity_type="user",
        entity_id=user.id,
        actor_user_id=actor.id,
        company_id=user.company_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={"scope": "admin_revoke", "revoked_sessions": revoked},
    )
    await db.commit()
    return {"message": "Sessions revoked", "revoked_sessions": revoked}


# --- Company-scoped admin operations ---


async def list_company_users_scoped(
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
    stmt = select(User).options(selectinload(User.company)).where(User.company_id == company_id)
    count_stmt = select(func.count()).select_from(User).where(User.company_id == company_id)

    if role is not None:
        stmt = stmt.where(User.role == role)
        count_stmt = count_stmt.where(User.role == role)
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


async def create_company_user_scoped(
    db: AsyncSession,
    *,
    request,
    actor: User,
    company_id: uuid.UUID,
    payload: dict,
) -> dict:
    ip_address, user_agent = _client_meta(request)
    company = await _ensure_company_active_for_membership(db, company_id)

    email = normalize_email(str(payload["email"]))
    await _ensure_email_available(db, email=email)
    status = payload.get("status", UserStatus.INVITED)
    if status not in {UserStatus.ACTIVE, UserStatus.INVITED, UserStatus.INACTIVE}:
        raise BadRequestError("Invalid user status", code="invalid_user_status")

    temporary_password = generate_temporary_password(20)
    user = User(
        company_id=company.id,
        email=email,
        first_name=payload["first_name"].strip(),
        last_name=payload["last_name"].strip(),
        password_hash=hash_password(temporary_password),
        role=UserRole.USER,
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
        metadata={"role": UserRole.USER.value, "status": status.value, "scope": "company"},
    )

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("Email already exists", code="email_exists") from exc

    created = await _get_user_in_company_or_404(db, user_id=user.id, company_id=company.id)
    return {
        "user": _user_to_admin_dict(created),
        "delivery": {
            "method": "manual_temporary_password",
            "note": "Email provider is not configured. Share the temporary password through a secure channel and require password change on first login.",
        },
        "temporary_password": temporary_password,
    }


async def get_company_user_scoped(db: AsyncSession, *, company_id: uuid.UUID, user_id: uuid.UUID) -> dict:
    user = await _get_user_in_company_or_404(db, user_id=user_id, company_id=company_id)
    return _user_to_admin_dict(user)


async def update_company_user_scoped(
    db: AsyncSession,
    *,
    request,
    actor: User,
    company_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: dict,
) -> dict:
    ip_address, user_agent = _client_meta(request)
    user = await _get_user_in_company_or_404(db, user_id=user_id, company_id=company_id)

    if actor.id == user.id:
        raise BadRequestError(
            "Cannot update your own account through admin endpoint", code="self_action_not_allowed"
        )

    changes: dict[str, dict[str, object]] = {}
    if "first_name" in payload and payload["first_name"] is not None:
        new_value = payload["first_name"].strip()
        if new_value != user.first_name:
            changes["first_name"] = {"from": user.first_name, "to": new_value}
            user.first_name = new_value
    if "last_name" in payload and payload["last_name"] is not None:
        new_value = payload["last_name"].strip()
        if new_value != user.last_name:
            changes["last_name"] = {"from": user.last_name, "to": new_value}
            user.last_name = new_value

    if changes:
        await record_audit_event(
            db,
            action="user.updated",
            entity_type="user",
            entity_id=user.id,
            actor_user_id=actor.id,
            company_id=company_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"changes": changes, "scope": "company"},
        )
        await db.commit()

    return await get_company_user_scoped(db, company_id=company_id, user_id=user.id)


async def set_company_user_status_scoped(
    db: AsyncSession,
    *,
    request,
    actor: User,
    company_id: uuid.UUID,
    user_id: uuid.UUID,
    active: bool,
    reason: str | None = None,
) -> dict:
    ip_address, user_agent = _client_meta(request)
    user = await _get_user_in_company_or_404(db, user_id=user_id, company_id=company_id)

    if actor.id == user.id and not active:
        raise BadRequestError("Cannot deactivate your own account", code="self_action_not_allowed")

    if not active:
        await _ensure_not_last_active_admin(db, user=user, actor=actor, allow_super_admin_override=False)

    old_status = user.status
    new_status = UserStatus.ACTIVE if active else UserStatus.INACTIVE
    if user.status == new_status:
        return _user_to_admin_dict(user)

    user.status = new_status
    user.deactivated_at = None if active else _utcnow()

    revoked = 0
    if not active:
        revoked = await auth_service.revoke_user_sessions(db, user_id=user.id)

    action = "user.activated" if active else "user.deactivated"
    await record_audit_event(
        db,
        action=action,
        entity_type="user",
        entity_id=user.id,
        actor_user_id=actor.id,
        company_id=company_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={
            "from": old_status.value,
            "to": new_status.value,
            "reason": reason,
            "revoked_sessions": revoked,
            "scope": "company",
        },
    )
    if not active:
        await record_audit_event(
            db,
            action="sessions.revoked",
            entity_type="user",
            entity_id=user.id,
            actor_user_id=actor.id,
            company_id=company_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"scope": "user_deactivation", "revoked_sessions": revoked},
        )

    await db.commit()
    return await get_company_user_scoped(db, company_id=company_id, user_id=user.id)


async def reset_company_user_password_scoped(
    db: AsyncSession,
    *,
    request,
    actor: User,
    company_id: uuid.UUID,
    user_id: uuid.UUID,
) -> dict:
    ip_address, user_agent = _client_meta(request)
    user = await _get_user_in_company_or_404(db, user_id=user_id, company_id=company_id)

    temporary_password = generate_temporary_password(20)
    user.password_hash = hash_password(temporary_password)
    user.must_change_password = True
    revoked = await auth_service.revoke_user_sessions(db, user_id=user.id)

    await record_audit_event(
        db,
        action="sessions.revoked",
        entity_type="user",
        entity_id=user.id,
        actor_user_id=actor.id,
        company_id=company_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={"scope": "password_reset", "revoked_sessions": revoked},
    )
    await record_audit_event(
        db,
        action="user.updated",
        entity_type="user",
        entity_id=user.id,
        actor_user_id=actor.id,
        company_id=company_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={"changes": {"password_reset_initiated": {"from": False, "to": True}}, "scope": "company"},
    )
    await db.commit()

    return {
        "message": "Password reset initiated. Email provider is not configured; a temporary password was generated for secure manual delivery.",
        "reset_initiated": True,
        "delivery": "manual_temporary_password",
        "temporary_password": temporary_password,
        "must_change_password": True,
    }


async def revoke_company_user_sessions_scoped(
    db: AsyncSession,
    *,
    request,
    actor: User,
    company_id: uuid.UUID,
    user_id: uuid.UUID,
) -> dict:
    ip_address, user_agent = _client_meta(request)
    user = await _get_user_in_company_or_404(db, user_id=user_id, company_id=company_id)
    revoked = await auth_service.revoke_user_sessions(db, user_id=user.id)
    await record_audit_event(
        db,
        action="sessions.revoked",
        entity_type="user",
        entity_id=user.id,
        actor_user_id=actor.id,
        company_id=company_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={"scope": "admin_revoke", "revoked_sessions": revoked},
    )
    await db.commit()
    return {"message": "Sessions revoked", "revoked_sessions": revoked}
