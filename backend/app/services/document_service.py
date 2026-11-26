from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from pathlib import PurePosixPath

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AppError, NotFoundError, PermissionDeniedError
from app.db.session import AsyncSessionFactory
from app.integrations.ai.ollama import OllamaProvider
from app.integrations.contracts import IntegrationFailure
from app.integrations.extraction.documents import (
    chunk_document_pages,
    extract_document_pages,
)
from app.integrations.storage.local import LocalPrivateDocumentStorage
from app.models.knowledge import (
    AIModel,
    AIProvider,
    Document,
    DocumentCategory,
    DocumentChunk,
    DocumentEmbedding,
    DocumentExtraction,
    DocumentVersion,
    StorageObject,
)
from app.models.processing_job import ProcessingJob
from app.models.user import User
from app.services.audit_service import record_company_audit_event
from app.services.processing_job_service import (
    enqueue_processing_job,
    retry_processing_job,
)
from app.services.tenant_service import assert_company_access

logger = logging.getLogger(__name__)
_EXTRACTOR_CODE = "pymupdf-python-docx"
_EXTRACTOR_VERSION = "1"


def _client() -> tuple[LocalPrivateDocumentStorage, OllamaProvider]:
    settings = get_settings()
    return (
        LocalPrivateDocumentStorage(settings.private_storage_root),
        OllamaProvider(
            settings.ollama_base_url,
            chat_model=settings.ollama_chat_model,
            embedding_model=settings.ollama_embedding_model,
            embedding_dimension=settings.embedding_dimension,
            timeout_seconds=settings.ai_provider_timeout_seconds,
        ),
    )


async def upload_company_document(
    db: AsyncSession,
    *,
    actor: User,
    filename: str,
    content: bytes,
    media_type: str,
    idempotency_key: str,
) -> dict:
    if actor.company_id is None:
        raise PermissionDeniedError(
            "Company context required", code="company_context_required"
        )
    assert_company_access(actor, actor.company_id)
    safe_filename = PurePosixPath(filename.replace("\\", "/")).name
    if not safe_filename or len(safe_filename) > 255:
        raise AppError(
            status_code=400,
            code="invalid_filename",
            message="filename must contain 1 to 255 characters",
        )
    if not content:
        raise AppError(
            status_code=400,
            code="empty_document",
            message="The uploaded document cannot be empty",
        )

    extension = safe_filename.rpartition(".")[2].lower()
    if extension not in {"pdf", "docx"}:
        raise AppError(
            status_code=400,
            code="unsupported_document",
            message="Only PDF and DOCX documents are supported",
        )
    if (extension == "pdf" and not content.startswith(b"%PDF-")) or (
        extension == "docx" and not content.startswith(b"PK")
    ):
        raise AppError(
            status_code=400,
            code="invalid_document_format",
            message="The uploaded file does not match its filename extension",
        )

    settings = get_settings()
    if len(content) > settings.max_document_upload_bytes:
        raise AppError(
            status_code=413,
            code="document_too_large",
            message="The uploaded document exceeds the configured size limit",
        )

    category = await db.scalar(
        select(DocumentCategory).where(
            DocumentCategory.code == "company-evidence",
            DocumentCategory.is_active.is_(True),
        )
    )
    if category is None:
        raise IntegrationFailure(
            integration="document_upload",
            code="document_category_not_configured",
            retryable=False,
        )

    document_id = uuid.uuid4()
    version_id = uuid.uuid4()
    object_key = (
        f"companies/{actor.company_id}/documents/{document_id}/"
        f"{version_id}.{extension}"
    )
    storage, _ = _client()
    stored = await storage.put(object_key, content, media_type)
    try:
        document = Document(
            id=document_id,
            company_id=actor.company_id,
            category_id=category.id,
            created_by=actor.id,
            title=safe_filename,
            document_kind="company",
            status="queued",
        )
        storage_object = StorageObject(
            storage_provider="local",
            object_key=stored.object_key,
            sha256=stored.sha256,
            byte_size=stored.byte_size,
            media_type=stored.media_type,
        )
        db.add_all([document, storage_object])
        await db.flush()
        version = DocumentVersion(
            id=version_id,
            document_id=document.id,
            version_number=1,
            storage_object_id=storage_object.id,
            original_filename=safe_filename,
            created_by=actor.id,
        )
        db.add(version)
        await db.flush()
        job = await enqueue_processing_job(
            db,
            actor=actor,
            company_id=actor.company_id,
            document_version_id=version.id,
            job_type="extract",
            idempotency_key=idempotency_key,
            payload={"document_id": str(document.id)},
        )
        await record_company_audit_event(
            db,
            actor=actor,
            action="document.uploaded",
            entity_type="document",
            entity_id=document.id,
            metadata={"filename": version.original_filename, "byte_size": stored.byte_size},
        )
        await db.commit()
    except Exception:
        await db.rollback()
        await storage.delete(object_key)
        raise
    return {
        "id": document.id,
        "title": document.title,
        "status": document.status,
        "version_id": version.id,
        "version_number": version.version_number,
        "job_id": job.id,
    }


