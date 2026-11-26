import pytest
from sqlalchemy import select

from app.core.security import verify_password
from app.models.company import Company
from app.models.enums import UserRole
from app.models.user import User
from app.seed_demo import seed_demo_data

DEMO_PASSWORDS = {
    "DEV_SEED_NORTH_ADMIN_PASSWORD": "north-admin-demo-password",
    "DEV_SEED_NORTH_USER_PASSWORD": "north-user-demo-password",
    "DEV_SEED_SOUTH_ADMIN_PASSWORD": "south-admin-demo-password",
    "DEV_SEED_SOUTH_USER_PASSWORD": "south-user-demo-password",
}


@pytest.mark.asyncio
async def test_demo_seed_creates_two_companies_and_four_users_idempotently(db_session):
    companies_created, users_created = await seed_demo_data(
        db_session,
        passwords=DEMO_PASSWORDS,
    )

    assert (companies_created, users_created) == (2, 4)
    companies = (await db_session.execute(select(Company))).scalars().all()
    users = (await db_session.execute(select(User))).scalars().all()
    assert {company.display_name for company in companies} == {"Demo Norte", "Demo Sur"}
    assert len(users) == 4
    for company in companies:
        company_roles = {user.role.code for user in users if user.company_id == company.id}
        assert company_roles == {UserRole.ADMIN.value, UserRole.USER.value}
    assert all(user.must_change_password for user in users)

    admin = next(user for user in users if user.email == "admin.norte@hackatoon.dev")
    original_hash = admin.password_hash

    changed_passwords = {
        key: f"new-{value}" for key, value in DEMO_PASSWORDS.items()
    }
    companies_created, users_created = await seed_demo_data(
        db_session,
        passwords=changed_passwords,
    )

    assert (companies_created, users_created) == (0, 0)
    admin_after_rerun = await db_session.get(User, admin.id)
    assert admin_after_rerun.password_hash == original_hash
    assert verify_password(original_hash, DEMO_PASSWORDS["DEV_SEED_NORTH_ADMIN_PASSWORD"])
