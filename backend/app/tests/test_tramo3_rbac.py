from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.core.security import hash_password, hash_refresh_token
from app.models.company import Company
from app.models.enums import CompanyStatus, UserRole, UserStatus
from app.models.refresh_token import RefreshToken
from app.models.role import Role
from app.models.user import User


async def create_company(db_session, **overrides) -> Company:
    data = {
        "legal_name": f"Company {uuid.uuid4().hex[:8]}",
        "display_name": "Test Co",
        "tax_id": f"76.{uuid.uuid4().hex[:8]}-1",
        "email": f"contact-{uuid.uuid4().hex[:6]}@example.com",
        "status": CompanyStatus.ACTIVE,
    }
    data.update(overrides)
    company = Company(**data)
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)
    return company


async def create_user(db_session, *, company: Company | None = None, **overrides) -> User:
    password = overrides.pop("password", "Password123!")
    data = {
        "email": f"user-{uuid.uuid4().hex[:8]}@example.com",
        "first_name": "Test",
        "last_name": "User",
        "password_hash": hash_password(password),
        "role": UserRole.USER,
        "status": UserStatus.ACTIVE,
        "company_id": company.id if company else None,
    }
    data.update(overrides)
    role = data["role"]
    data["role"] = await db_session.scalar(select(Role).where(Role.code == role.value))
    user = User(**data)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def login(client, email: str, password: str = "Password123!") -> dict:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()


async def login_token(client, email: str, password: str = "Password123!") -> str:
    body = await login(client, email, password)
    return body["access_token"]


