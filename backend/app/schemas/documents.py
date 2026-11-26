import uuid
from datetime import datetime

from pydantic import BaseModel


class DocumentUploadResponse(BaseModel):
    id: uuid.UUID
    title: str
    status: str
    version_id: uuid.UUID
    version_number: int
    job_id: uuid.UUID


class DocumentListItem(BaseModel):
    id: uuid.UUID
    title: str
    status: str
    created_at: datetime
    version_number: int
    job_status: str | None
    error_code: str | None


class DocumentRetryResponse(BaseModel):
    id: uuid.UUID
    status: str
    job_status: str
