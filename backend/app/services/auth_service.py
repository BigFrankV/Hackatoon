from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import Select, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.exceptions import (
    AuthenticationError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
)
from app.core.rate_limit import login_rate_limiter
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    normalize_email,
    verify_password,
)
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.enums import CompanyStatus, UserStatus
from app.models.refresh_token import RefreshToken
from app.models.role import Role
from app.models.user import User
from app.services.audit_service import record_audit_event


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _client_meta(request) -> tuple[str | None, str | None]:
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    if user_agent and len(user_agent) > 512:
        user_agent = user_agent[:512]
    return ip, user_agent


async def _get_user_by_email(db: AsyncSession, email: str) -> User | None:
    stmt: Select[tuple[User]] = (
        select(User)
        .options(
            selectinload(User.company),
            selectinload(User.role).selectinload(Role.permissions),
        )
        .where(User.email == normalize_email(email))
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def _get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    stmt = (
        select(User)
        .options(
            selectinload(User.company),
            selectinload(User.role).selectinload(Role.permissions),
        )
        .where(User.id == user_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


def _ensure_user_can_authenticate(user: User) -> None:
    now = _utcnow()
    locked_until = _as_utc(user.locked_until)
    if locked_until and locked_until > now:
        raise PermissionDeniedError("User account is temporarily locked", code="user_locked")
    if user.status != UserStatus.ACTIVE:
        raise PermissionDeniedError("User account is not active", code="user_inactive")
    if user.company_id is not None:
        company = user.company
        if company is None or company.status != CompanyStatus.ACTIVE:
            raise PermissionDeniedError("Company is not active", code="company_inactive")


async def _check_login_rate_limit(*, email: str, ip_address: str | None) -> None:
    settings = get_settings()
    account_key = f"login:account:{normalize_email(email)}"
    ip_key = f"login:ip:{ip_address or 'unknown'}"
    account_ok = await login_rate_limiter.hit(
        account_key,
        limit=settings.login_rate_limit_account_attempts,
        window_seconds=settings.login_rate_limit_window_seconds,
    )
    ip_ok = await login_rate_limiter.hit(
        ip_key,
        limit=settings.login_rate_limit_ip_attempts,
        window_seconds=settings.login_rate_limit_window_seconds,
    )
    if not account_ok or not ip_ok:
        raise RateLimitError("Too many login attempts. Please try again later.")


def _lockout_delta(failed_attempts: int) -> timedelta:
    settings = get_settings()
    threshold = settings.login_lockout_threshold
    if failed_attempts < threshold:
        return timedelta(0)
    # Progressive lockout: doubles for each threshold window, capped.
    level = max(0, (failed_attempts - threshold) // threshold)
    minutes = settings.login_lockout_minutes * (2**level)
    minutes = min(minutes, 24 * 60)
    return timedelta(minutes=minutes)


async def _register_failed_login(db: AsyncSession, user: User) -> None:
    user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
    delta = _lockout_delta(user.failed_login_attempts)
    if delta.total_seconds() > 0:
        user.locked_until = _utcnow() + delta
        if user.status == UserStatus.ACTIVE:
            # Keep status active; locked_until enforces temporary lock.
            pass
    await db.flush()


async def _register_successful_login(db: AsyncSession, user: User) -> None:
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = _utcnow()
    await db.flush()


async def _issue_refresh_token(
    db: AsyncSession,
    *,
    user: User,
    family_id: uuid.UUID | None = None,
    user_agent: str | None,
    ip_address: str | None,
) -> tuple[str, RefreshToken]:
    settings = get_settings()
    raw_token = generate_refresh_token()
    token_hash = hash_refresh_token(raw_token)
    now = _utcnow()
    record = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        family_id=family_id or uuid.uuid4(),
        expires_at=now + timedelta(days=settings.refresh_token_expire_days),
        user_agent=user_agent,
        ip_address=ip_address,
    )
    db.add(record)
    await db.flush()
    return raw_token, record


async def _revoke_refresh_token(
    db: AsyncSession,
    token: RefreshToken,
    *,
    replaced_by_id: uuid.UUID | None = None,
    reuse_detected: bool = False,
) -> None:
    now = _utcnow()
    if token.revoked_at is None:
        token.revoked_at = now
    token.replaced_by_id = replaced_by_id
    if reuse_detected and token.reuse_detected_at is None:
        token.reuse_detected_at = now
    await db.flush()


async def _revoke_family(db: AsyncSession, *, family_id: uuid.UUID) -> int:
    now = _utcnow()
    stmt = (
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    result = await db.execute(stmt)
    await db.flush()
    return int(result.rowcount or 0)


async def _revoke_all_user_tokens(db: AsyncSession, *, user_id: uuid.UUID) -> int:
    now = _utcnow()
    stmt = (
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    result = await db.execute(stmt)
    await db.flush()
    return int(result.rowcount or 0)


def _build_user_public_payload(user: User) -> dict:
    company_payload = None
    if user.company is not None:
        company_payload = {
            "id": user.company.id,
            "display_name": user.company.display_name,
            "legal_name": user.company.legal_name,
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
        "permissions": sorted(permission.code for permission in user.role.permissions),
    }


async def login(db: AsyncSession, *, request, email: str, password: str) -> dict:
    settings = get_settings()
    ip_address, user_agent = _client_meta(request)
    normalized_email = normalize_email(email)

    await _check_login_rate_limit(email=normalized_email, ip_address=ip_address)

    user = await _get_user_by_email(db, normalized_email)
    if user is None:
        await record_audit_event(
            db,
            action="auth.login.failed",
            entity_type="user",
            entity_id=None,
            actor_user_id=None,
            company_id=None,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"reason": "invalid_credentials", "email": normalized_email},
        )
        await db.commit()
        raise AuthenticationError("Invalid credentials", code="invalid_credentials")

    locked_until = _as_utc(user.locked_until)
    if locked_until and locked_until <= _utcnow():
        user.locked_until = None
        user.failed_login_attempts = 0
        await db.flush()

    try:
        _ensure_user_can_authenticate(user)
    except PermissionDeniedError as exc:
        await record_audit_event(
            db,
            action="auth.login.failed",
            entity_type="user",
            entity_id=user.id,
            actor_user_id=user.id,
            company_id=user.company_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"reason": exc.code},
        )
        await db.commit()
        raise

    if not verify_password(user.password_hash, password):
        await _register_failed_login(db, user)
        await record_audit_event(
            db,
            action="auth.login.failed",
            entity_type="user",
            entity_id=user.id,
            actor_user_id=user.id,
            company_id=user.company_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"reason": "invalid_credentials"},
        )
        await db.commit()
        raise AuthenticationError("Invalid credentials", code="invalid_credentials")

    await _register_successful_login(db, user)

    access_token, expires_in, _ = create_access_token(
        subject=str(user.id),
        role=user.role.code,
        company_id=str(user.company_id) if user.company_id else None,
        expires_minutes=settings.access_token_expire_minutes,
    )
    raw_refresh, refresh_record = await _issue_refresh_token(
        db, user=user, user_agent=user_agent, ip_address=ip_address
    )

    await record_audit_event(
        db,
        action="auth.login.success",
        entity_type="user",
        entity_id=user.id,
        actor_user_id=user.id,
        company_id=user.company_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={"refresh_token_id": str(refresh_record.id)},
    )
    await db.commit()
    refreshed_user = await _get_user_by_id(db, user.id)
    if refreshed_user is None:
        raise AuthenticationError("User not found", code="user_not_found")
    user = refreshed_user

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": expires_in,
        "user": _build_user_public_payload(user),
        "refresh_token": raw_refresh,
    }


async def refresh_session(db: AsyncSession, *, request, raw_refresh_token: str | None) -> dict:
    if not raw_refresh_token:
        raise AuthenticationError("Missing refresh token", code="missing_refresh_token")

    ip_address, user_agent = _client_meta(request)
    token_hash = hash_refresh_token(raw_refresh_token)
    stmt = (
        select(RefreshToken)
        .options(
            selectinload(RefreshToken.user).selectinload(User.company),
            selectinload(RefreshToken.user)
            .selectinload(User.role)
            .selectinload(Role.permissions),
        )
        .where(RefreshToken.token_hash == token_hash)
    )
    result = await db.execute(stmt)
    token = result.scalar_one_or_none()

    if token is None:
        raise AuthenticationError("Invalid refresh token", code="invalid_refresh_token")

    now = _utcnow()
    if token.reuse_detected_at is not None or token.revoked_at is not None or token.replaced_by_id is not None:
        await _revoke_family(db, family_id=token.family_id)
        await record_audit_event(
            db,
            action="auth.refresh.reuse_detected",
            entity_type="refresh_token",
            entity_id=token.id,
            actor_user_id=token.user_id,
            company_id=token.user.company_id if token.user else None,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"family_id": str(token.family_id)},
        )
        await db.commit()
        raise AuthenticationError("Refresh token reuse detected", code="refresh_token_reuse_detected")

    if _as_utc(token.expires_at) <= now:
        await _revoke_refresh_token(db, token)
        await record_audit_event(
            db,
            action="auth.refresh.failed",
            entity_type="refresh_token",
            entity_id=token.id,
            actor_user_id=token.user_id,
            company_id=token.user.company_id if token.user else None,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"reason": "expired"},
        )
        await db.commit()
        raise AuthenticationError("Refresh token expired", code="refresh_token_expired")

    user = token.user
    if user is None:
        await _revoke_refresh_token(db, token)
        await db.commit()
        raise AuthenticationError("Invalid refresh token", code="invalid_refresh_token")

    try:
        _ensure_user_can_authenticate(user)
    except PermissionDeniedError as exc:
        await _revoke_refresh_token(db, token)
        await record_audit_event(
            db,
            action="auth.refresh.failed",
            entity_type="refresh_token",
            entity_id=token.id,
            actor_user_id=user.id,
            company_id=user.company_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"reason": exc.code},
        )
        await db.commit()
        raise

    raw_new_refresh, new_refresh = await _issue_refresh_token(
        db,
        user=user,
        family_id=token.family_id,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    await _revoke_refresh_token(db, token, replaced_by_id=new_refresh.id)

    settings = get_settings()
    access_token, expires_in, _ = create_access_token(
        subject=str(user.id),
        role=user.role.code,
        company_id=str(user.company_id) if user.company_id else None,
        expires_minutes=settings.access_token_expire_minutes,
    )

    await record_audit_event(
        db,
        action="auth.refresh",
        entity_type="refresh_token",
        entity_id=new_refresh.id,
        actor_user_id=user.id,
        company_id=user.company_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={
            "previous_token_id": str(token.id),
            "family_id": str(token.family_id),
        },
    )
    await db.commit()

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": expires_in,
        "refresh_token": raw_new_refresh,
    }