async def list_company_documents(
    db: AsyncSession, *, actor: User
) -> list[dict]:
    if actor.company_id is None:
        raise PermissionDeniedError(
            "Company context required", code="company_context_required"
        )
    assert_company_access(actor, actor.company_id)
    statement = (
        select(Document, DocumentVersion, ProcessingJob)
        .join(DocumentVersion, DocumentVersion.document_id == Document.id)
        .join(
            ProcessingJob,
            ProcessingJob.document_version_id == DocumentVersion.id,
            isouter=True,
        )
        .where(
            Document.company_id == actor.company_id,
            Document.deleted_at.is_(None),
        )
        .order_by(Document.created_at.desc(), DocumentVersion.version_number.desc())
    )
    rows = (await db.execute(statement)).all()
    latest: dict[uuid.UUID, dict] = {}
    for document, version, job in rows:
        if document.id in latest:
            continue
        latest[document.id] = {
            "id": document.id,
            "title": document.title,
            "status": document.status,
            "created_at": document.created_at,
            "version_number": version.version_number,
            "job_status": job.status if job else None,
            "error_code": job.last_error_code if job else None,
        }
    return list(latest.values())


async def retry_company_document(
    db: AsyncSession, *, actor: User, document_id: uuid.UUID
) -> dict:
    if actor.company_id is None:
        raise NotFoundError()
    assert_company_access(actor, actor.company_id)
    row = await db.execute(
        select(Document, DocumentVersion, ProcessingJob)
        .join(DocumentVersion, DocumentVersion.document_id == Document.id)
        .join(
            ProcessingJob,
            ProcessingJob.document_version_id == DocumentVersion.id,
        )
        .where(
            Document.id == document_id,
            Document.company_id == actor.company_id,
            Document.deleted_at.is_(None),
        )
        .order_by(DocumentVersion.version_number.desc())
        .limit(1)
    )
    result = row.first()
    if result is None:
        raise NotFoundError("Document not found")
    document, _, job = result
    retried = await retry_processing_job(db, actor=actor, job=job)
    if retried.status == "queued":
        document.status = "queued"
        document.updated_at = datetime.now(UTC)
    await db.commit()
    return {"id": document.id, "status": document.status, "job_status": retried.status}


async def download_company_document(
    db: AsyncSession, *, actor: User, document_id: uuid.UUID
) -> tuple[str, str, bytes]:
    if actor.company_id is None:
        raise PermissionDeniedError(
            "Company context required", code="company_context_required"
        )
    assert_company_access(actor, actor.company_id)
    result = await db.execute(
        select(DocumentVersion, StorageObject)
        .join(Document, Document.id == DocumentVersion.document_id)
        .join(StorageObject, StorageObject.id == DocumentVersion.storage_object_id)
        .where(
            Document.id == document_id,
            Document.company_id == actor.company_id,
            Document.deleted_at.is_(None),
        )
        .order_by(DocumentVersion.version_number.desc())
        .limit(1)
    )
    row = result.first()
    if row is None:
        raise NotFoundError("Document not found")
    version, stored_object = row
    storage, _ = _client()
    content = await storage.get(stored_object.object_key)
    return version.original_filename, stored_object.media_type, content


