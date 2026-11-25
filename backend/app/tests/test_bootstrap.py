from __future__ import annotations

import pytest
from sqlalchemy import select

from app.bootstrap import bootstrap_superadmin
from app.core.security import verify_password
from app.models.enums import UserRole, UserStatus
from app.models.user import User


@pytest.mark.asyncio
async def test_bootstrap_creates_superadmin_once(db_session):
    created = await bootstrap_superadmin(
        db_session,
        email="  ADMIN@EXAMPLE.COM ",
        password="a-strong-local-password",
    )

    assert created is True
    result = await db_session.execute(select(User).where(User.role == UserRole.SUPER_ADMIN))
    admin = result.scalar_one()
    assert admin.email == "admin@example.com"
    assert admin.status == UserStatus.ACTIVE
    assert admin.company_id is None
    assert admin.must_change_password is True
    assert verify_password(admin.password_hash, "a-strong-local-password")

    created_again = await bootstrap_superadmin(
        db_session,
        email="other@example.com",
        password="another-strong-password",
    )
    assert created_again is False


@pytest.mark.asyncio
async def test_bootstrap_rejects_short_password(db_session):
    with pytest.raises(ValueError, match="at least 12 characters"):
        await bootstrap_superadmin(db_session, email="admin@example.com", password="too-short")