async def logout(db: AsyncSession, *, request, raw_refresh_token: str | None) -> None:
    ip_address, user_agent = _client_meta(request)
    if not raw_refresh_token:
        return

    token_hash = hash_refresh_token(raw_refresh_token)
    stmt = select(RefreshToken).options(selectinload(RefreshToken.user)).where(
        RefreshToken.token_hash == token_hash
    )
    result = await db.execute(stmt)
    token = result.scalar_one_or_none()
    if token is None:
        return

    if token.revoked_at is None:
        await _revoke_refresh_token(db, token)
        await record_audit_event(
            db,
            action="auth.logout",
            entity_type="refresh_token",
            entity_id=token.id,
            actor_user_id=token.user_id,
            company_id=token.user.company_id if token.user else None,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"family_id": str(token.family_id)},
        )
        await db.commit()


async def get_current_user_profile(user: User) -> dict:
    return _build_user_public_payload(user)


async def update_profile(
    db: AsyncSession,
    *,
    request,
    user: User,
    first_name: str | None,
    last_name: str | None,
) -> dict:
    ip_address, user_agent = _client_meta(request)
    changed: dict[str, dict[str, str | None]] = {}

    if first_name is not None and first_name != user.first_name:
        changed["first_name"] = {"from": user.first_name, "to": first_name}
        user.first_name = first_name
    if last_name is not None and last_name != user.last_name:
        changed["last_name"] = {"from": user.last_name, "to": last_name}
        user.last_name = last_name

    if changed:
        await record_audit_event(
            db,
            action="profile.updated",
            entity_type="user",
            entity_id=user.id,
            actor_user_id=user.id,
            company_id=user.company_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"fields": changed},
        )
        await db.commit()
        await db.refresh(user)
    else:
        await db.commit()

    # Ensure company relation available
    await db.refresh(user)
    full_user = await _get_user_by_id(db, user.id)
    return _build_user_public_payload(full_user or user)


