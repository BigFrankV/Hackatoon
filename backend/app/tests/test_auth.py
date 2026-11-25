from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.security import hash_password, hash_refresh_token
from app.models.company import Company
from app.models.enums import CompanyStatus, UserRole, UserStatus
from app.models.refresh_token import RefreshToken
from app.models.user import User


async def create_company(db_session, **overrides) -> Company:
    data = {
        "legal_name": "Acme SpA",
        "display_name": "Acme",
        "tax_id": f"76.{uuid.uuid4().hex[:8]}-1",
        "email": "contact@acme.com",
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
        "email": f"user-{uuid.uuid4().hex[:8]}@acme.com",
        "first_name": "Test",
        "last_name": "User",
        "password_hash": hash_password(password),
        "role": UserRole.USER,
        "status": UserStatus.ACTIVE,
        "company_id": company.id if company else None,
    }
    data.update(overrides)
    user = User(**data)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_login_success_returns_access_token_and_sets_refresh_cookie(client, db_session):
    company = await create_company(db_session)
    user = await create_user(db_session, company=company, email="member@acme.com", password="Password123!")

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "member@acme.com", "password": "Password123!"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["expires_in"] > 0
    assert body["user"]["email"] == "member@acme.com"
    assert body["user"]["role"] == "user"
    assert body["user"]["company_id"] == str(company.id)
    assert "refresh_token" not in body
    assert "refresh_token" in response.cookies

    await db_session.refresh(user)
    assert user.last_login_at is not None
    assert user.failed_login_attempts == 0


@pytest.mark.asyncio
async def test_login_fails_with_invalid_password(client, db_session):
    company = await create_company(db_session)
    await create_user(db_session, company=company, email="member@acme.com", password="Password123!")

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "member@acme.com", "password": "wrong-password"},
    )

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "invalid_credentials"


@pytest.mark.asyncio
async def test_login_fails_for_inactive_user(client, db_session):
    company = await create_company(db_session)
    await create_user(
        db_session,
        company=company,
        email="inactive@acme.com",
        password="Password123!",
        status=UserStatus.INACTIVE,
    )

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "inactive@acme.com", "password": "Password123!"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "user_inactive"


@pytest.mark.asyncio
async def test_login_fails_for_suspended_company(client, db_session):
    company = await create_company(db_session, status=CompanyStatus.SUSPENDED)
    await create_user(db_session, company=company, email="member@acme.com", password="Password123!")

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "member@acme.com", "password": "Password123!"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "company_inactive"


@pytest.mark.asyncio
async def test_login_fails_for_locked_account(client, db_session):
    company = await create_company(db_session)
    await create_user(
        db_session,
        company=company,
        email="locked@acme.com",
        password="Password123!",
        locked_until=datetime.now(UTC) + timedelta(minutes=10),
    )

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "locked@acme.com", "password": "Password123!"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "user_locked"


@pytest.mark.asyncio
async def test_login_lockout_after_failed_attempts(client, db_session, monkeypatch):
    from app.core.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "login_lockout_threshold", 3)
    monkeypatch.setattr(settings, "login_lockout_minutes", 15)
    monkeypatch.setattr(settings, "login_rate_limit_account_attempts", 100)
    monkeypatch.setattr(settings, "login_rate_limit_ip_attempts", 100)

    company = await create_company(db_session)
    user = await create_user(db_session, company=company, email="lock@acme.com", password="Password123!")

    for _ in range(3):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "lock@acme.com", "password": "bad-password"},
        )
        assert response.status_code == 401

    await db_session.refresh(user)
    assert user.failed_login_attempts >= 3
    assert user.locked_until is not None

    locked_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "lock@acme.com", "password": "Password123!"},
    )
    assert locked_response.status_code == 403
    assert locked_response.json()["error"]["code"] == "user_locked"


@pytest.mark.asyncio
async def test_refresh_rotates_token_and_returns_new_access_token(client, db_session):
    company = await create_company(db_session)
    await create_user(db_session, company=company, email="member@acme.com", password="Password123!")

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "member@acme.com", "password": "Password123!"},
    )
    assert login_response.status_code == 200
    old_cookie = login_response.cookies.get("refresh_token")
    assert old_cookie

    refresh_response = await client.post("/api/v1/auth/refresh")
    assert refresh_response.status_code == 200
    body = refresh_response.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    new_cookie = refresh_response.cookies.get("refresh_token")
    assert new_cookie
    assert new_cookie != old_cookie


@pytest.mark.asyncio
async def test_refresh_fails_for_expired_token(client, db_session):
    company = await create_company(db_session)
    user = await create_user(db_session, company=company, email="member@acme.com", password="Password123!")

    raw_token = "expired-refresh-token"
    token = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(raw_token),
        family_id=uuid.uuid4(),
        expires_at=datetime.now(UTC) - timedelta(minutes=1),
    )
    db_session.add(token)
    await db_session.commit()

    client.cookies.set("refresh_token", raw_token)
    response = await client.post("/api/v1/auth/refresh")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "refresh_token_expired"


