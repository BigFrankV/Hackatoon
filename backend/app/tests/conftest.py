import os
import uuid
from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, insert, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.permissions import PERMISSIONS
from app.core.rate_limit import login_rate_limiter
from app.models import Base, Permission, Role
from app.models.enums import UserRole
from app.models.role_permission import role_permissions


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        roles = {
            UserRole.SUPER_ADMIN.value: Role(
                code=UserRole.SUPER_ADMIN.value,
                name="Platform Super Admin",
                scope="platform",
            ),
            UserRole.ADMIN.value: Role(
                code=UserRole.ADMIN.value,
                name="Company Admin",
                scope="company",
            ),
            UserRole.USER.value: Role(
                code=UserRole.USER.value,
                name="Company User",
                scope="company",
            ),
        }
        permissions = {
            code: Permission(
                code=code,
                description=code.replace(".", " ").replace("_", " ").title(),
            )
            for code in PERMISSIONS
        }
        session.add_all([*roles.values(), *permissions.values()])
        await session.flush()
        await session.execute(
            insert(role_permissions),
            [
                {
                    "role_id": roles[role_code].id,
                    "permission_id": permissions[permission_code].id,
                }
                for permission_code, role_codes in PERMISSIONS.items()
                for role_code in role_codes
            ],
        )
        await session.commit()
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def postgres_db_session() -> AsyncGenerator[AsyncSession, None]:
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        import pytest

        pytest.skip("Set TEST_DATABASE_URL to an isolated PostgreSQL test database")
    if not database_url.startswith("postgresql+asyncpg://"):
        import pytest

        pytest.fail("TEST_DATABASE_URL must use the postgresql+asyncpg driver")

    schema = f"test_{uuid.uuid4().hex}"
    engine = create_async_engine(
        database_url,
        connect_args={"server_settings": {"search_path": schema}},
    )
    async with engine.begin() as connection:
        await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    try:
        async with session_factory() as session:
            roles = {
                UserRole.SUPER_ADMIN.value: Role(
                    code=UserRole.SUPER_ADMIN.value,
                    name="Platform Super Admin",
                    scope="platform",
                ),
                UserRole.ADMIN.value: Role(
                    code=UserRole.ADMIN.value,
                    name="Company Admin",
                    scope="company",
                ),
                UserRole.USER.value: Role(
                    code=UserRole.USER.value,
                    name="Company User",
                    scope="company",
                ),
            }
            permissions = {
                code: Permission(
                    code=code,
                    description=code.replace(".", " ").replace("_", " ").title(),
                )
                for code in PERMISSIONS
            }
            session.add_all([*roles.values(), *permissions.values()])
            await session.flush()
            await session.execute(
                insert(role_permissions),
                [
                    {
                        "role_id": roles[role_code].id,
                        "permission_id": permissions[permission_code].id,
                    }
                    for permission_code, role_codes in PERMISSIONS.items()
                    for role_code in role_codes
                ],
            )
            await session.commit()
            yield session
    finally:
        async with engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def _reset_rate_limiter() -> AsyncGenerator[None, None]:
    await login_rate_limiter.reset()
    yield
    await login_rate_limiter.reset()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    from app.api.dependencies.database import get_db
    from app.main import app

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client
    app.dependency_overrides.clear()
