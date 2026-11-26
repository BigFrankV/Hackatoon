from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import UserRole
from app.models.role import Role


async def get_role(db: AsyncSession, role: UserRole | str) -> Role:
    role_code = role.value if isinstance(role, UserRole) else role
    result = await db.execute(select(Role).where(Role.code == role_code))
    role_record = result.scalar_one_or_none()
    if role_record is None:
        raise RuntimeError(f"Required role is missing from the database: {role_code}")
    return role_record
