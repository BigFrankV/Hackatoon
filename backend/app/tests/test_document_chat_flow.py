from __future__ import annotations

import uuid
from pathlib import Path
from typing import ClassVar

import fitz
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.exceptions import AppError, NotFoundError
from app.core.security import hash_password
from app.integrations.contracts import AIResponse
from app.integrations.storage.local import LocalPrivateDocumentStorage
from app.models.company import Company
from app.models.enums import CompanyStatus, UserRole, UserStatus
from app.models.knowledge import (
    AIModel,
    AIProvider,
    Document,
    DocumentCategory,
    DocumentChunk,
    DocumentExtraction,
    MessageCitation,
)
from app.models.processing_job import ProcessingJob
from app.models.role import Role
from app.models.user import User
from app.services import chat_service, document_service


class FakeProvider:
    prompts: ClassVar[list[str]] = []

    def __init__(self, *_args, **_kwargs) -> None:
        pass

    async def embed(self, texts, model_code):
        return [[1.0] + [0.0] * 1023 for _ in texts]

    async def generate(self, request):
        self.prompts.append(request.system_prompt or "")
        return AIResponse(
            content="La respuesta usa el material disponible [1].",
            provider_code="ollama",
            model_code="qwen3:1.7b",
        )


async def _create_admin(db_session, label: str) -> User:
    company = Company(
        legal_name=f"{label}-{uuid.uuid4().hex[:8]} SpA",
        status=CompanyStatus.ACTIVE,
    )
    role = await db_session.scalar(select(Role).where(Role.code == UserRole.ADMIN.value))
    user = User(
        company=company,
        role=role,
        email=f"{label}-{uuid.uuid4().hex[:8]}@example.test",
        first_name="Test",
        last_name="Admin",
        password_hash=hash_password("Password123!"),
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def _seed_ai_catalog(db_session) -> None:
    provider = AIProvider(
        id=uuid.uuid4(),
        code="ollama",
        name="Ollama local",
        provider_type="local",
        is_enabled=True,
    )
    db_session.add(provider)
    await db_session.flush()
    db_session.add_all(
        [
            AIModel(
                id=uuid.uuid4(),
                provider_id=provider.id,
                model_code="qwen3:1.7b",
                display_name="Qwen3 1.7B",
                supports_chat=True,
                supports_embeddings=False,
                supports_tools=False,
                is_enabled=True,
            ),
            AIModel(
                id=uuid.uuid4(),
                provider_id=provider.id,
                model_code="bge-m3",
                display_name="BGE-M3",
                supports_chat=False,
                supports_embeddings=True,
                supports_tools=False,
                embedding_dimension=1024,
                is_enabled=True,
            ),
        ]
    )
    db_session.add(
        DocumentCategory(
            code="company-evidence",
            name="Company evidence",
            is_active=True,
        )
    )
    await db_session.commit()


def _pdf_bytes(text: str) -> bytes:
    pdf = fitz.open()
    page = pdf.new_page()
    page.insert_text((72, 72), text)
    return pdf.tobytes()


@pytest.mark.asyncio
async def test_upload_worker_and_chat_keep_retrieval_company_scoped(
    db_session, monkeypatch, tmp_path: Path
):
    await _seed_ai_catalog(db_session)
    company_one = await _create_admin(db_session, "first")
    company_two = await _create_admin(db_session, "second")
    storage = LocalPrivateDocumentStorage(tmp_path / "private")
    monkeypatch.setattr(
        document_service,
        "_client",
        lambda: (storage, FakeProvider()),
    )
    monkeypatch.setattr(
        document_service,
        "AsyncSessionFactory",
        async_sessionmaker(
            bind=db_session.bind,
            expire_on_commit=False,
            autoflush=False,
        ),
    )
    monkeypatch.setattr(chat_service, "OllamaProvider", FakeProvider)
    FakeProvider.prompts.clear()

    uploads = []
    for actor, text in (
        (company_one, "La experiencia requerida es de cinco años."),
        (company_two, "El plazo de entrega es de treinta días."),
    ):
        uploaded = await document_service.upload_company_document(
            db_session,
            actor=actor,
            filename="bases.pdf",
            content=_pdf_bytes(text),
            media_type="application/pdf",
            idempotency_key=f"upload-{actor.company_id}",
        )
        job = await db_session.get(ProcessingJob, uploaded["job_id"])
        assert job is not None
        await document_service.process_document_job(job)
        uploads.append(uploaded)

    own_docs = await document_service.list_company_documents(
        db_session, actor=company_one
    )
    foreign_download = document_service.download_company_document(
        db_session, actor=company_two, document_id=uploads[0]["id"]
    )
    assert [item["id"] for item in own_docs] == [uploads[0]["id"]]
    with pytest.raises(NotFoundError):
        await foreign_download
    with pytest.raises(AppError) as upload_error:
        await document_service.upload_company_document(
            db_session,
            actor=company_one,
            filename="invalid.pdf",
            content=b"not a PDF",
            media_type="application/pdf",
            idempotency_key="invalid-upload",
        )
    assert upload_error.value.code == "invalid_document_format"

    answer = await chat_service.send_chat_message(
        db_session,
        actor=company_one,
        content="¿Cuántos años de experiencia necesito?",
        conversation_id=None,
    )
    assert answer["grounded"] is True
    assert answer["citations"][0]["document_id"] == uploads[0]["id"]
    assert "treinta días" not in answer["citations"][0]["excerpt"]
    with pytest.raises(NotFoundError):
        await chat_service.send_chat_message(
            db_session,
            actor=company_two,
            content="Muestra la conversación de otra empresa",
            conversation_id=answer["conversation_id"],
        )

    user_message_with_no_docs = await chat_service.send_chat_message(
        db_session,
        actor=await _create_admin(db_session, "empty"),
        content="¿Qué puedo preguntar?",
        conversation_id=None,
    )
    assert user_message_with_no_docs["grounded"] is False
    assert user_message_with_no_docs["citations"] == []
    assert user_message_with_no_docs["notice"]
    assert any("no tiene documentos" in prompt.lower() for prompt in FakeProvider.prompts)

    citations = list((await db_session.scalars(select(MessageCitation))).all())
    assert len(citations) == 1
    chunks = list((await db_session.scalars(select(DocumentChunk))).all())
    assert len(chunks) == 2
    extractions = list((await db_session.scalars(select(DocumentExtraction))).all())
    assert all(extraction.status == "completed" for extraction in extractions)
    documents = list((await db_session.scalars(select(Document))).all())
    assert all(document.status == "completed" for document in documents)
