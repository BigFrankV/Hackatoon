from __future__ import annotations

import asyncio
import os

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, normalize_email
from app.db.session import AsyncSessionFactory
from app.models.enums import UserRole, UserStatus
from app.models.user import User


async def bootstrap_superadmin(db: AsyncSession, *, email: str, password: str) -> bool:
    normalized_email = normalize_email(str(TypeAdapter(EmailStr).validate_python(email)))
    if len(password) < 12:
        raise ValueError("Bootstrap super_admin password must be at least 12 characters.")

    existing_admin = await db.execute(
        select(User.id).where(User.role == UserRole.SUPER_ADMIN).limit(1)
    )
    if existing_admin.scalar_one_or_none() is not None:
        return False

    existing_email = await db.execute(select(User.id).where(User.email == normalized_email))
    if existing_email.scalar_one_or_none() is not None:
        raise ValueError("Bootstrap email already belongs to a non-super_admin user.")

    db.add(
        User(
            company_id=None,
            email=normalized_email,
            first_name="Platform",
            last_name="Admin",
            password_hash=hash_password(password),
            role=UserRole.SUPER_ADMIN,
            status=UserStatus.ACTIVE,
            must_change_password=True,
        )
    )

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        existing_admin = await db.execute(
            select(User.id).where(User.role == UserRole.SUPER_ADMIN).limit(1)
        )
        if existing_admin.scalar_one_or_none() is not None:
            return False
        raise

    return True


async def _run_bootstrap() -> None:
    email = os.getenv("BOOTSTRAP_SUPERADMIN_EMAIL", "").strip()
    password = os.getenv("BOOTSTRAP_SUPERADMIN_PASSWORD", "")
    if not email or not password:
        raise RuntimeError(
            "Set BOOTSTRAP_SUPERADMIN_EMAIL and BOOTSTRAP_SUPERADMIN_PASSWORD in the root .env."
        )

    async with AsyncSessionFactory() as db:
        created = await bootstrap_superadmin(db, email=email, password=password)

    if created:
        print(f"Created initial super_admin: {normalize_email(email)}")
    else:
        print("A super_admin already exists; bootstrap skipped.")


def main() -> None:
    try:
        asyncio.run(_run_bootstrap())
    except ValidationError as exc:
        raise RuntimeError("BOOTSTRAP_SUPERADMIN_EMAIL must be a valid email address.") from exc


if __name__ == "__main__":
    main()
