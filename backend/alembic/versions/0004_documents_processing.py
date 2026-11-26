"""Add private documents and durable processing metadata.

Revision ID: 0004_documents_processing
Revises: 0003_ai_procurement
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004_documents_processing"
down_revision: str | Sequence[str] | None = "0003_ai_procurement"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def upgrade() -> None:
    op.create_table(
        "document_categories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("description", sa.String(300), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_document_categories_code"),
    )

    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("document_kind", sa.String(40), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "document_kind IN ('company', 'tender', 'generated')",
            name="ck_documents_document_kind",
        ),
        sa.CheckConstraint(
            "status IN ('uploaded', 'queued', 'processing', 'completed', 'failed', 'ready')",
            name="ck_documents_status",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["category_id"], ["document_categories.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["created_by", "company_id"],
            ["users.id", "users.company_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "company_id", name="uq_documents_id_company"),
    )
    op.create_index(
        "ix_documents_company_status_updated",
        "documents",
        ["company_id", "status", "updated_at"],
    )
    op.create_index("ix_documents_category_id", "documents", ["category_id"])

    op.create_table(
        "document_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("storage_object_id", sa.Uuid(), nullable=False),
        sa.Column("source_document_id", sa.Uuid(), nullable=True),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("version_number > 0", name="ck_document_versions_version_number"),
        sa.ForeignKeyConstraint(
            ["document_id"], ["documents.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["storage_object_id"], ["storage_objects.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["source_document_id"], ["source_documents.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_id", "version_number", name="uq_document_versions_document_number"
        ),
    )
    op.create_index(
        "ix_document_versions_storage_object_id",
        "document_versions",
        ["storage_object_id"],
    )

    op.create_table(
        "tender_documents",
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("tracked_tender_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("document_role", sa.String(40), nullable=False),
        sa.Column("linked_by", sa.Uuid(), nullable=False),
        sa.Column("linked_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "document_role IN ('administrative', 'technical', 'annex', "
            "'clarification', 'company_evidence', 'other')",
            name="ck_tender_documents_document_role",
        ),
        sa.ForeignKeyConstraint(
            ["tracked_tender_id", "company_id"],
            ["tracked_tenders.id", "tracked_tenders.company_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["document_id", "company_id"],
            ["documents.id", "documents.company_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["linked_by", "company_id"],
            ["users.id", "users.company_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "tracked_tender_id", "document_id", name="pk_tender_documents"
        ),
    )
    op.create_index(
        "ix_tender_documents_company_document",
        "tender_documents",
        ["company_id", "document_id"],
    )

    op.create_table(
        "document_extractions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_version_id", sa.Uuid(), nullable=False),
        sa.Column("extractor_code", sa.String(80), nullable=False),
        sa.Column("extractor_version", sa.String(80), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("text_storage_object_id", sa.Uuid(), nullable=True),
        sa.Column(
            "metadata",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=True,
        ),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "status IN ('queued', 'processing', 'completed', 'failed')",
            name="ck_document_extractions_status",
        ),
        sa.CheckConstraint(
            "started_at IS NULL OR completed_at IS NULL OR completed_at >= started_at",
            name="ck_document_extractions_time_order",
        ),
        sa.ForeignKeyConstraint(
            ["document_version_id"], ["document_versions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["text_storage_object_id"], ["storage_objects.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_version_id",
            "extractor_code",
            "extractor_version",
            name="uq_document_extractions_version_extractor",
        ),
    )
    op.create_index(
        "ix_document_extractions_document_version_id",
        "document_extractions",
        ["document_version_id"],
    )

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("extraction_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("section_label", sa.String(240), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.CHAR(64), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("start_offset", sa.Integer(), nullable=True),
        sa.Column("end_offset", sa.Integer(), nullable=True),
        sa.CheckConstraint("chunk_index >= 0", name="ck_document_chunks_chunk_index"),
        sa.CheckConstraint(
            "page_number IS NULL OR page_number > 0",
            name="ck_document_chunks_page_number",
        ),
        sa.CheckConstraint(
            "token_count IS NULL OR token_count >= 0",
            name="ck_document_chunks_token_count",
        ),
        sa.CheckConstraint(
            "start_offset IS NULL OR start_offset >= 0",
            name="ck_document_chunks_start_offset",
        ),
        sa.CheckConstraint(
            "end_offset IS NULL OR end_offset >= 0",
            name="ck_document_chunks_end_offset",
        ),
        sa.CheckConstraint(
            "start_offset IS NULL OR end_offset IS NULL OR end_offset >= start_offset",
            name="ck_document_chunks_offset_order",
        ),
        sa.ForeignKeyConstraint(
            ["extraction_id"], ["document_extractions.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "extraction_id", "chunk_index", name="uq_document_chunks_extraction_index"
        ),
    )
    op.create_index("ix_document_chunks_extraction_id", "document_chunks", ["extraction_id"])

    op.create_table(
        "document_processing_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("document_version_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by", sa.Uuid(), nullable=True),
        sa.Column("job_type", sa.String(40), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(180), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "job_type IN ('extract', 'chunk', 'embed')",
            name="ck_document_processing_jobs_job_type",
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'processing', 'completed', 'failed', 'cancelled')",
            name="ck_document_processing_jobs_status",
        ),
        sa.CheckConstraint(
            "attempt_count >= 0 AND max_attempts > 0 AND attempt_count <= max_attempts",
            name="ck_document_processing_jobs_attempts",
        ),
        sa.CheckConstraint(
            "started_at IS NULL OR completed_at IS NULL OR completed_at >= started_at",
            name="ck_document_processing_jobs_time_order",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["document_version_id"], ["document_versions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["requested_by"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "idempotency_key", name="uq_document_processing_jobs_idempotency_key"
        ),
    )
    op.create_index(
        "ix_document_processing_jobs_claim",
        "document_processing_jobs",
        ["status", "available_at", "created_at"],
    )
    op.create_index(
        "ix_document_processing_jobs_company_status",
        "document_processing_jobs",
        ["company_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_document_processing_jobs_company_status", table_name="document_processing_jobs")
    op.drop_index("ix_document_processing_jobs_claim", table_name="document_processing_jobs")
    op.drop_table("document_processing_jobs")
    op.drop_index("ix_document_chunks_extraction_id", table_name="document_chunks")
    op.drop_table("document_chunks")
    op.drop_index("ix_document_extractions_document_version_id", table_name="document_extractions")
    op.drop_table("document_extractions")
    op.drop_index("ix_tender_documents_company_document", table_name="tender_documents")
    op.drop_table("tender_documents")
    op.drop_index("ix_document_versions_storage_object_id", table_name="document_versions")
    op.drop_table("document_versions")
    op.drop_index("ix_documents_category_id", table_name="documents")
    op.drop_index("ix_documents_company_status_updated", table_name="documents")
    op.drop_table("documents")
    op.drop_table("document_categories")
