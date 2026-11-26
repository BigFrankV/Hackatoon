"""Add analysis, conversations, and offer preparation entities.

Revision ID: 0005_analysis_chat_offers
Revises: 0004_documents_processing
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005_analysis_chat_offers"
down_revision: str | Sequence[str] | None = "0004_documents_processing"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def upgrade() -> None:
    op.create_table(
        "analysis_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("tracked_tender_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by", sa.Uuid(), nullable=False),
        sa.Column("chat_model_id", sa.Uuid(), nullable=True),
        sa.Column("embedding_model_id", sa.Uuid(), nullable=True),
        sa.Column("prompt_version", sa.String(80), nullable=False),
        sa.Column("ruleset_version", sa.String(80), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("recommendation", sa.String(30), nullable=True),
        sa.Column("executive_summary", sa.Text(), nullable=True),
        sa.Column("report_storage_object_id", sa.Uuid(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_code", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "status IN ('queued', 'processing', 'completed', 'failed', 'cancelled')",
            name="ck_analysis_runs_status",
        ),
        sa.CheckConstraint(
            "recommendation IS NULL OR recommendation IN ('GO', 'NO_GO', 'REVIEW_REQUIRED')",
            name="ck_analysis_runs_recommendation",
        ),
        sa.CheckConstraint(
            "started_at IS NULL OR completed_at IS NULL OR completed_at >= started_at",
            name="ck_analysis_runs_time_order",
        ),
        sa.ForeignKeyConstraint(
            ["tracked_tender_id", "company_id"],
            ["tracked_tenders.id", "tracked_tenders.company_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["requested_by", "company_id"],
            ["users.id", "users.company_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["chat_model_id"], ["ai_models.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["embedding_model_id"], ["ai_models.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["report_storage_object_id"], ["storage_objects.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "company_id", name="uq_analysis_runs_id_company"),
    )
    op.create_index(
        "ix_analysis_runs_company_created",
        "analysis_runs",
        ["company_id", "created_at"],
    )
    op.create_index(
        "ix_analysis_runs_tracked_tender_id",
        "analysis_runs",
        ["tracked_tender_id"],
    )

    op.create_table(
        "analysis_requirements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_run_id", sa.Uuid(), nullable=False),
        sa.Column("requirement_code", sa.String(100), nullable=True),
        sa.Column("category_code", sa.String(60), nullable=False),
        sa.Column("requirement_text", sa.Text(), nullable=False),
        sa.Column("is_mandatory", sa.Boolean(), nullable=False),
        sa.Column("result_status", sa.String(30), nullable=False),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "result_status IN ('compliant', 'non_compliant', 'unverified')",
            name="ck_analysis_requirements_result_status",
        ),
        sa.CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_analysis_requirements_confidence",
        ),
        sa.CheckConstraint("sort_order >= 0", name="ck_analysis_requirements_sort_order"),
        sa.ForeignKeyConstraint(
            ["analysis_run_id"], ["analysis_runs.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_analysis_requirements_analysis_run_id",
        "analysis_requirements",
        ["analysis_run_id"],
    )

    op.create_table(
        "analysis_findings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_run_id", sa.Uuid(), nullable=False),
        sa.Column("finding_type", sa.String(60), nullable=False),
        sa.Column("dimension_code", sa.String(60), nullable=False),
        sa.Column("severity", sa.String(30), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("result_status", sa.String(30), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "severity IN ('info', 'low', 'medium', 'high', 'critical')",
            name="ck_analysis_findings_severity",
        ),
        sa.CheckConstraint(
            "result_status IN ('compliant', 'non_compliant', 'unverified')",
            name="ck_analysis_findings_result_status",
        ),
        sa.CheckConstraint("sort_order >= 0", name="ck_analysis_findings_sort_order"),
        sa.ForeignKeyConstraint(
            ["analysis_run_id"], ["analysis_runs.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_analysis_findings_analysis_run_id",
        "analysis_findings",
        ["analysis_run_id"],
    )

    op.create_table(
        "analysis_evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("finding_id", sa.Uuid(), nullable=True),
        sa.Column("requirement_id", sa.Uuid(), nullable=True),
        sa.Column("document_version_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_id", sa.Uuid(), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("quoted_text", sa.Text(), nullable=False),
        sa.Column("evidence_kind", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "(finding_id IS NOT NULL AND requirement_id IS NULL) OR "
            "(finding_id IS NULL AND requirement_id IS NOT NULL)",
            name="ck_analysis_evidence_exactly_one_parent",
        ),
        sa.CheckConstraint(
            "page_number IS NULL OR page_number > 0",
            name="ck_analysis_evidence_page_number",
        ),
        sa.CheckConstraint(
            "evidence_kind IN ('supports', 'contradicts', 'context')",
            name="ck_analysis_evidence_kind",
        ),
        sa.ForeignKeyConstraint(
            ["finding_id"], ["analysis_findings.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["requirement_id"], ["analysis_requirements.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["document_version_id"], ["document_versions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["chunk_id"], ["document_chunks.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_analysis_evidence_finding_id", "analysis_evidence", ["finding_id"])
    op.create_index(
        "ix_analysis_evidence_requirement_id", "analysis_evidence", ["requirement_id"]
    )
    op.create_index(
        "ix_analysis_evidence_document_version_id",
        "analysis_evidence",
        ["document_version_id"],
    )

    op.create_table(
        "analysis_decisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_run_id", sa.Uuid(), nullable=False),
        sa.Column("decided_by", sa.Uuid(), nullable=False),
        sa.Column("decision", sa.String(30), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "decision IN ('GO', 'NO_GO', 'REVIEW_REQUIRED')",
            name="ck_analysis_decisions_decision",
        ),
        sa.ForeignKeyConstraint(
            ["analysis_run_id"], ["analysis_runs.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["decided_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_analysis_decisions_analysis_run_id",
        "analysis_decisions",
        ["analysis_run_id"],
    )

    op.create_table(
        "conversations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("tracked_tender_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(240), nullable=True),
        sa.Column("context_scope", sa.String(30), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "(context_scope = 'company' AND tracked_tender_id IS NULL) OR "
            "(context_scope = 'tender' AND tracked_tender_id IS NOT NULL)",
            name="ck_conversations_context_scope",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'closed')",
            name="ck_conversations_status",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["created_by", "company_id"],
            ["users.id", "users.company_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tracked_tender_id", "company_id"],
            ["tracked_tenders.id", "tracked_tenders.company_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "company_id", name="uq_conversations_id_company"),
    )
    op.create_index(
        "ix_conversations_company_updated",
        "conversations",
        ["company_id", "updated_at"],
    )
    op.create_index(
        "ix_conversations_tracked_tender_id",
        "conversations",
        ["tracked_tender_id"],
    )

    op.create_table(
        "messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("model_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("sequence_number > 0", name="ck_messages_sequence_number"),
        sa.CheckConstraint(
            "role IN ('system', 'user', 'assistant', 'tool')",
            name="ck_messages_role",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'completed', 'failed')",
            name="ck_messages_status",
        ),
        sa.CheckConstraint(
            "input_tokens IS NULL OR input_tokens >= 0",
            name="ck_messages_input_tokens",
        ),
        sa.CheckConstraint(
            "output_tokens IS NULL OR output_tokens >= 0",
            name="ck_messages_output_tokens",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["conversations.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["model_id"], ["ai_models.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "conversation_id", "sequence_number", name="uq_messages_conversation_sequence"
        ),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])

    op.create_table(
        "message_citations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("message_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_id", sa.Uuid(), nullable=False),
        sa.Column("citation_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("citation_order >= 0", name="ck_message_citations_order"),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["chunk_id"], ["document_chunks.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "message_id", "citation_order", name="uq_message_citations_message_order"
        ),
    )
    op.create_index("ix_message_citations_chunk_id", "message_citations", ["chunk_id"])

    op.create_table(
        "offers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("tracked_tender_id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('draft', 'in_progress', 'ready', 'cancelled')",
            name="ck_offers_status",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["tracked_tender_id", "company_id"],
            ["tracked_tenders.id", "tracked_tenders.company_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by", "company_id"],
            ["users.id", "users.company_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "company_id", name="uq_offers_id_company"),
    )
    op.create_index(
        "ix_offers_company_status_updated",
        "offers",
        ["company_id", "status", "updated_at"],
    )

    op.create_table(
        "offer_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("offer_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("generated_storage_object_id", sa.Uuid(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("version_number > 0", name="ck_offer_versions_version_number"),
        sa.CheckConstraint(
            "status IN ('draft', 'generated', 'approved')",
            name="ck_offer_versions_status",
        ),
        sa.ForeignKeyConstraint(["offer_id"], ["offers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["generated_storage_object_id"], ["storage_objects.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "offer_id", "version_number", name="uq_offer_versions_offer_number"
        ),
    )
    op.create_index("ix_offer_versions_offer_id", "offer_versions", ["offer_id"])

    op.create_table(
        "offer_checklist_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("offer_version_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("assigned_user_id", sa.Uuid(), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('pending', 'in_progress', 'completed', 'blocked')",
            name="ck_offer_checklist_items_status",
        ),
        sa.CheckConstraint("sort_order >= 0", name="ck_offer_checklist_items_sort_order"),
        sa.ForeignKeyConstraint(
            ["offer_version_id"], ["offer_versions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["assigned_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_offer_checklist_items_offer_version_id",
        "offer_checklist_items",
        ["offer_version_id"],
    )

    op.create_table(
        "offer_documents",
        sa.Column("offer_version_id", sa.Uuid(), nullable=False),
        sa.Column("document_version_id", sa.Uuid(), nullable=False),
        sa.Column("included_by", sa.Uuid(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("included_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("sort_order >= 0", name="ck_offer_documents_sort_order"),
        sa.ForeignKeyConstraint(
            ["offer_version_id"], ["offer_versions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["document_version_id"], ["document_versions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["included_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint(
            "offer_version_id", "document_version_id", name="pk_offer_documents"
        ),
    )
    op.create_index(
        "ix_offer_documents_document_version_id",
        "offer_documents",
        ["document_version_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_offer_documents_document_version_id", table_name="offer_documents")
    op.drop_table("offer_documents")
    op.drop_index("ix_offer_checklist_items_offer_version_id", table_name="offer_checklist_items")
    op.drop_table("offer_checklist_items")
    op.drop_index("ix_offer_versions_offer_id", table_name="offer_versions")
    op.drop_table("offer_versions")
    op.drop_index("ix_offers_company_status_updated", table_name="offers")
    op.drop_table("offers")
    op.drop_index("ix_message_citations_chunk_id", table_name="message_citations")
    op.drop_table("message_citations")
    op.drop_index("ix_messages_conversation_id", table_name="messages")
    op.drop_table("messages")
    op.drop_index("ix_conversations_tracked_tender_id", table_name="conversations")
    op.drop_index("ix_conversations_company_updated", table_name="conversations")
    op.drop_table("conversations")
    op.drop_index("ix_analysis_decisions_analysis_run_id", table_name="analysis_decisions")
    op.drop_table("analysis_decisions")
    op.drop_index("ix_analysis_evidence_document_version_id", table_name="analysis_evidence")
    op.drop_index("ix_analysis_evidence_requirement_id", table_name="analysis_evidence")
    op.drop_index("ix_analysis_evidence_finding_id", table_name="analysis_evidence")
    op.drop_table("analysis_evidence")
    op.drop_index("ix_analysis_findings_analysis_run_id", table_name="analysis_findings")
    op.drop_table("analysis_findings")
    op.drop_index("ix_analysis_requirements_analysis_run_id", table_name="analysis_requirements")
    op.drop_table("analysis_requirements")
    op.drop_index("ix_analysis_runs_tracked_tender_id", table_name="analysis_runs")
    op.drop_index("ix_analysis_runs_company_created", table_name="analysis_runs")
    op.drop_table("analysis_runs")
