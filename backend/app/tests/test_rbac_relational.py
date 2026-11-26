import pytest
from sqlalchemy import select

from app.core.security import hash_password
from app.models.company import Company
from app.models.enums import CompanyStatus, UserRole, UserStatus
from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User


async def _create_company(db_session) -> Company:
    company = Company(
        legal_name="Relational RBAC SpA",
        status=CompanyStatus.ACTIVE,
    )
    db_session.add(company)
    await db_session.commit()
    return company


async def _create_user(db_session, company: Company) -> User:
    role = await db_session.scalar(
        select(Role).where(Role.code == UserRole.USER.value)
    )
    user = User(
        company_id=company.id,
        email="relational-rbac@example.com",
        first_name="Test",
        last_name="User",
        password_hash=hash_password("Password123!"),
        role=role,
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.mark.asyncio
async def test_permission_granted_in_relational_tables_controls_authorization(
    client, db_session
):
    company = await _create_company(db_session)
    user = await _create_user(db_session, company)
    token_response = await client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "Password123!"},
    )
    assert token_response.status_code == 200
    headers = {"Authorization": f"Bearer {token_response.json()['access_token']}"}

    denied = await client.get("/api/v1/company/profile", headers=headers)
    assert denied.status_code == 403

    permission = await db_session.scalar(
        select(Permission).where(Permission.code == "company.profile.read")
    )
    user.role.permissions.append(permission)
    await db_session.commit()
    db_session.expire_all()

    granted = await client.get("/api/v1/company/profile", headers=headers)
    assert granted.status_code == 200
    assert granted.json()["id"] == str(company.id)
