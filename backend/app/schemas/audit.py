from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import StrictSchema


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    actor_user_id: uuid.UUID | None = None
    company_id: uuid.UUID | None = None
    action: str
    entity_type: str
    entity_id: str | None = None
    occurred_at: datetime
    ip_address: str | None = None
    user_agent: str | None = None
    metadata: dict[str, Any] | None = Field(default=None, validation_alias="event_metadata")


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse]
    total: int
    page: int
    page_size: int


class AuditLogFilters(StrictSchema):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    action: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    actor_user_id: uuid.UUID | None = None
    company_id: uuid.UUID | None = None
    from_date: datetime | None = None
    to_date: datetime | None = None