async def process_document_job(job: ProcessingJob) -> None:
    storage, provider = _client()
    text_object_key: str | None = None
    async with AsyncSessionFactory() as db:
        source = await db.execute(
            select(Document, DocumentVersion, StorageObject)
            .join(DocumentVersion, DocumentVersion.document_id == Document.id)
            .join(StorageObject, StorageObject.id == DocumentVersion.storage_object_id)
            .where(
                DocumentVersion.id == job.document_version_id,
                Document.company_id == job.company_id,
                Document.deleted_at.is_(None),
            )
        )
        row = source.first()
        if row is None:
            raise IntegrationFailure(
                integration="document_processing",
                code="document_not_found",
                retryable=False,
            )
        document, version, source_object = row
        document_id = document.id
        version_id = version.id
        extraction = await db.scalar(
            select(DocumentExtraction).where(
                DocumentExtraction.document_version_id == version.id,
                DocumentExtraction.extractor_code == _EXTRACTOR_CODE,
                DocumentExtraction.extractor_version == _EXTRACTOR_VERSION,
            )
        )
        if extraction is not None and extraction.status == "completed":
            document.status = "completed"
            await db.commit()
            return

        now = datetime.now(UTC)
        document.status = "processing"
        if extraction is None:
            extraction = DocumentExtraction(
                document_version_id=version.id,
                extractor_code=_EXTRACTOR_CODE,
                extractor_version=_EXTRACTOR_VERSION,
                status="processing",
                started_at=now,
            )
            db.add(extraction)
            await db.flush()
        else:
            extraction.status = "processing"
            extraction.error_code = None
            extraction.started_at = now
            extraction.completed_at = None
        await db.commit()

        try:
            content = await storage.get(source_object.object_key)
            pages = extract_document_pages(content, version.original_filename)
            chunks = chunk_document_pages(pages)
            if not chunks:
                raise IntegrationFailure(
                    integration="document_extraction",
                    code="document_has_no_extractable_text",
                    retryable=False,
                )
            model = await db.scalar(
                select(AIModel)
                .join(AIProvider, AIProvider.id == AIModel.provider_id)
                .where(
                    AIProvider.code == "ollama",
                    AIModel.model_code == get_settings().ollama_embedding_model,
                    AIModel.embedding_dimension == get_settings().embedding_dimension,
                    AIModel.supports_embeddings.is_(True),
                    AIModel.is_enabled.is_(True),
                )
            )
            if model is None:
                raise IntegrationFailure(
                    integration="ollama",
                    code="embedding_model_not_configured",
                    retryable=False,
                )

            old_chunk_ids = select(DocumentChunk.id).where(
                DocumentChunk.extraction_id == extraction.id
            )
            await db.execute(
                delete(DocumentEmbedding).where(DocumentEmbedding.chunk_id.in_(old_chunk_ids))
            )
            await db.execute(
                delete(DocumentChunk).where(DocumentChunk.extraction_id == extraction.id)
            )
            extracted_text = "\n\n".join(page.text for page in pages if page.text)
            text_object_key = (
                f"companies/{document.company_id}/extractions/{version.id}/"
                f"{uuid.uuid4()}.txt"
            )
            text_stored = await storage.put(
                text_object_key, extracted_text.encode("utf-8"), "text/plain; charset=utf-8"
            )
            text_object = StorageObject(
                storage_provider="local",
                object_key=text_stored.object_key,
                sha256=text_stored.sha256,
                byte_size=text_stored.byte_size,
                media_type=text_stored.media_type,
            )
            db.add(text_object)
            await db.flush()
            extraction.text_storage_object_id = text_object.id
            extraction.metadata_json = {
                "page_count": len(pages),
                "chunk_count": len(chunks),
                "embedding_model": model.model_code,
            }
            extraction.status = "completed"
            extraction.error_code = None
            extraction.completed_at = datetime.now(UTC)

            chunk_rows = [
                DocumentChunk(
                    extraction_id=extraction.id,
                    chunk_index=chunk.chunk_index,
                    page_number=chunk.page_number,
                    section_label=chunk.section_label,
                    content=chunk.content,
                    content_hash=chunk.content_hash,
                    token_count=chunk.token_count,
                    start_offset=chunk.start_offset,
                    end_offset=chunk.end_offset,
                )
                for chunk in chunks
            ]
            db.add_all(chunk_rows)
            await db.flush()
            for offset in range(0, len(chunk_rows), 16):
                batch = chunk_rows[offset : offset + 16]
                vectors = await provider.embed(
                    [chunk.content for chunk in batch], model.model_code
                )
                db.add_all(
                    [
                        DocumentEmbedding(
                            chunk_id=chunk.id,
                            model_id=model.id,
                            embedding=list(vector),
                        )
                        for chunk, vector in zip(batch, vectors, strict=True)
                    ]
                )
            document.status = "completed"
            document.updated_at = datetime.now(UTC)
            await db.commit()
        except Exception as exc:
            await db.rollback()
            if text_object_key is not None:
                await storage.delete(text_object_key)
            async with AsyncSessionFactory() as error_db:
                failed_document = await error_db.scalar(
                    select(Document).where(
                        Document.id == document_id,
                        Document.company_id == job.company_id,
                    )
                )
                failed_extraction = await error_db.scalar(
                    select(DocumentExtraction).where(
                        DocumentExtraction.document_version_id == version_id,
                        DocumentExtraction.extractor_code == _EXTRACTOR_CODE,
                        DocumentExtraction.extractor_version == _EXTRACTOR_VERSION,
                    )
                )
                terminal = job.attempt_count >= job.max_attempts
                if failed_document is not None:
                    failed_document.status = "failed" if terminal else "queued"
                    failed_document.updated_at = datetime.now(UTC)
                if failed_extraction is not None:
                    failed_extraction.status = "failed"
                    failed_extraction.error_code = (
                        exc.code if isinstance(exc, IntegrationFailure) else "processing_failed"
                    )
                    failed_extraction.completed_at = datetime.now(UTC)
                await error_db.commit()
            raise