@pytest.mark.asyncio
async def test_refresh_reuse_detection_revokes_family(client, db_session):
    company = await create_company(db_session)
    user = await create_user(db_session, company=company, email="member@acme.com", password="Password123!")

    family_id = uuid.uuid4()
    old_raw = "old-refresh-token"
    old_token = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(old_raw),
        family_id=family_id,
        expires_at=datetime.now(UTC) + timedelta(days=1),
        revoked_at=datetime.now(UTC) - timedelta(minutes=5),
    )
    active_raw = "active-refresh-token"
    active_token = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(active_raw),
        family_id=family_id,
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    db_session.add_all([old_token, active_token])
    await db_session.commit()

    client.cookies.set("refresh_token", old_raw)
    response = await client.post("/api/v1/auth/refresh")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "refresh_token_reuse_detected"

    result = await db_session.execute(
        select(RefreshToken).where(RefreshToken.family_id == family_id)
    )
    tokens = list(result.scalars().all())
    assert tokens
    assert all(t.revoked_at is not None for t in tokens)


@pytest.mark.asyncio
async def test_logout_revokes_current_token_and_clears_cookie(client, db_session):
    company = await create_company(db_session)
    await create_user(db_session, company=company, email="member@acme.com", password="Password123!")

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "member@acme.com", "password": "Password123!"},
    )
    assert login_response.status_code == 200
    raw_cookie = login_response.cookies.get("refresh_token")
    assert raw_cookie

    logout_response = await client.post("/api/v1/auth/logout")
    assert logout_response.status_code == 200
    assert logout_response.json()["message"] == "Logged out"

    token_hash = hash_refresh_token(raw_cookie)
    result = await db_session.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    token = result.scalar_one()
    assert token.revoked_at is not None

    set_cookie_headers = logout_response.headers.get_list("set-cookie")
    assert any("refresh_token=" in h for h in set_cookie_headers)


@pytest.mark.asyncio
async def test_me_requires_auth(client):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_returns_current_user(client, db_session):
    company = await create_company(db_session)
    await create_user(db_session, company=company, email="member@acme.com", password="Password123!")

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "member@acme.com", "password": "Password123!"},
    )
    token = login_response.json()["access_token"]

    me_response = await client.get("/api/v1/auth/me", headers=auth_header(token))
    assert me_response.status_code == 200
    body = me_response.json()
    assert body["email"] == "member@acme.com"
    assert body["company"]["id"] == str(company.id)


