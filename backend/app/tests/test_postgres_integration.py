import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_postgres_test_fixture_uses_an_isolated_schema(
    postgres_db_session: AsyncSession,
):
    schema = await postgres_db_session.scalar(text("SELECT current_schema()"))

    assert schema.startswith("test_")
    assert await postgres_db_session.scalar(text("SELECT COUNT(*) FROM permissions")) > 0
