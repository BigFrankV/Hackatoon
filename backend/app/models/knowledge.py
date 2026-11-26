from __future__ import annotations

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CHAR,
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AIProvider(Base):
    __tablename__ = "ai_providers"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    code: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    provider_type: Mapped[str] = mapped_column(String(30), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class AIModel(Base):
    __tablename__ = "ai_models"
    __table_args__ = (
        CheckConstraint(
            "context_window IS NULL OR context_window > 0",
            name="ck_ai_models_context_window",
        ),
        CheckConstraint(
            "embedding_dimension IS NULL OR embedding_dimension > 0",
            name="ck_ai_models_embedding_dimension",
        ),
        UniqueConstraint("provider_id", "model_code", name="uq_ai_models_provider_model"),
        Index("ix_ai_models_provider_id", "provider_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    provider_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("ai_providers.id", ondelete="RESTRICT"), nullable=False
    )
    model_code: Mapped[str] = mapped_column(String(160), nullable=False)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    supports_chat: Mapped[bool] = mapped_column(Boolean, nullable=False)
    supports_embeddings: Mapped[bool] = mapped_column(Boolean, nullable=False)
    supports_tools: Mapped[bool] = mapped_column(Boolean, nullable=False)
    context_window: Mapped[int | None] = mapped_column(Integer)
    embedding_dimension: Mapped[int | None] = mapped_column(Integer)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class DocumentCategory(Base):
    __tablename__ = "document_categories"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    code: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(String(300))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class StorageObject(Base):
    __tablename__ = "storage_objects"
    __table_args__ = (
        CheckConstraint("byte_size > 0", name="ck_storage_objects_byte_size"),
        CheckConstraint("length(sha256) = 64", name="ck_storage_objects_sha256_length"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    storage_provider: Mapped[str] = mapped_column(String(60), nullable=False)
    object_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    sha256: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    byte_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    media_type: Mapped[str] = mapped_column(String(160), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint(
            "document_kind IN ('company', 'tender', 'generated')",
            name="ck_documents_document_kind",
        ),
        CheckConstraint(
            "status IN ('uploaded', 'queued', 'processing', 'completed', 'failed', 'ready')",
            name="ck_documents_status",
        ),
        ForeignKeyConstraint(
            ["created_by", "company_id"],
            ["users.id", "users.company_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("id", "company_id", name="uq_documents_id_company"),
        Index("ix_documents_company_status_updated", "company_id", "status", "updated_at"),
        Index("ix_documents_category_id", "category_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("document_categories.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    document_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="uploaded")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class DocumentVersion(Base):
    __tablename__ = "document_versions"
    __table_args__ = (
        UniqueConstraint(
            "document_id", "version_number", name="uq_document_versions_document_number"
        ),
        Index("ix_document_versions_storage_object_id", "storage_object_id"),
        CheckConstraint("version_number > 0", name="ck_document_versions_version_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("documents.id", ondelete="RESTRICT"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_object_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("storage_objects.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class DocumentExtraction(Base):
    __tablename__ = "document_extractions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'processing', 'completed', 'failed')",
            name="ck_document_extractions_status",
        ),
        CheckConstraint(
            "started_at IS NULL OR completed_at IS NULL OR completed_at >= started_at",
            name="ck_document_extractions_time_order",
        ),
        UniqueConstraint(
            "document_version_id",
            "extractor_code",
            "extractor_version",
            name="uq_document_extractions_version_extractor",
        ),
        Index("ix_document_extractions_document_version_id", "document_version_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("document_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    extractor_code: Mapped[str] = mapped_column(String(80), nullable=False)
    extractor_version: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    text_storage_object_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("storage_objects.id", ondelete="RESTRICT")
    )
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON)
    error_code: Mapped[str | None] = mapped_column(String(100))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        CheckConstraint("chunk_index >= 0", name="ck_document_chunks_chunk_index"),
        CheckConstraint(
            "page_number IS NULL OR page_number > 0",
            name="ck_document_chunks_page_number",
        ),
        CheckConstraint(
            "token_count IS NULL OR token_count >= 0",
            name="ck_document_chunks_token_count",
        ),
        CheckConstraint(
            "start_offset IS NULL OR start_offset >= 0",
            name="ck_document_chunks_start_offset",
        ),
        CheckConstraint(
            "end_offset IS NULL OR end_offset >= 0",
            name="ck_document_chunks_end_offset",
        ),
        CheckConstraint(
            "start_offset IS NULL OR end_offset IS NULL OR end_offset >= start_offset",
            name="ck_document_chunks_offset_order",
        ),
        UniqueConstraint("extraction_id", "chunk_index", name="uq_document_chunks_extraction_index"),
        Index("ix_document_chunks_extraction_id", "extraction_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    extraction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("document_extractions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer)
    section_label: Mapped[str | None] = mapped_column(String(240))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer)
    start_offset: Mapped[int | None] = mapped_column(Integer)
    end_offset: Mapped[int | None] = mapped_column(Integer)


class DocumentEmbedding(Base):
    __tablename__ = "document_embeddings"
    __table_args__ = (
        UniqueConstraint("chunk_id", "model_id", name="uq_document_embeddings_chunk_model"),
        Index("ix_document_embeddings_model_id", "model_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    chunk_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("document_chunks.id", ondelete="RESTRICT"), nullable=False
    )
    model_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("ai_models.id", ondelete="RESTRICT"), nullable=False
    )
    embedding: Mapped[list[float]] = mapped_column(
        Vector(1024).with_variant(JSON(), "sqlite"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        CheckConstraint(
            "(context_scope = 'company' AND tracked_tender_id IS NULL) OR "
            "(context_scope = 'tender' AND tracked_tender_id IS NOT NULL)",
            name="ck_conversations_context_scope",
        ),
        CheckConstraint("status IN ('active', 'closed')", name="ck_conversations_status"),
        ForeignKeyConstraint(
            ["created_by", "company_id"],
            ["users.id", "users.company_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("id", "company_id", name="uq_conversations_id_company"),
        Index("ix_conversations_company_updated", "company_id", "updated_at"),
        Index("ix_conversations_tracked_tender_id", "tracked_tender_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False
    )
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    tracked_tender_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    title: Mapped[str | None] = mapped_column(String(240))
    context_scope: Mapped[str] = mapped_column(String(30), nullable=False, default="company")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint("sequence_number > 0", name="ck_messages_sequence_number"),
        CheckConstraint(
            "role IN ('system', 'user', 'assistant', 'tool')",
            name="ck_messages_role",
        ),
        CheckConstraint(
            "status IN ('pending', 'completed', 'failed')",
            name="ck_messages_status",
        ),
        CheckConstraint(
            "input_tokens IS NULL OR input_tokens >= 0",
            name="ck_messages_input_tokens",
        ),
        CheckConstraint(
            "output_tokens IS NULL OR output_tokens >= 0",
            name="ck_messages_output_tokens",
        ),
        UniqueConstraint(
            "conversation_id", "sequence_number", name="uq_messages_conversation_sequence"
        ),
        Index("ix_messages_conversation_id", "conversation_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("conversations.id", ondelete="RESTRICT"), nullable=False
    )
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    model_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("ai_models.id", ondelete="RESTRICT")
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="completed")
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class MessageCitation(Base):
    __tablename__ = "message_citations"
    __table_args__ = (
        CheckConstraint("citation_order >= 0", name="ck_message_citations_order"),
        UniqueConstraint(
            "message_id", "citation_order", name="uq_message_citations_message_order"
        ),
        Index("ix_message_citations_chunk_id", "chunk_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    message_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("messages.id", ondelete="RESTRICT"), nullable=False
    )
    chunk_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("document_chunks.id", ondelete="RESTRICT"), nullable=False
    )
    citation_order: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
