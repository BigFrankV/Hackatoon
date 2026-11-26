"""Add local Ollama model catalog and pgvector document embeddings.

Revision ID: 0007_local_knowledge_vectors
Revises: 0006_foundation_jobs_permissions
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

from alembic import op

revision: str = "0007_local_knowledge_vectors"
down_revision: str | Sequence[str] | None = "0006_foundation_jobs_permissions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _seed_ollama_models() -> None:
    providers = sa.table(
        "ai_providers",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("provider_type", sa.String()),
        sa.column("is_enabled", sa.Boolean()),
    )
    models = sa.table(
        "ai_models",
        sa.column("id", sa.Uuid()),
        sa.column("provider_id", sa.Uuid()),
        sa.column("model_code", sa.String()),
        sa.column("display_name", sa.String()),
        sa.column("supports_chat", sa.Boolean()),
        sa.column("supports_embeddings", sa.Boolean()),
        sa.column("supports_tools", sa.Boolean()),
        sa.column("embedding_dimension", sa.Integer()),
        sa.column("is_enabled", sa.Boolean()),
    )
    connection = op.get_bind()
    provider_id = connection.scalar(
        sa.select(providers.c.id).where(providers.c.code == "ollama")
    )
    if provider_id is None:
        provider_id = uuid.uuid4()
        connection.execute(
            providers.insert().values(
                id=provider_id,
                code="ollama",
                name="Ollama local",
                provider_type="local",
                is_enabled=True,
            )
        )

    for model_code, display_name, supports_chat, supports_embeddings, dimension in (
        ("qwen3:1.7b", "Qwen3 1.7B", True, False, None),
        ("bge-m3", "BGE-M3", False, True, 1024),
    ):
        existing = connection.scalar(
            sa.select(models.c.id).where(
                models.c.provider_id == provider_id,
                models.c.model_code == model_code,
            )
        )
        if existing is None:
            connection.execute(
                models.insert().values(
                    id=uuid.uuid4(),
                    provider_id=provider_id,
                    model_code=model_code,
                    display_name=display_name,
                    supports_chat=supports_chat,
                    supports_embeddings=supports_embeddings,
                    supports_tools=False,
                    embedding_dimension=dimension,
                    is_enabled=True,
                )
            )


def _seed_default_document_category() -> None:
    categories = sa.table(
        "document_categories",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("description", sa.String()),
        sa.column("is_active", sa.Boolean()),
    )
    connection = op.get_bind()
    existing = connection.scalar(
        sa.select(categories.c.id).where(categories.c.code == "company-evidence")
    )
    if existing is None:
        connection.execute(
            categories.insert().values(
            id=uuid.uuid4(),
            code="company-evidence",
            name="Antecedentes de empresa",
            description="Documentos de respaldo y antecedentes de la empresa.",
            is_active=True,
            )
        )


def upgrade() -> None:
    connection = op.get_bind()
    if connection.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    _seed_ollama_models()
    _seed_default_document_category()

    op.create_table(
        "document_embeddings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("chunk_id", sa.Uuid(), nullable=False),
        sa.Column("model_id", sa.Uuid(), nullable=False),
        sa.Column(
            "embedding",
            sa.JSON().with_variant(Vector(1024), "postgresql"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["chunk_id"], ["document_chunks.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["model_id"], ["ai_models.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "chunk_id", "model_id", name="uq_document_embeddings_chunk_model"
        ),
    )
    op.create_index(
        "ix_document_embeddings_model_id",
        "document_embeddings",
        ["model_id"],
    )
    if connection.dialect.name == "postgresql":
        op.create_index(
            "ix_document_embeddings_cosine",
            "document_embeddings",
            ["embedding"],
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        )


def downgrade() -> None:
    connection = op.get_bind()
    if connection.dialect.name == "postgresql":
        op.drop_index(
            "ix_document_embeddings_cosine",
            table_name="document_embeddings",
        )
    op.drop_index(
        "ix_document_embeddings_model_id",
        table_name="document_embeddings",
    )
    op.drop_table("document_embeddings")
