from __future__ import annotations

import math
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AppError, NotFoundError, PermissionDeniedError
from app.integrations.ai.ollama import OllamaProvider
from app.integrations.contracts import AIRequest, IntegrationFailure
from app.models.knowledge import (
    AIModel,
    AIProvider,
    Conversation,
    Document,
    DocumentChunk,
    DocumentEmbedding,
    DocumentExtraction,
    DocumentVersion,
    Message,
    MessageCitation,
)
from app.models.user import User
from app.services.audit_service import record_company_audit_event
from app.services.tenant_service import assert_company_access


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


async def _retrieve_chunks(
    db: AsyncSession,
    *,
    company_id: uuid.UUID,
    model_id: uuid.UUID,
    query_vector: list[float],
) -> list[tuple[DocumentChunk, Document, float]]:
    statement = (
        select(DocumentChunk, Document, DocumentEmbedding.embedding)
        .join(
            DocumentEmbedding,
            DocumentEmbedding.chunk_id == DocumentChunk.id,
        )
        .join(
            DocumentExtraction,
            DocumentExtraction.id == DocumentChunk.extraction_id,
        )
        .join(
            DocumentVersion,
            DocumentVersion.id == DocumentExtraction.document_version_id,
        )
        .join(Document, Document.id == DocumentVersion.document_id)
        .where(
            Document.company_id == company_id,
            Document.deleted_at.is_(None),
            Document.status == "completed",
            DocumentEmbedding.model_id == model_id,
        )
    )
    if db.get_bind().dialect.name == "postgresql":
        distance = DocumentEmbedding.embedding.cosine_distance(query_vector)
        rows = (
            await db.execute(
                select(DocumentChunk, Document, distance.label("distance"))
                .select_from(DocumentChunk)
                .join(
                    DocumentEmbedding,
                    DocumentEmbedding.chunk_id == DocumentChunk.id,
                )
                .join(
                    DocumentExtraction,
                    DocumentExtraction.id == DocumentChunk.extraction_id,
                )
                .join(
                    DocumentVersion,
                    DocumentVersion.id == DocumentExtraction.document_version_id,
                )
                .join(Document, Document.id == DocumentVersion.document_id)
                .where(
                    Document.company_id == company_id,
                    Document.deleted_at.is_(None),
                    Document.status == "completed",
                    DocumentEmbedding.model_id == model_id,
                )
                .order_by(distance)
                .limit(get_settings().rag_top_k)
            )
        ).all()
        return [
            (chunk, document, 1.0 - float(distance))
            for chunk, document, distance in rows
            if 1.0 - float(distance) >= get_settings().rag_min_similarity
        ]

    rows = (await db.execute(statement)).all()
    scored = [
        (chunk, document, _cosine_similarity(query_vector, embedding))
        for chunk, document, embedding in rows
    ]
    scored = [
        row for row in scored if row[2] >= get_settings().rag_min_similarity
    ]
    return sorted(scored, key=lambda row: row[2], reverse=True)[
        : get_settings().rag_top_k
    ]