@pytest.mark.asyncio
async def test_profile_update_allowlist_rejects_protected_fields(client, db_session):
    company = await create_company(db_session)
    await create_user(db_session, company=company, email="member@acme.com", password="Password123!")

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "member@acme.com", "password": "Password123!"},
    )
    token = login_response.json()["access_token"]

    response = await client.patch(
        "/api/v1/auth/me",
        headers=auth_header(token),
        json={"first_name": "New", "role": "admin"},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"


@pytest.mark.asyncio
async def test_profile_update_allows_safe_fields(client, db_session):
    company = await create_company(db_session)
    await create_user(db_session, company=company, email="member@acme.com", password="Password123!")

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "member@acme.com", "password": "Password123!"},
    )
    token = login_response.json()["access_token"]

    response = await client.patch(
        "/api/v1/auth/me",
        headers=auth_header(token),
        json={"first_name": "Updated", "last_name": "Name"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["first_name"] == "Updated"
    assert body["last_name"] == "Name"


@pytest.mark.asyncio
async def test_change_password_revokes_existing_sessions_and_issues_new_one(client, db_session):
    company = await create_company(db_session)
    await create_user(db_session, company=company, email="member@acme.com", password="Password123!")

    login1 = await client.post(
        "/api/v1/auth/login",
        json={"email": "member@acme.com", "password": "Password123!"},
    )
    token1 = login1.json()["access_token"]
    old_refresh = login1.cookies.get("refresh_token")

    # Simulate another session
    login2 = await client.post(
        "/api/v1/auth/login",
        json={"email": "member@acme.com", "password": "Password123!"},
    )
    assert login2.status_code == 200
    other_refresh = login2.cookies.get("refresh_token")

    client.cookies.set("refresh_token", old_refresh)
    response = await client.post(
        "/api/v1/auth/change-password",
        headers=auth_header(token1),
        json={"current_password": "Password123!", "new_password": "NewPassword123!"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert "refresh_token" in response.cookies
    new_refresh = response.cookies.get("refresh_token")
    assert new_refresh != old_refresh

    # Old refresh token should be revoked
    old_hash = hash_refresh_token(old_refresh)
    result = await db_session.execute(select(RefreshToken).where(RefreshToken.token_hash == old_hash))
    old_token = result.scalar_one()
    assert old_token.revoked_at is not None

    # Other session should also be revoked
    other_hash = hash_refresh_token(other_refresh)
    result = await db_session.execute(select(RefreshToken).where(RefreshToken.token_hash == other_hash))
    other_token = result.scalar_one()
    assert other_token.revoked_at is not None

    # New refresh token should work
    client.cookies.set("refresh_token", new_refresh)
    refresh_response = await client.post("/api/v1/auth/refresh")
    assert refresh_response.status_code == 200


@pytest.mark.asyncio
async def test_sessions_list_and_revoke_own_session(client, db_session):
    company = await create_company(db_session)
    await create_user(db_session, company=company, email="member@acme.com", password="Password123!")

    login1 = await client.post(
        "/api/v1/auth/login",
        json={"email": "member@acme.com", "password": "Password123!"},
    )
    token = login1.json()["access_token"]
    refresh1 = login1.cookies.get("refresh_token")

    login2 = await client.post(
        "/api/v1/auth/login",
        json={"email": "member@acme.com", "password": "Password123!"},
    )
    assert login2.status_code == 200

    client.cookies.set("refresh_token", refresh1)
    sessions_response = await client.get("/api/v1/auth/sessions", headers=auth_header(token))
    assert sessions_response.status_code == 200
    sessions = sessions_response.json()
    assert len(sessions) >= 2
    assert any(s["is_current"] for s in sessions)

    target_session = next(s for s in sessions if not s["is_current"])
    revoke_response = await client.delete(
        f"/api/v1/auth/sessions/{target_session['id']}",
        headers=auth_header(token),
    )
    assert revoke_response.status_code == 200

    result = await db_session.execute(
        select(RefreshToken).where(RefreshToken.id == uuid.UUID(target_session["id"]))
    )
    revoked = result.scalar_one()
    assert revoked.revoked_at is not None


@pytest.mark.asyncio
async def test_get_current_user_rejects_inactive_user(client, db_session):
    company = await create_company(db_session)
    user = await create_user(db_session, company=company, email="member@acme.com", password="Password123!")

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "member@acme.com", "password": "Password123!"},
    )
    token = login.json()["access_token"]

    user.status = UserStatus.INACTIVE
    await db_session.commit()

    me_response = await client.get("/api/v1/auth/me", headers=auth_header(token))
    assert me_response.status_code == 403
    assert me_response.json()["error"]["code"] == "user_inactive"


@pytest.mark.asyncio
async def test_get_current_user_rejects_suspended_company(client, db_session):
    company = await create_company(db_session)
    await create_user(db_session, company=company, email="member@acme.com", password="Password123!")

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "member@acme.com", "password": "Password123!"},
    )
    token = login.json()["access_token"]

    company.status = CompanyStatus.SUSPENDED
    await db_session.commit()

    me_response = await client.get("/api/v1/auth/me", headers=auth_header(token))
    assert me_response.status_code == 403
    assert me_response.json()["error"]["code"] == "company_inactive"


@pytest.mark.asyncio
async def test_refresh_fails_for_revoked_token(client, db_session):
    company = await create_company(db_session)
    user = await create_user(db_session, company=company, email="member@acme.com", password="Password123!")

    raw_token = "revoked-refresh-token"
    token = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(raw_token),
        family_id=uuid.uuid4(),
        expires_at=datetime.now(UTC) + timedelta(days=1),
        revoked_at=datetime.now(UTC),
    )
    db_session.add(token)
    await db_session.commit()

    client.cookies.set("refresh_token", raw_token)
    response = await client.post("/api/v1/auth/refresh")

    assert response.status_code == 401
    assert response.json()["error"]["code"] in {
        "refresh_token_reuse_detected",
        "invalid_refresh_token",
    }


@pytest.mark.asyncio
async def test_session_revocation_is_scoped_to_current_user(client, db_session):
    company = await create_company(db_session)
    await create_user(db_session, company=company, email="a@acme.com", password="Password123!")
    await create_user(db_session, company=company, email="b@acme.com", password="Password123!")

    login_a = await client.post("/api/v1/auth/login", json={"email": "a@acme.com", "password": "Password123!"})
    token_a = login_a.json()["access_token"]

    login_b = await client.post("/api/v1/auth/login", json={"email": "b@acme.com", "password": "Password123!"})
    refresh_b = login_b.cookies.get("refresh_token")
    token_b_hash = hash_refresh_token(refresh_b)
    result = await db_session.execute(select(RefreshToken).where(RefreshToken.token_hash == token_b_hash))
    token_b_record = result.scalar_one()

    response = await client.delete(
        f"/api/v1/auth/sessions/{token_b_record.id}",
        headers=auth_header(token_a),
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_change_password_rejects_wrong_current_password(client, db_session):
    company = await create_company(db_session)
    await create_user(db_session, company=company, email="member@acme.com", password="Password123!")

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "member@acme.com", "password": "Password123!"},
    )
    token = login.json()["access_token"]

    response = await client.post(
        "/api/v1/auth/change-password",
        headers=auth_header(token),
        json={"current_password": "wrong", "new_password": "NewPassword123!"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_current_password"