@pytest.mark.asyncio
async def test_user_gets_403_creating_users(client, db_session):
    company = await create_company(db_session)
    user = await create_user(db_session, company=company, email="user@example.com", role=UserRole.USER)
    token = await login_token(client, user.email)

    response = await client.post(
        "/api/v1/company/users",
        headers=auth_header(token),
        json={"first_name": "A", "last_name": "B", "email": "new@example.com"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_gets_403_creating_companies(client, db_session):
    company = await create_company(db_session)
    admin = await create_user(db_session, company=company, email="admin@example.com", role=UserRole.ADMIN)
    token = await login_token(client, admin.email)

    response = await client.post(
        "/api/v1/companies",
        headers=auth_header(token),
        json={
            "legal_name": "New Co",
            "initial_admin": {"first_name": "A", "last_name": "B", "email": "a@newco.com"},
        },
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_cannot_assign_admin_role_or_promote(client, db_session):
    company = await create_company(db_session)
    admin = await create_user(db_session, company=company, email="admin@example.com", role=UserRole.ADMIN)
    target = await create_user(db_session, company=company, email="target@example.com", role=UserRole.USER)
    token = await login_token(client, admin.email)

    # Company-scoped create schema forbids role field.
    response = await client.post(
        "/api/v1/company/users",
        headers=auth_header(token),
        json={
            "first_name": "A",
            "last_name": "B",
            "email": "promoted@example.com",
            "role": "admin",
        },
    )
    assert response.status_code == 422

    # Company-scoped update cannot change role/status/company.
    response = await client.patch(
        f"/api/v1/company/users/{target.id}",
        headers=auth_header(token),
        json={"role": "admin"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_super_admin_can_create_company(client, db_session):
    super_admin = await create_user(
        db_session, company=None, email="sa@example.com", role=UserRole.SUPER_ADMIN
    )
    token = await login_token(client, super_admin.email)

    response = await client.post(
        "/api/v1/companies",
        headers=auth_header(token),
        json={
            "legal_name": "Acme SpA",
            "display_name": "Acme",
            "tax_id": "76.111.222-3",
            "initial_admin": {"first_name": "Ana", "last_name": "Admin", "email": "ana@acme.com"},
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["company"]["legal_name"] == "Acme SpA"
    assert body["initial_admin"]["role"] == "admin"
    assert body["initial_admin"]["must_change_password"] is True
    assert body["initial_admin"]["temporary_password"]
    assert "password" not in str(body["delivery"]).lower() or "temporary" in str(body["delivery"]).lower()


@pytest.mark.asyncio
async def test_profile_cannot_change_role_company_id_status(client, db_session):
    company = await create_company(db_session)
    user = await create_user(db_session, company=company, email="user@example.com", role=UserRole.USER)
    token = await login_token(client, user.email)

    response = await client.patch(
        "/api/v1/auth/me",
        headers=auth_header(token),
        json={"first_name": "Ok", "role": "admin"},
    )
    assert response.status_code == 422

    response = await client.patch(
        "/api/v1/auth/me",
        headers=auth_header(token),
        json={"company_id": str(uuid.uuid4())},
    )
    assert response.status_code == 422

    response = await client.patch(
        "/api/v1/auth/me",
        headers=auth_header(token),
        json={"status": "inactive"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_admin_a_cannot_access_user_of_company_b(client, db_session):
    company_a = await create_company(db_session, legal_name="A")
    company_b = await create_company(db_session, legal_name="B")
    admin_a = await create_user(db_session, company=company_a, email="admina@example.com", role=UserRole.ADMIN)
    user_b = await create_user(db_session, company=company_b, email="userb@example.com", role=UserRole.USER)
    token_a = await login_token(client, admin_a.email)

    # List should only contain company A users.
    list_response = await client.get("/api/v1/company/users", headers=auth_header(token_a))
    assert list_response.status_code == 200
    ids = {item["id"] for item in list_response.json()["items"]}
    assert str(user_b.id) not in ids

    # Direct access should return 404 to avoid existence leak.
    for method, url, kwargs in [
        ("get", f"/api/v1/company/users/{user_b.id}", {}),
        ("patch", f"/api/v1/company/users/{user_b.id}", {"json": {"first_name": "X"}}),
        ("post", f"/api/v1/company/users/{user_b.id}/deactivate", {}),
        ("post", f"/api/v1/company/users/{user_b.id}/activate", {}),
        ("post", f"/api/v1/company/users/{user_b.id}/reset-password", {}),
        ("post", f"/api/v1/company/users/{user_b.id}/revoke-sessions", {}),
    ]:
        response = await getattr(client, method)(url, headers=auth_header(token_a), **kwargs)
        assert response.status_code == 404, (method, url, response.text)


@pytest.mark.asyncio
async def test_changing_company_id_in_body_or_query_does_not_expand_access(client, db_session):
    company_a = await create_company(db_session, legal_name="A")
    company_b = await create_company(db_session, legal_name="B")
    admin_a = await create_user(db_session, company=company_a, email="admina@example.com", role=UserRole.ADMIN)
    user_b = await create_user(db_session, company=company_b, email="userb@example.com", role=UserRole.USER)
    token_a = await login_token(client, admin_a.email)

    # Company-scoped create ignores/rejects company_id and role - schema forbids extra fields.
    response = await client.post(
        "/api/v1/company/users",
        headers=auth_header(token_a),
        json={
            "first_name": "X",
            "last_name": "Y",
            "email": "x@example.com",
            "company_id": str(company_b.id),
        },
    )
    assert response.status_code == 422

    # Query param company_id on company-scoped list is not accepted/used; endpoint has no such param.
    response = await client.get(
        f"/api/v1/company/users?company_id={company_b.id}",
        headers=auth_header(token_a),
    )
    # FastAPI will ignore unknown query params by default; result must still be scoped to company A.
    assert response.status_code == 200
    ids = {item["id"] for item in response.json()["items"]}
    assert str(user_b.id) not in ids

    # Company profile endpoint does not accept company_id.
    response = await client.patch(
        f"/api/v1/company/profile?company_id={company_b.id}",
        headers=auth_header(token_a),
        json={"display_name": "Nope"},
    )
    assert response.status_code == 200
    # Verify company B unchanged
    await db_session.refresh(company_b)
    assert company_b.display_name != "Nope" or company_b.display_name is None


@pytest.mark.asyncio
async def test_company_suspension_blocks_member_login_and_revokes_sessions(client, db_session):
    company = await create_company(db_session)
    admin = await create_user(db_session, company=company, email="admin@example.com", role=UserRole.ADMIN)
    member = await create_user(db_session, company=company, email="member@example.com", role=UserRole.USER)
    super_admin = await create_user(
        db_session, company=None, email="sa@example.com", role=UserRole.SUPER_ADMIN
    )

    member_login = await client.post(
        "/api/v1/auth/login", json={"email": member.email, "password": "Password123!"}
    )
    assert member_login.status_code == 200
    member_refresh = member_login.cookies.get("refresh_token")
    assert member_refresh

    sa_token = await login_token(client, super_admin.email)
    suspend_response = await client.post(
        f"/api/v1/companies/{company.id}/suspend",
        headers=auth_header(sa_token),
        json={"reason": "test"},
    )
    assert suspend_response.status_code == 200
    assert suspend_response.json()["status"] == "suspended"

    # Existing refresh token should be revoked.
    token_hash = hash_refresh_token(member_refresh)
    result = await db_session.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    token_record = result.scalar_one()
    assert token_record.revoked_at is not None

    # Member login should be blocked.
    blocked = await client.post(
        "/api/v1/auth/login", json={"email": member.email, "password": "Password123!"}
    )
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "company_inactive"

    # Admin of suspended company should also be blocked.
    admin_blocked = await client.post(
        "/api/v1/auth/login", json={"email": admin.email, "password": "Password123!"}
    )
    assert admin_blocked.status_code == 403


@pytest.mark.asyncio
async def test_user_deactivation_revokes_sessions(client, db_session):
    company = await create_company(db_session)
    admin = await create_user(db_session, company=company, email="admin@example.com", role=UserRole.ADMIN)
    member = await create_user(db_session, company=company, email="member@example.com", role=UserRole.USER)

    login_response = await client.post(
        "/api/v1/auth/login", json={"email": member.email, "password": "Password123!"}
    )
    assert login_response.status_code == 200
    refresh = login_response.cookies.get("refresh_token")
    assert refresh

    admin_token = await login_token(client, admin.email)
    deactivate_response = await client.post(
        f"/api/v1/company/users/{member.id}/deactivate",
        headers=auth_header(admin_token),
    )
    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["status"] == "inactive"

    token_hash = hash_refresh_token(refresh)
    result = await db_session.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    token_record = result.scalar_one()
    assert token_record.revoked_at is not None


@pytest.mark.asyncio
async def test_audit_logs_created_for_admin_actions_and_no_secrets(client, db_session):
    super_admin = await create_user(
        db_session, company=None, email="sa@example.com", role=UserRole.SUPER_ADMIN
    )
    sa_token = await login_token(client, super_admin.email)

    create_response = await client.post(
        "/api/v1/companies",
        headers=auth_header(sa_token),
        json={
            "legal_name": "Audit Co",
            "initial_admin": {"first_name": "A", "last_name": "B", "email": "admin@auditco.com"},
        },
    )
    assert create_response.status_code == 201

    logs_response = await client.get("/api/v1/audit-logs", headers=auth_header(sa_token))
    assert logs_response.status_code == 200
    logs = logs_response.json()["items"]
    actions = {log["action"] for log in logs}
    assert "company.created" in actions
    assert "user.created" in actions

    serialized = str(logs_response.json()).lower()
    for secret_marker in ["password123", "temporary_password\": \"password", "argon2", "bearer ", "refresh_token="]:
        # "temporary_password" key may appear in other contexts? not in audit logs; check values carefully
        pass
    # Ensure no obvious secrets in audit payload
    assert "password_hash" not in serialized
    assert "refresh_token" not in serialized
    assert "access_token" not in serialized
    # temporary password value should not be in audit logs
    temp_pwd = create_response.json()["initial_admin"]["temporary_password"]
    assert temp_pwd not in str(logs_response.json())


@pytest.mark.asyncio
async def test_company_profile_admin_scoped_and_no_company_id_accepted(client, db_session):
    company = await create_company(db_session, display_name="Old")
    admin = await create_user(db_session, company=company, email="admin@example.com", role=UserRole.ADMIN)
    token = await login_token(client, admin.email)

    get_resp = await client.get("/api/v1/company/profile", headers=auth_header(token))
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == str(company.id)

    patch_resp = await client.patch(
        "/api/v1/company/profile",
        headers=auth_header(token),
        json={"display_name": "New Display", "company_id": str(uuid.uuid4())},
    )
    # company_id is not in schema -> 422
    assert patch_resp.status_code == 422


@pytest.mark.asyncio
async def test_admin_cannot_create_admin_via_company_users(client, db_session):
    company = await create_company(db_session)
    admin = await create_user(db_session, company=company, email="admin@example.com", role=UserRole.ADMIN)
    token = await login_token(client, admin.email)

    resp = await client.post(
        "/api/v1/company/users",
        headers=auth_header(token),
        json={"first_name": "X", "last_name": "Y", "email": "x@example.com", "role": "admin"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_company_scoped_user_endpoints_return_404_for_other_company(client, db_session):
    company_a = await create_company(db_session)
    company_b = await create_company(db_session)
    admin_a = await create_user(db_session, company=company_a, email="admina@example.com", role=UserRole.ADMIN)
    admin_b = await create_user(db_session, company=company_b, email="adminb@example.com", role=UserRole.ADMIN)
    token_a = await login_token(client, admin_a.email)

    resp = await client.get(f"/api/v1/company/users/{admin_b.id}", headers=auth_header(token_a))
    assert resp.status_code == 404
