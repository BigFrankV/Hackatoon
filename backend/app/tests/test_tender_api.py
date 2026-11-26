from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.core.security import hash_password
from app.models.company import Company
from app.models.enums import CompanyStatus, UserRole, UserStatus
from app.models.role import Role
from app.models.user import User


async def _create_admin(db_session) -> User:
    company = Company(
        legal_name=f"Tender API {uuid.uuid4().hex[:8]} SpA",
        status=CompanyStatus.ACTIVE,
    )
    role = await db_session.scalar(select(Role).where(Role.code == UserRole.ADMIN.value))
    user = User(
        company=company,
        role=role,
        email=f"tender-{uuid.uuid4().hex[:8]}@example.com",
        first_name="Tender",
        last_name="Admin",
        password_hash=hash_password("Password123!"),
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.mark.asyncio
async def test_tender_lookup_requires_authentication(client):
    response = await client.get("/api/v1/tenders/2415-30-LP26")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_authenticated_user_can_lookup_tender_by_code(client, db_session, monkeypatch):
    from app.services import tender_service

    user = await _create_admin(db_session)
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "Password123!"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    calls: list[str] = []

    async def fake_lookup(external_id: str) -> dict:
        calls.append(external_id)
        return {
            "external_id": external_id,
            "title": "Adquisición de equipamiento",
            "status": "Publicada",
            "status_code": "5",
            "description": "Compra de equipamiento municipal.",
            "buyer_name": "Municipalidad de Prueba",
            "buyer_code": "1234",
            "published_at": "2026-11-20T12:00:00",
            "closing_at": "2026-12-04T16:00:00",
            "estimated_amount": "1500000",
            "currency": "CLP",
            "official_url": "https://www.mercadopublico.cl/Procurement/Modules/RFB/DetailsAcquisition.aspx?idlicitacion=2415-30-LP26",
            "items": [],
        }

    monkeypatch.setattr(tender_service, "get_public_tender", fake_lookup)
    response = await client.get(
        "/api/v1/tenders/2415-30-LP26",
        headers={"Authorization": f"Bearer {token}"},
    )
    invalid_response = await client.get(
        "/api/v1/tenders/not-a-tender-code",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["external_id"] == "2415-30-LP26"
    assert response.json()["buyer_name"] == "Municipalidad de Prueba"
    assert response.json()["official_url"].startswith("https://www.mercadopublico.cl/")
    assert invalid_response.status_code == 422
    assert calls == ["2415-30-LP26"]
