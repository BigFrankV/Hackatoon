import sqlite3
import uuid
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command


def _upgrade_to_head(db_path, monkeypatch):
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


def test_product_schema_migrations_create_non_vector_domain_tables(tmp_path, monkeypatch):
    db_path = tmp_path / "product-schema.db"
    _upgrade_to_head(db_path, monkeypatch)

    with sqlite3.connect(db_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }

    assert {
        "ai_providers",
        "ai_models",
        "company_ai_model_policies",
        "user_ai_preferences",
        "procurement_sources",
        "procurement_buyers",
        "procurement_opportunities",
        "source_documents",
        "storage_objects",
        "tracked_tenders",
        "tracked_tender_milestones",
        "tender_tracking_events",
        "document_categories",
        "documents",
        "document_versions",
        "tender_documents",
        "document_extractions",
        "document_chunks",
        "document_processing_jobs",
        "analysis_runs",
        "analysis_requirements",
        "analysis_findings",
        "analysis_evidence",
        "analysis_decisions",
        "conversations",
        "messages",
        "message_citations",
        "offers",
        "offer_versions",
        "offer_checklist_items",
        "offer_documents",
    }.issubset(tables)
    assert "document_embeddings" not in tables
    with sqlite3.connect(db_path) as connection:
        job_columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(document_processing_jobs)"
            )
        }
        product_permissions = {
            row[0]
            for row in connection.execute(
                "SELECT code FROM permissions WHERE code LIKE 'tenders.%' "
                "OR code LIKE 'documents.%' OR code LIKE 'analysis.%' "
                "OR code LIKE 'chat.%' OR code LIKE 'offers.%'"
            )
        }

    assert {"payload", "locked_at", "lease_expires_at", "locked_by", "updated_at"} <= job_columns
    assert {
        "tenders.read",
        "tenders.manage",
        "documents.read",
        "documents.manage",
        "analysis.read",
        "analysis.run",
        "analysis.decide",
        "chat.use",
        "offers.read",
        "offers.manage",
    } == product_permissions


def test_product_schema_rejects_cross_company_relations_and_invalid_values(
    tmp_path, monkeypatch
):
    db_path = tmp_path / "product-constraints.db"
    _upgrade_to_head(db_path, monkeypatch)

    company_one, company_two = str(uuid.uuid4()), str(uuid.uuid4())
    user_one, user_two = str(uuid.uuid4()), str(uuid.uuid4())
    source_id, opportunity_id = str(uuid.uuid4()), str(uuid.uuid4())
    second_opportunity_id = str(uuid.uuid4())
    tender_one, tender_two = str(uuid.uuid4()), str(uuid.uuid4())
    category_id, document_one, document_two = (
        str(uuid.uuid4()),
        str(uuid.uuid4()),
        str(uuid.uuid4()),
    )
    storage_one, storage_two = str(uuid.uuid4()), str(uuid.uuid4())

    with sqlite3.connect(db_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        role_id = connection.execute(
            "SELECT id FROM roles WHERE code = 'admin'"
        ).fetchone()[0]
        for company_id, user_id, email in (
            (company_one, user_one, "one@example.com"),
            (company_two, user_two, "two@example.com"),
        ):
            connection.execute(
                "INSERT INTO companies (id, legal_name, status) VALUES (?, ?, ?)",
                (company_id, f"Company {email}", "active"),
            )
            connection.execute(
                """
                INSERT INTO users (
                    id, company_id, role_id, role_scope, email, first_name,
                    last_name, password_hash, status, must_change_password,
                    failed_login_attempts
                ) VALUES (?, ?, ?, 'company', ?, 'Test', 'User', 'hash', 'active', 0, 0)
                """,
                (user_id, company_id, role_id, email),
            )

        connection.execute(
            "INSERT INTO procurement_sources (id, code, name, base_url, is_enabled) "
            "VALUES (?, 'test', 'Test Source', 'https://example.test', 1)",
            (source_id,),
        )
        connection.execute(
            """
            INSERT INTO procurement_opportunities (
                id, source_id, external_id, title, source_url
            ) VALUES (?, ?, 'external-1', 'Tender', 'https://example.test/tender')
            """,
            (opportunity_id, source_id),
        )
        connection.execute(
            """
            INSERT INTO procurement_opportunities (
                id, source_id, external_id, title, source_url
            ) VALUES (?, ?, 'external-2', 'Tender 2', 'https://example.test/tender-2')
            """,
            (second_opportunity_id, source_id),
        )
        for tender_id, company_id, user_id in (
            (tender_one, company_one, user_one),
            (tender_two, company_two, user_two),
        ):
            connection.execute(
                """
                INSERT INTO tracked_tenders (
                    id, company_id, opportunity_id, created_by, internal_status,
                    priority, decision_status
                ) VALUES (?, ?, ?, ?, 'new', 'normal', 'pending')
                """,
                (tender_id, company_id, opportunity_id, user_id),
            )

        connection.execute(
            """
            INSERT INTO document_categories (id, code, name, is_active)
            VALUES (?, 'general', 'General', 1)
            """,
            (category_id,),
        )
        for storage_id, key, digest in (
            (storage_one, "one/file.pdf", "a" * 64),
            (storage_two, "two/file.pdf", "b" * 64),
        ):
            connection.execute(
                """
                INSERT INTO storage_objects (
                    id, storage_provider, object_key, sha256, byte_size, media_type
                ) VALUES (?, 'local', ?, ?, 1, 'application/pdf')
                """,
                (storage_id, key, digest),
            )
        for document_id, company_id, user_id, storage_id in (
            (document_one, company_one, user_one, storage_one),
            (document_two, company_two, user_two, storage_two),
        ):
            connection.execute(
                """
                INSERT INTO documents (
                    id, company_id, category_id, created_by, title,
                    document_kind, status
                ) VALUES (?, ?, ?, ?, 'Document', 'company', 'ready')
                """,
                (document_id, company_id, category_id, user_id),
            )
            connection.execute(
                """
                INSERT INTO document_versions (
                    id, document_id, version_number, storage_object_id,
                    original_filename, created_by
                ) VALUES (?, ?, 1, ?, 'file.pdf', ?)
                """,
                (str(uuid.uuid4()), document_id, storage_id, user_id),
            )

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO tracked_tenders (
                    id, company_id, opportunity_id, assigned_user_id, created_by,
                    internal_status, priority, decision_status
                ) VALUES (?, ?, ?, ?, ?, 'new', 'normal', 'pending')
                """,
                (
                    str(uuid.uuid4()),
                    company_one,
                    second_opportunity_id,
                    user_two,
                    user_one,
                ),
            )

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO tender_documents (
                    company_id, tracked_tender_id, document_id, document_role,
                    linked_by
                ) VALUES (?, ?, ?, 'technical', ?)
                """,
                (company_one, tender_one, document_two, user_one),
            )

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO tracked_tenders (
                    id, company_id, opportunity_id, created_by, internal_status,
                    priority, decision_status
                ) VALUES (?, ?, ?, ?, 'invalid', 'normal', 'pending')
                """,
                (str(uuid.uuid4()), company_one, second_opportunity_id, user_one),
            )

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO procurement_opportunities (
                    id, source_id, external_id, title, estimated_amount, source_url
                ) VALUES (?, ?, 'external-negative', 'Invalid', -1, 'https://example.test')
                """,
                (str(uuid.uuid4()), source_id),
            )