async def change_password(
    db: AsyncSession,
    *,
    request,
    user: User,
    current_password: str,
    new_password: str,
) -> dict:
    ip_address, user_agent = _client_meta(request)

    if not verify_password(user.password_hash, current_password):
        raise AuthenticationError("Current password is invalid", code="invalid_current_password")

    if verify_password(user.password_hash, new_password):
        raise PermissionDeniedError(
            "New password must be different from current password",
            code="password_unchanged",
        )

    if len(new_password) < 8:
        raise PermissionDeniedError("Password does not meet policy", code="weak_password")

    user.password_hash = hash_password(new_password)
    user.must_change_password = False

    revoked_count = await _revoke_all_user_tokens(db, user_id=user.id)

    # Issue a fresh session for the current client.
    raw_refresh, refresh_record = await _issue_refresh_token(
        db,
        user=user,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    settings = get_settings()
    access_token, expires_in, _ = create_access_token(
        subject=str(user.id),
        role=user.role.code,
        company_id=str(user.company_id) if user.company_id else None,
        expires_minutes=settings.access_token_expire_minutes,
    )

    await record_audit_event(
        db,
        action="password.changed",
        entity_type="user",
        entity_id=user.id,
        actor_user_id=user.id,
        company_id=user.company_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={
            "revoked_refresh_tokens": revoked_count,
            "new_refresh_token_id": str(refresh_record.id),
        },
    )
    await db.commit()

    return {
        "message": "Password changed successfully. Existing sessions were revoked.",
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": expires_in,
        "refresh_token": raw_refresh,
    }


async def list_sessions(db: AsyncSession, *, user: User, raw_refresh_token: str | None) -> list[dict]:
    current_hash = hash_refresh_token(raw_refresh_token) if raw_refresh_token else None
    stmt = (
        select(RefreshToken)
        .where(RefreshToken.user_id == user.id)
        .order_by(RefreshToken.created_at.desc())
    )
    result = await db.execute(stmt)
    tokens = list(result.scalars().all())
    sessions: list[dict] = []
    for token in tokens:
        sessions.append(
            {
                "id": token.id,
                "family_id": token.family_id,
                "created_at": token.created_at,
                "expires_at": token.expires_at,
                "revoked_at": token.revoked_at,
                "replaced_by_id": token.replaced_by_id,
                "user_agent": token.user_agent,
                "ip_address": token.ip_address,
                "reuse_detected_at": token.reuse_detected_at,
                "is_current": bool(current_hash and token.token_hash == current_hash),
            }
        )
    return sessions


async def revoke_session(
    db: AsyncSession, *, request, user: User, session_id: uuid.UUID
) -> dict:
    ip_address, user_agent = _client_meta(request)
    stmt = select(RefreshToken).where(
        RefreshToken.id == session_id, RefreshToken.user_id == user.id
    )
    result = await db.execute(stmt)
    token = result.scalar_one_or_none()
    if token is None:
        raise NotFoundError("Session not found", code="session_not_found")

    if token.revoked_at is None:
        await _revoke_refresh_token(db, token)
        await record_audit_event(
            db,
            action="sessions.revoked",
            entity_type="refresh_token",
            entity_id=token.id,
            actor_user_id=user.id,
            company_id=user.company_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"session_id": str(session_id), "family_id": str(token.family_id)},
        )
        await db.commit()

    return {"message": "Session revoked"}


async def revoke_user_sessions(db: AsyncSession, *, user_id: uuid.UUID) -> int:
    """Revoke all active refresh tokens for a user."""
    return await _revoke_all_user_tokens(db, user_id=user_id)


async def revoke_company_sessions(db: AsyncSession, *, company_id: uuid.UUID) -> int:
    """Revoke active refresh tokens for all users in a company."""
    now = _utcnow()
    stmt = (
        update(RefreshToken)
        .where(
            RefreshToken.revoked_at.is_(None),
            RefreshToken.user_id.in_(select(User.id).where(User.company_id == company_id)),
        )
        .values(revoked_at=now)
    )
    result = await db.execute(stmt)
    await db.flush()
    return int(result.rowcount or 0)


async def ensure_user_can_authenticate(user: User) -> None:
    """Public wrapper for authentication eligibility checks."""
    _ensure_user_can_authenticate(user)