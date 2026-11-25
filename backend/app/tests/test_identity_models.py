import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import AuditLog, Company, RefreshToken, User
from app.models.enums import CompanyStatus, UserRole, UserStatus


async def _create_company(db_session, **overrides) -> Company:
    data = {
        "legal_name": "Acme SpA",
        "display_name": "Acme",
        "tax_id": "76.123.456-7",
        "email": "contact@acme.com",
        "status": CompanyStatus.ACTIVE,
    }
    data.update(overrides)
    company = Company(**data)
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)
    return company


async def _create_user(db_session, **overrides) -> User:
    data = {
        "email": "user@acme.com",
        "first_name": "Test",
        "last_name": "User",
        "password_hash": "argon2id$hashed",
        "role": UserRole.USER,
        "status": UserStatus.ACTIVE,
    }
    data.update(overrides)
    user = User(**data)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_company_has_uuid_pk_and_timestamps(db_session):
    company = await _create_company(db_session)

    assert isinstance(company.id, uuid.UUID)
    assert company.created_at is not None
    assert company.updated_at is not None
    assert company.status == CompanyStatus.ACTIVE


@pytest.mark.asyncio
async def test_user_super_admin_must_not_have_company(db_session):
    with pytest.raises(IntegrityError):
        await _create_user(
            db_session,
            email="super@platform.com",
            role=UserRole.SUPER_ADMIN,
            company_id=uuid.uuid4(),
        )
    await db_session.rollback()


@pytest.mark.asyncio
async def test_user_admin_requires_company(db_session):
    with pytest.raises(IntegrityError):
        await _create_user(
            db_session,
            email="admin@acme.com",
            role=UserRole.ADMIN,
            company_id=None,
        )
    await db_session.rollback()


@pytest.mark.asyncio
async def test_user_regular_requires_company(db_session):
    with pytest.raises(IntegrityError):
        await _create_user(
            db_session,
            email="member@acme.com",
            role=UserRole.USER,
            company_id=None,
        )
    await db_session.rollback()


@pytest.mark.asyncio
async def test_super_admin_without_company_is_allowed(db_session):
    user = await _create_user(
        db_session,
        email="super@platform.com",
        role=UserRole.SUPER_ADMIN,
        company_id=None,
    )

    assert user.company_id is None
    assert user.role == UserRole.SUPER_ADMIN


@pytest.mark.asyncio
async def test_company_user_with_company_is_allowed(db_session):
    company = await _create_company(db_session)
    user = await _create_user(
        db_session,
        email="admin@acme.com",
        role=UserRole.ADMIN,
        company_id=company.id,
    )

    assert user.company_id == company.id
    assert user.role == UserRole.ADMIN


@pytest.mark.asyncio
async def test_user_email_is_globally_unique(db_session):
    company = await _create_company(db_session)
    await _create_user(db_session, email="dup@acme.com", role=UserRole.USER, company_id=company.id)

    with pytest.raises(IntegrityError):
        await _create_user(
            db_session,
            email="dup@acme.com",
            role=UserRole.USER,
            company_id=company.id,
            first_name="Another",
        )
    await db_session.rollback()


@pytest.mark.asyncio
async def test_user_email_should_be_stored_normalized(db_session):
    company = await _create_company(db_session)
    user = await _create_user(
        db_session,
        email="Person@acme.com".lower(),
        role=UserRole.USER,
        company_id=company.id,
    )

    assert user.email == "person@acme.com"


@pytest.mark.asyncio
async def test_refresh_token_stores_hash_only(db_session):
    company = await _create_company(db_session)
    user = await _create_user(db_session, company_id=company.id, email="rt@acme.com")

    token = RefreshToken(
        user_id=user.id,
        token_hash="sha256:abcdef1234567890",
        family_id=uuid.uuid4(),
        expires_at=datetime.now(UTC),
    )
    db_session.add(token)
    await db_session.commit()
    await db_session.refresh(token)

    assert token.token_hash == "sha256:abcdef1234567890"
    assert not hasattr(token, "token")
    assert not hasattr(token, "plaintext_token")
    assert isinstance(token.id, uuid.UUID)


@pytest.mark.asyncio
async def test_refresh_token_hash_is_unique(db_session):
    company = await _create_company(db_session)
    user = await _create_user(db_session, company_id=company.id, email="rt2@acme.com")

    first = RefreshToken(
        user_id=user.id,
        token_hash="same-hash",
        family_id=uuid.uuid4(),
        expires_at=datetime.now(UTC),
    )
    db_session.add(first)
    await db_session.commit()

    second = RefreshToken(
        user_id=user.id,
        token_hash="same-hash",
        family_id=uuid.uuid4(),
        expires_at=datetime.now(UTC),
    )
    db_session.add(second)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_audit_log_persists_event_metadata_without_secrets(db_session):
    company = await _create_company(db_session)
    actor = await _create_user(
        db_session,
        company_id=company.id,
        email="actor@acme.com",
        role=UserRole.ADMIN,
    )

    log = AuditLog(
        actor_user_id=actor.id,
        company_id=company.id,
        action="user.created",
        entity_type="user",
        entity_id=str(uuid.uuid4()),
        ip_address="127.0.0.1",
        user_agent="pytest",
        event_metadata={"target_role": "user", "source": "test"},
    )
    db_session.add(log)
    await db_session.commit()
    await db_session.refresh(log)

    assert log.id is not None
    assert log.action == "user.created"
    assert log.event_metadata == {"target_role": "user", "source": "test"}
    assert "password" not in str(log.event_metadata).lower()
    assert "token" not in str(log.event_metadata).lower()


@pytest.mark.asyncio
async def test_audit_log_allows_system_event_without_actor(db_session):
    log = AuditLog(
        actor_user_id=None,
        company_id=None,
        action="system.bootstrap",
        entity_type="system",
        entity_id=None,
        event_metadata={"detail": "initialized"},
    )
    db_session.add(log)
    await db_session.commit()
    await db_session.refresh(log)

    assert log.actor_user_id is None
    assert log.company_id is None


@pytest.mark.asyncio
async def test_user_defaults(db_session):
    company = await _create_company(db_session)
    user = User(
        company_id=company.id,
        email="defaults@acme.com",
        first_name="Default",
        last_name="User",
        password_hash="hashed",
        role=UserRole.USER,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    assert user.status == UserStatus.ACTIVE
    assert user.must_change_password is False
    assert user.failed_login_attempts == 0
