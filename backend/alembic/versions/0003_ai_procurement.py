"""Add AI catalogs, procurement catalog, and company tracking.

Revision ID: 0003_ai_procurement
Revises: 0002_relational_rbac
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0003_ai_procurement"
down_revision: str | Sequence[str] | None = "0002_relational_rbac"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def upgrade() -> None:
    op.create_index(
        "uq_users_id_company_id",
        "users",
        ["id", "company_id"],
        unique=True,
    )

    op.create_table(
        "ai_providers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(60), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("provider_type", sa.String(30), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_ai_providers_code"),
    )
    op.create_table(
        "ai_models",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider_id", sa.Uuid(), nullable=False),
        sa.Column("model_code", sa.String(160), nullable=False),
        sa.Column("display_name", sa.String(160), nullable=False),
        sa.Column("supports_chat", sa.Boolean(), nullable=False),
        sa.Column("supports_embeddings", sa.Boolean(), nullable=False),
        sa.Column("supports_tools", sa.Boolean(), nullable=False),
        sa.Column("context_window", sa.Integer(), nullable=True),
        sa.Column("embedding_dimension", sa.Integer(), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "context_window IS NULL OR context_window > 0",
            name="ck_ai_models_context_window",
        ),
        sa.CheckConstraint(
            "embedding_dimension IS NULL OR embedding_dimension > 0",
            name="ck_ai_models_embedding_dimension",
        ),
        sa.ForeignKeyConstraint(
            ["provider_id"], ["ai_providers.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider_id", "model_code", name="uq_ai_models_provider_model"
        ),
    )
    op.create_index("ix_ai_models_provider_id", "ai_models", ["provider_id"])

    op.create_table(
        "company_ai_model_policies",
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("model_id", sa.Uuid(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("allowed_for_chat", sa.Boolean(), nullable=False),
        sa.Column("allowed_for_embeddings", sa.Boolean(), nullable=False),
        sa.Column("is_default_chat", sa.Boolean(), nullable=False),
        sa.Column("is_default_embedding", sa.Boolean(), nullable=False),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "NOT is_default_chat OR (enabled AND allowed_for_chat)",
            name="ck_company_ai_default_chat_allowed",
        ),
        sa.CheckConstraint(
            "NOT is_default_embedding OR (enabled AND allowed_for_embeddings)",
            name="ck_company_ai_default_embedding_allowed",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["model_id"], ["ai_models.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("company_id", "model_id"),
    )
    op.create_index(
        "uq_company_ai_default_chat",
        "company_ai_model_policies",
        ["company_id"],
        unique=True,
        sqlite_where=sa.text("is_default_chat = 1"),
        postgresql_where=sa.text("is_default_chat"),
    )
    op.create_index(
        "uq_company_ai_default_embedding",
        "company_ai_model_policies",
        ["company_id"],
        unique=True,
        sqlite_where=sa.text("is_default_embedding = 1"),
        postgresql_where=sa.text("is_default_embedding"),
    )
    op.create_table(
        "user_ai_preferences",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("preferred_chat_model_id", sa.Uuid(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["preferred_chat_model_id"], ["ai_models.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.create_table(
        "procurement_sources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(60), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_procurement_sources_code"),
    )
    op.create_table(
        "procurement_buyers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(160), nullable=False),
        sa.Column("legal_name", sa.String(240), nullable=False),
        sa.Column("region_code", sa.String(40), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["source_id"], ["procurement_sources.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_id", "external_id", name="uq_procurement_buyers_source_external"
        ),
        sa.UniqueConstraint("id", "source_id", name="uq_procurement_buyers_id_source"),
    )
    op.create_index("ix_procurement_buyers_source_id", "procurement_buyers", ["source_id"])

    op.create_table(
        "storage_objects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("storage_provider", sa.String(60), nullable=False),
        sa.Column("object_key", sa.Text(), nullable=False),
        sa.Column("sha256", sa.CHAR(64), nullable=False),
        sa.Column("byte_size", sa.BigInteger(), nullable=False),
        sa.Column("media_type", sa.String(160), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("byte_size > 0", name="ck_storage_objects_byte_size"),
        sa.CheckConstraint("length(sha256) = 64", name="ck_storage_objects_sha256_length"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("object_key", name="uq_storage_objects_object_key"),
    )

    op.create_table(
        "procurement_opportunities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("buyer_id", sa.Uuid(), nullable=True),
        sa.Column("external_id", sa.String(180), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_status", sa.String(80), nullable=True),
        sa.Column("estimated_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("currency_code", sa.CHAR(3), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closing_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column(
            "source_payload",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=True,
        ),
        sa.Column("source_hash", sa.String(128), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "estimated_amount IS NULL OR estimated_amount >= 0",
            name="ck_procurement_opportunities_estimated_amount",
        ),
        sa.CheckConstraint(
            "currency_code IS NULL OR length(currency_code) = 3",
            name="ck_procurement_opportunities_currency_code",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"], ["procurement_sources.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["buyer_id", "source_id"],
            ["procurement_buyers.id", "procurement_buyers.source_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_id", "external_id", name="uq_procurement_opportunities_source_external"
        ),
    )
    op.create_index(
        "ix_procurement_opportunities_source_closing",
        "procurement_opportunities",
        ["source_id", "closing_at"],
    )
    op.create_index(
        "ix_procurement_opportunities_buyer_id",
        "procurement_opportunities",
        ["buyer_id"],
    )

    op.create_table(
        "source_documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("opportunity_id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(180), nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("media_type", sa.String(160), nullable=True),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("storage_object_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["opportunity_id"], ["procurement_opportunities.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["storage_object_id"], ["storage_objects.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "opportunity_id", "external_id", name="uq_source_documents_opportunity_external"
        ),
    )
    op.create_index(
        "ix_source_documents_opportunity_id", "source_documents", ["opportunity_id"]
    )

    op.create_table(
        "tracked_tenders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("opportunity_id", sa.Uuid(), nullable=False),
        sa.Column("assigned_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("internal_status", sa.String(40), nullable=False),
        sa.Column("priority", sa.String(20), nullable=False),
        sa.Column("decision_status", sa.String(30), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "internal_status IN ('new', 'reviewing', 'preparing', 'submitted', "
            "'awarded', 'not_awarded', 'closed')",
            name="ck_tracked_tenders_internal_status",
        ),
        sa.CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'urgent')",
            name="ck_tracked_tenders_priority",
        ),
        sa.CheckConstraint(
            "decision_status IN ('pending', 'go', 'no_go', 'review_required')",
            name="ck_tracked_tenders_decision_status",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["opportunity_id"], ["procurement_opportunities.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["assigned_user_id", "company_id"],
            ["users.id", "users.company_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by", "company_id"],
            ["users.id", "users.company_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "company_id", name="uq_tracked_tenders_id_company"),
        sa.UniqueConstraint(
            "company_id", "opportunity_id", name="uq_tracked_tenders_company_opportunity"
        ),
    )
    op.create_index(
        "ix_tracked_tenders_company_status_updated",
        "tracked_tenders",
        ["company_id", "internal_status", "updated_at"],
    )
    op.create_index(
        "ix_tracked_tenders_opportunity_id", "tracked_tenders", ["opportunity_id"]
    )
    op.create_index(
        "ix_tracked_tenders_assigned_user_id", "tracked_tenders", ["assigned_user_id"]
    )

    op.create_table(
        "tracked_tender_milestones",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("tracked_tender_id", sa.Uuid(), nullable=False),
        sa.Column("milestone_type", sa.String(60), nullable=False),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_kind", sa.String(20), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "source_kind IN ('source', 'user', 'system')",
            name="ck_tracked_tender_milestones_source_kind",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'completed', 'cancelled')",
            name="ck_tracked_tender_milestones_status",
        ),
        sa.ForeignKeyConstraint(
            ["tracked_tender_id", "company_id"],
            ["tracked_tenders.id", "tracked_tenders.company_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_tracked_tender_milestones_company_due",
        "tracked_tender_milestones",
        ["company_id", "due_at"],
    )
    op.create_index(
        "ix_tracked_tender_milestones_tracked_tender_id",
        "tracked_tender_milestones",
        ["tracked_tender_id"],
    )

    op.create_table(
        "tender_tracking_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("tracked_tender_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("from_status", sa.String(40), nullable=True),
        sa.Column("to_status", sa.String(40), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "metadata",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["tracked_tender_id", "company_id"],
            ["tracked_tenders.id", "tracked_tenders.company_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_tender_tracking_events_company_occurred",
        "tender_tracking_events",
        ["company_id", "occurred_at"],
    )
    op.create_index(
        "ix_tender_tracking_events_tracked_tender_id",
        "tender_tracking_events",
        ["tracked_tender_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_tender_tracking_events_tracked_tender_id", table_name="tender_tracking_events")
    op.drop_index("ix_tender_tracking_events_company_occurred", table_name="tender_tracking_events")
    op.drop_table("tender_tracking_events")
    op.drop_index("ix_tracked_tender_milestones_tracked_tender_id", table_name="tracked_tender_milestones")
    op.drop_index("ix_tracked_tender_milestones_company_due", table_name="tracked_tender_milestones")
    op.drop_table("tracked_tender_milestones")
    op.drop_index("ix_tracked_tenders_assigned_user_id", table_name="tracked_tenders")
    op.drop_index("ix_tracked_tenders_opportunity_id", table_name="tracked_tenders")
    op.drop_index("ix_tracked_tenders_company_status_updated", table_name="tracked_tenders")
    op.drop_table("tracked_tenders")
    op.drop_index("ix_source_documents_opportunity_id", table_name="source_documents")
    op.drop_table("source_documents")
    op.drop_index("ix_procurement_opportunities_buyer_id", table_name="procurement_opportunities")
    op.drop_index("ix_procurement_opportunities_source_closing", table_name="procurement_opportunities")
    op.drop_table("procurement_opportunities")
    op.drop_index("ix_procurement_buyers_source_id", table_name="procurement_buyers")
    op.drop_table("procurement_buyers")
    op.drop_table("storage_objects")
    op.drop_table("procurement_sources")
    op.drop_table("user_ai_preferences")
    op.drop_index("uq_company_ai_default_embedding", table_name="company_ai_model_policies")
    op.drop_index("uq_company_ai_default_chat", table_name="company_ai_model_policies")
    op.drop_table("company_ai_model_policies")
    op.drop_index("ix_ai_models_provider_id", table_name="ai_models")
    op.drop_table("ai_models")
    op.drop_table("ai_providers")
    op.drop_index("uq_users_id_company_id", table_name="users")
