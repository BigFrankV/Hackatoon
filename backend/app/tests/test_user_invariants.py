from __future__ import annotations

import uuid

import pytest

from app.core.exceptions import ConflictError
from app.core.security import hash_password
from app.models.company import Company
from app.models.enums import CompanyStatus, UserRole, UserStatus
from app.models.user import User
from app.services.user_service import _ensure_not_last_active_admin


@pytest.mark.asyncio
async def test_cannot_remove_the_last_active_company_admin(db_session):
    company = Company(
        legal_name="Admin invariant company",
        status=CompanyStatus.ACTIVE,
    )
    db_session.add(company)
    await db_session.flush()

    admin = User(
        company_id=company.id,
        email=f"admin-{uuid.uuid4().hex}@example.com",
        first_name="Company",
        last_name="Admin",
        password_hash=hash_password("test-password"),
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    actor = User(
        company_id=company.id,
        email=f"user-{uuid.uuid4().hex}@example.com",
        first_name="Regular",
        last_name="User",
        password_hash=hash_password("test-password"),
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
    )
    db_session.add_all([admin, actor])
    await db_session.flush()

    with pytest.raises(ConflictError, match="last active admin"):
        await _ensure_not_last_active_admin(
            db_session,
            user=admin,
            actor=actor,
            allow_super_admin_override=False,
        )
