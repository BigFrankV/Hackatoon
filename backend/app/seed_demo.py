from __future__ import annotations

import asyncio
import os

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, normalize_email
from app.db.session import AsyncSessionFactory
from app.models.company import Company
from app.models.enums import CompanyStatus, UserRole, UserStatus
from app.models.user import User

DEMO_COMPANIES = (
    {
        "legal_name": "Empresa Demo Norte SpA",
        "display_name": "Demo Norte",
        "tax_id": "DEMO-NORTE-001",
        "users": (
            ("admin.norte@hackatoon.dev", "Admin", "Norte", UserRole.ADMIN, "DEV_SEED_NORTH_ADMIN_PASSWORD"),
            ("usuario.norte@hackatoon.dev", "Usuario", "Norte", UserRole.USER, "DEV_SEED_NORTH_USER_PASSWORD"),
        ),
    },
    {
        "legal_name": "Empresa Demo Sur SpA",
        "display_name": "Demo Sur",
        "tax_id": "DEMO-SUR-002",
        "users": (
            ("admin.sur@hackatoon.dev", "Admin", "Sur", UserRole.ADMIN, "DEV_SEED_SOUTH_ADMIN_PASSWORD"),
            ("usuario.sur@hackatoon.dev", "Usuario", "Sur", UserRole.USER, "DEV_SEED_SOUTH_USER_PASSWORD"),
        ),
    },
)


async def seed_demo_data(
    db: AsyncSession,
    *,
    passwords: dict[str, str],
) -> tuple[int, int]:
    created_companies = 0
    created_users = 0
    email_adapter = TypeAdapter(EmailStr)

    for company_data in DEMO_COMPANIES:
        company_result = await db.execute(
            select(Company).where(Company.tax_id == company_data["tax_id"])
        )
        company = company_result.scalar_one_or_none()
        if company is None:
            company = Company(
                legal_name=company_data["legal_name"],
                display_name=company_data["display_name"],
                tax_id=company_data["tax_id"],
                status=CompanyStatus.ACTIVE,
            )
            db.add(company)
            await db.flush()
            created_companies += 1
        elif (
            company.legal_name != company_data["legal_name"]
            or company.display_name != company_data["display_name"]
        ):
            raise ValueError(f"Demo company tax ID already belongs to another company: {company.tax_id}")

        for raw_email, first_name, last_name, role, password_key in company_data["users"]:
            email = normalize_email(str(email_adapter.validate_python(raw_email)))
            password = passwords.get(password_key, "")
            if len(password) < 12:
                raise ValueError(f"{password_key} must contain at least 12 characters.")

            user_result = await db.execute(select(User).where(User.email == email))
            user = user_result.scalar_one_or_none()
            if user is not None:
                if user.company_id != company.id or user.role != role:
                    raise ValueError(f"Demo user email already belongs to a different account: {email}")
                continue

            db.add(
                User(
                    company_id=company.id,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    password_hash=hash_password(password),
                    role=role,
                    status=UserStatus.ACTIVE,
                    must_change_password=True,
                )
            )
            created_users += 1

    await db.commit()
    return created_companies, created_users


async def _run_seed() -> None:
    password_keys = {
        "DEV_SEED_NORTH_ADMIN_PASSWORD",
        "DEV_SEED_NORTH_USER_PASSWORD",
        "DEV_SEED_SOUTH_ADMIN_PASSWORD",
        "DEV_SEED_SOUTH_USER_PASSWORD",
    }
    passwords = {key: os.getenv(key, "") for key in password_keys}
    missing_keys = sorted(key for key, value in passwords.items() if not value)
    if missing_keys:
        raise RuntimeError(f"Set local demo account passwords in .env: {', '.join(missing_keys)}")

    async with AsyncSessionFactory() as db:
        companies_created, users_created = await seed_demo_data(db, passwords=passwords)

    print(
        "Demo seed complete "
        f"(new companies: {companies_created}, new users: {users_created})."
    )


def main() -> None:
    try:
        asyncio.run(_run_seed())
    except ValidationError as exc:
        raise RuntimeError("The fixed demo account emails must be valid.") from exc


if __name__ == "__main__":
    main()