async def send_chat_message(
    db: AsyncSession,
    *,
    actor: User,
    content: str,
    conversation_id: uuid.UUID | None,
) -> dict:
    if actor.company_id is None:
        raise PermissionDeniedError(
            "Company context required", code="company_context_required"
        )
    assert_company_access(actor, actor.company_id)
    if not content.strip():
        raise AppError(
            status_code=400,
            code="empty_message",
            message="Message content cannot be empty",
        )

    settings = get_settings()
    if conversation_id is None:
        conversation = Conversation(
            company_id=actor.company_id,
            created_by=actor.id,
            title=content.strip()[:240],
            context_scope="company",
            status="active",
        )
        db.add(conversation)
        await db.flush()
    else:
        conversation = await db.scalar(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.company_id == actor.company_id,
                Conversation.deleted_at.is_(None),
                Conversation.status == "active",
            ).with_for_update()
        )
        if conversation is None:
            raise NotFoundError("Conversation not found")

    history = list(
        (
            await db.scalars(
                select(Message)
                .where(
                    Message.conversation_id == conversation.id,
                    Message.status == "completed",
                )
                .order_by(Message.sequence_number.desc())
                .limit(10)
            )
        ).all()
    )
    history.reverse()
    latest_sequence = await db.scalar(
        select(func.max(Message.sequence_number)).where(
            Message.conversation_id == conversation.id
        )
    )
    sequence = (latest_sequence or 0) + 1
    user_message = Message(
        conversation_id=conversation.id,
        sequence_number=sequence,
        role="user",
        content=content.strip(),
        status="completed",
    )
    db.add(user_message)
    await db.flush()

    provider = OllamaProvider(
        settings.ollama_base_url,
        chat_model=settings.ollama_chat_model,
        embedding_model=settings.ollama_embedding_model,
        embedding_dimension=settings.embedding_dimension,
        timeout_seconds=settings.ai_provider_timeout_seconds,
    )
    chat_model = await db.scalar(
        select(AIModel)
        .join(AIProvider, AIProvider.id == AIModel.provider_id)
        .where(
            AIProvider.code == "ollama",
            AIModel.model_code == settings.ollama_chat_model,
            AIModel.supports_chat.is_(True),
            AIModel.is_enabled.is_(True),
        )
    )
    embedding_model = await db.scalar(
        select(AIModel)
        .join(AIProvider, AIProvider.id == AIModel.provider_id)
        .where(
            AIProvider.code == "ollama",
            AIModel.model_code == settings.ollama_embedding_model,
            AIModel.supports_embeddings.is_(True),
            AIModel.is_enabled.is_(True),
        )
    )
    if chat_model is None or embedding_model is None:
        raise AppError(
            status_code=503,
            code="ai_models_not_configured",
            message="Configured local AI models are not available in the model catalog",
        )
    if embedding_model.embedding_dimension != settings.embedding_dimension:
        raise AppError(
            status_code=503,
            code="embedding_dimension_mismatch",
            message="The configured embedding model dimension does not match the vector schema",
        )

    try:
        vectors = await provider.embed([content.strip()], embedding_model.model_code)
        matches = await _retrieve_chunks(
            db,
            company_id=actor.company_id,
            model_id=embedding_model.id,
            query_vector=list(vectors[0]),
        )
        context = "\n\n".join(
            f"[{index}] {document.title} - "
            f"{chunk.section_label or 'Ubicacion no disponible'}: {chunk.content}"
            for index, (chunk, document, _) in enumerate(matches, start=1)
        )
        history_text = "\n".join(
            f"{message.role}: {message.content}" for message in history
        )
        prompt = (
            f"Historial reciente:\n{history_text or '(sin mensajes previos)'}\n\n"
            f"Pregunta actual:\n{content.strip()}\n\n"
            f"Contexto documental:\n{context or '(no hay fragmentos relevantes)'}"
        )
        has_sources = bool(matches)
        system_prompt = (
            "Responde en español. Usa exclusivamente el contexto documental para "
            "afirmaciones sobre documentos y licitaciones. Cita cada afirmación "
            "documental con el número [1], [2], etc. Si el contexto no responde, "
            "indica claramente que no hay evidencia suficiente y no inventes citas."
            if has_sources
            else "Responde en español. Esta conversación todavía no tiene documentos "
            "relevantes disponibles. Puedes responder preguntas generales, pero "
            "aclara que la respuesta no está respaldada por documentos de la empresa; "
            "no inventes citas ni afirmes haber revisado licitaciones."
        )
        response = await provider.generate(
            AIRequest(prompt=prompt, system_prompt=system_prompt)
        )
    except IntegrationFailure as exc:
        db.add(
            Message(
                conversation_id=conversation.id,
                sequence_number=sequence + 1,
                role="assistant",
                content="No fue posible obtener una respuesta del proveedor local de IA.",
                model_id=chat_model.id,
                status="failed",
            )
        )
        await db.commit()
        raise AppError(
            status_code=503,
            code=exc.code,
            message="The local AI provider could not complete the request",
        ) from exc

    assistant_message = Message(
        conversation_id=conversation.id,
        sequence_number=sequence + 1,
        role="assistant",
        content=response.content,
        model_id=chat_model.id,
        status="completed",
    )
    db.add(assistant_message)
    await db.flush()
    for index, (chunk, _, _) in enumerate(matches):
        db.add(
            MessageCitation(
                message_id=assistant_message.id,
                chunk_id=chunk.id,
                citation_order=index,
            )
        )
    await record_company_audit_event(
        db,
        actor=actor,
        action="chat.message.sent",
        entity_type="conversation",
        entity_id=conversation.id,
        metadata={"citation_count": len(matches), "model": chat_model.model_code},
    )
    conversation.updated_at = datetime.now(UTC)
    await db.commit()

    return {
        "conversation_id": conversation.id,
        "user_message_id": user_message.id,
        "assistant_message_id": assistant_message.id,
        "answer": response.content,
        "model": response.model_code,
        "grounded": bool(matches),
        "notice": None
        if matches
        else "Esta respuesta no está respaldada por documentos de la empresa.",
        "citations": [
            {
                "order": index + 1,
                "document_id": document.id,
                "document_title": document.title,
                "location": chunk.section_label,
                "page_number": chunk.page_number,
                "excerpt": chunk.content,
                "similarity": score,
            }
            for index, (chunk, document, score) in enumerate(matches)
        ],
    }
