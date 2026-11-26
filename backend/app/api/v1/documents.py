from __future__ import annotations

import uuid
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.database import get_db
from app.api.dependencies.permissions import require_permissions
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.models.user import User
from app.schemas.documents import (
    DocumentListItem,
    DocumentRetryResponse,
    DocumentUploadResponse,
)
from app.services import document_service

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=list[DocumentListItem])
async def list_documents(
    current_user: User = Depends(require_permissions("documents.read")),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentListItem]:
    documents = await document_service.list_company_documents(db, actor=current_user)
    return [DocumentListItem(**document) for document in documents]


@router.post("", response_model=DocumentUploadResponse, status_code=201)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(require_permissions("documents.manage")),
    db: AsyncSession = Depends(get_db),
) -> DocumentUploadResponse:
    settings = get_settings()
    content = await file.read(settings.max_document_upload_bytes + 1)
    if len(content) > settings.max_document_upload_bytes:
        raise AppError(
            status_code=413,
            code="document_too_large",
            message="The uploaded document exceeds the configured size limit",
        )
    filename = file.filename or ""
    media_type = (
        "application/pdf"
        if filename.lower().endswith(".pdf")
        else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    idempotency_key = request.headers.get("Idempotency-Key") or f"upload:{uuid.uuid4()}"
    result = await document_service.upload_company_document(
        db,
        actor=current_user,
        filename=filename,
        content=content,
        media_type=media_type,
        idempotency_key=idempotency_key,
    )
    return DocumentUploadResponse(**result)


@router.get("/{document_id}/download")
async def download_document(
    document_id: uuid.UUID,
    current_user: User = Depends(require_permissions("documents.read")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    filename, media_type, content = await document_service.download_company_document(
        db, actor=current_user, document_id=document_id
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"
        },
    )


@router.post("/{document_id}/retry", response_model=DocumentRetryResponse)
async def retry_document(
    document_id: uuid.UUID,
    current_user: User = Depends(require_permissions("documents.manage")),
    db: AsyncSession = Depends(get_db),
) -> DocumentRetryResponse:
    result = await document_service.retry_company_document(
        db, actor=current_user, document_id=document_id
    )
    return DocumentRetryResponse(**result)
