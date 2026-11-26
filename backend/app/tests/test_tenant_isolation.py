from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import MetaData, Table, create_engine, select, update

from alembic import command
from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.core.security import hash_password
from app.models.company import Company
from app.models.enums import CompanyStatus, UserRole, UserStatus
from app.models.role import Role
from app.models.user import User
from app.services.audit_service import record_company_audit_event
from app.services.tenant_service import (
    assert_company_access,
    company_id_for_user,
    scope_statement_to_company,
)

PROTECTED_DOMAINS = (
    "tracked_tenders",
    "documents",
    "document_processing_jobs",
    "analysis_runs",
    "conversations",
    "offers",
)


def _upgrade_test_database(db_path: Path, monkeypatch) -> None:
    database_url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    from app.core.config import get_settings

    get_settings.cache_clear()
    backend_dir = Path(__file__).resolve().parents[2]
    monkeypatch.chdir(backend_dir)
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path.as_posix()}")
    command.upgrade(config, "head")
    get_settings.cache_clear()


async def _create_company_user(db_session, name: str) -> User:
    company = Company(
        legal_name=f"{name} SpA",
        status=CompanyStatus.ACTIVE,
    )
    role = await db_session.scalar(select(Role).where(Role.code == UserRole.ADMIN.value))
    user = User(
        company=company,
        role=role,
        email=f"{name.lower()}-{uuid.uuid4().hex[:8]}@example.test",
        first_name="Tenant",
        last_name="Admin",
        password_hash=hash_password("Password123!"),
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


def test_company_scoped_reads_and_writes_cover_product_domains(tmp_path, monkeypatch):
    db_path = tmp_path / "tenant-isolation.db"
    _upgrade_test_database(db_path, monkeypatch)
    company_ids = [uuid.uuid4(), uuid.uuid4()]
    user_ids = [uuid.uuid4(), uuid.uuid4()]
    source_id, opportunity_id = uuid.uuid4(), uuid.uuid4()
    category_id = uuid.uuid4()
    tracked_tender_ids = [uuid.uuid4(), uuid.uuid4()]
    document_ids = [uuid.uuid4(), uuid.uuid4()]
    document_version_ids = [uuid.uuid4(), uuid.uuid4()]
    analysis_ids = [uuid.uuid4(), uuid.uuid4()]
    conversation_ids = [uuid.uuid4(), uuid.uuid4()]
    offer_ids = [uuid.uuid4(), uuid.uuid4()]
    job_ids = [uuid.uuid4(), uuid.uuid4()]

    with sqlite3.connect(db_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        role_id = connection.execute(
            "SELECT id FROM roles WHERE code = 'admin'"
        ).fetchone()[0]
        for index, (company_id, user_id) in enumerate(zip(company_ids, user_ids)):
            connection.execute(
                "INSERT INTO companies (id, legal_name, status) VALUES (?, ?, 'active')",
                (str(company_id), f"Tenant {index}"),
            )
            connection.execute(
                """
                INSERT INTO users (
                    id, company_id, role_id, role_scope, email, first_name,
                    last_name, password_hash, status, must_change_password,
                    failed_login_attempts
                ) VALUES (?, ?, ?, 'company', ?, 'Tenant', 'Admin', 'hash', 'active', 0, 0)
                """,
                (
                    str(user_id),
                    str(company_id),
                    role_id,
                    f"tenant-{index}@example.test",
                ),
            )
        connection.execute(
            "INSERT INTO procurement_sources (id, code, name, base_url, is_enabled) "
            "VALUES (?, 'test', 'Test Source', 'https://example.test', 1)",
            (str(source_id),),
        )
        connection.execute(
            "INSERT INTO procurement_opportunities "
            "(id, source_id, external_id, title, source_url) "
            "VALUES (?, ?, 'external', 'Tender', 'https://example.test/tender')",
            (str(opportunity_id), str(source_id)),
        )
        connection.execute(
            "INSERT INTO document_categories (id, code, name, is_active) "
            "VALUES (?, 'general', 'General', 1)",
            (str(category_id),),
        )
        for index, company_id in enumerate(company_ids):
            connection.execute(
                """
                INSERT INTO tracked_tenders (
                    id, company_id, opportunity_id, created_by, internal_status,
                    priority, decision_status
                ) VALUES (?, ?, ?, ?, 'new', 'normal', 'pending')
                """,
                (
                    str(tracked_tender_ids[index]),
                    str(company_id),
                    str(opportunity_id),
                    str(user_ids[index]),
                ),
            )
            storage_id = uuid.uuid4()
            connection.execute(
                """
                INSERT INTO storage_objects (
                    id, storage_provider, object_key, sha256, byte_size, media_type
                ) VALUES (?, 'local', ?, ?, 1, 'application/pdf')
                """,
                (str(storage_id), f"tenant-{index}/document.pdf", "a" * 64),
            )
            connection.execute(
                """
                INSERT INTO documents (
                    id, company_id, category_id, created_by, title,
                    document_kind, status
                ) VALUES (?, ?, ?, ?, 'Tenant document', 'company', 'ready')
                """,
                (
                    str(document_ids[index]),
                    str(company_id),
                    str(category_id),
                    str(user_ids[index]),
                ),
            )
            connection.execute(
                """
                INSERT INTO document_versions (
                    id, document_id, version_number, storage_object_id,
                    original_filename, created_by
                ) VALUES (?, ?, 1, ?, 'document.pdf', ?)
                """,
                (
                    str(document_version_ids[index]),
                    str(document_ids[index]),
                    str(storage_id),
                    str(user_ids[index]),
                ),
            )
            connection.execute(
                """
                INSERT INTO document_processing_jobs (
                    id, company_id, document_version_id, requested_by, job_type,
                    status, attempt_count, max_attempts, idempotency_key, available_at
                ) VALUES (?, ?, ?, ?, 'extract', 'queued', 0, 3, ?, CURRENT_TIMESTAMP)
                """,
                (
                    str(job_ids[index]),
                    str(company_id),
                    str(document_version_ids[index]),
                    str(user_ids[index]),
                    f"job-{index}",
                ),
            )
            connection.execute(
                """
                INSERT INTO analysis_runs (
                    id, company_id, tracked_tender_id, requested_by, prompt_version,
                    ruleset_version, status
                ) VALUES (?, ?, ?, ?, 'v1', 'v1', 'queued')
                """,
                (
                    str(analysis_ids[index]),
                    str(company_id),
                    str(tracked_tender_ids[index]),
                    str(user_ids[index]),
                ),
            )
            connection.execute(
                """
                INSERT INTO conversations (
                    id, company_id, created_by, context_scope, status
                ) VALUES (?, ?, ?, 'company', 'active')
                """,
                (
                    str(conversation_ids[index]),
                    str(company_id),
                    str(user_ids[index]),
                ),
            )
            connection.execute(
                """
                INSERT INTO offers (
                    id, company_id, tracked_tender_id, created_by, title, status
                ) VALUES (?, ?, ?, ?, 'Tenant offer', 'draft')
                """,
                (
                    str(offer_ids[index]),
                    str(company_id),
                    str(tracked_tender_ids[index]),
                    str(user_ids[index]),
                ),
            )

    resource_ids = {
        "tracked_tenders": tracked_tender_ids,
        "documents": document_ids,
        "document_processing_jobs": job_ids,
        "analysis_runs": analysis_ids,
        "conversations": conversation_ids,
        "offers": offer_ids,
    }
    update_values = {
        "tracked_tenders": {"priority": "high"},
        "documents": {"title": "Cross-tenant update"},
        "document_processing_jobs": {"locked_by": "unauthorized"},
        "analysis_runs": {"failure_code": "unauthorized"},
        "conversations": {"title": "Unauthorized"},
        "offers": {"title": "Unauthorized"},
    }
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    try:
        with engine.begin() as connection:
            tables = {
                name: Table(name, MetaData(), autoload_with=connection)
                for name in PROTECTED_DOMAINS
            }
            for table_name, table in tables.items():
                own_rows = connection.execute(
                    scope_statement_to_company(
                        select(table), table, company_ids[0]
                    )
                ).fetchall()
                assert {row._mapping["id"] for row in own_rows} == {
                    str(resource_ids[table_name][0])
                }

                write = scope_statement_to_company(
                    update(table).where(
                        table.c.id == str(resource_ids[table_name][1])
                    ),
                    table,
                    company_ids[0],
                ).values(**update_values[table_name])
                assert connection.execute(write).rowcount == 0
    finally:
        engine.dispose()



@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ("read", "write"))
async def test_explicit_cross_company_access_is_hidden(operation: str, db_session):
    company_one_user = await _create_company_user(db_session, f"one-{operation}")
    company_two_user = await _create_company_user(db_session, f"two-{operation}")

    with pytest.raises(NotFoundError):
        assert_company_access(company_one_user, company_two_user.company_id)


@pytest.mark.asyncio
async def test_platform_user_cannot_use_company_scoped_context(db_session):
    role = await db_session.scalar(
        select(Role).where(Role.code == UserRole.SUPER_ADMIN.value)
    )
    user = User(
        role=role,
        email=f"platform-{uuid.uuid4().hex[:8]}@example.test",
        first_name="Platform",
        last_name="Admin",
        password_hash=hash_password("Password123!"),
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    await db_session.commit()

    with pytest.raises(PermissionDeniedError):
        company_id_for_user(user)


@pytest.mark.asyncio
async def test_company_audit_derives_tenant_and_redacts_secrets(db_session):
    actor = await _create_company_user(db_session, "audit")

    event = await record_company_audit_event(
        db_session,
        actor=actor,
        action="document.uploaded",
        entity_type="document",
        entity_id=uuid.uuid4(),
        metadata={"nested": {"access_token": "do-not-store", "title": "Plan"}},
    )
    await db_session.commit()

    assert event.company_id == actor.company_id
    assert event.actor_user_id == actor.id
    assert event.event_metadata == {
        "nested": {"access_token": "[REDACTED]", "title": "Plan"}
    }
