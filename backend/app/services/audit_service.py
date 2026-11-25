from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog

_SENSITIVE_KEYS = {
    "password",
    "token",
    "refresh_token",
    "access_token",
    "secret",
    "authorization",
    "cookie",
    "hashed_password",
    "password_hash",
}


def _sanitize_metadata(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            if str(key).lower() in _SENSITIVE_KEYS:
                sanitized[str(key)] = "[REDACTED]"
            else:
                sanitized[str(key)] = _sanitize_metadata(item)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_metadata(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize_metadata(item) for item in value]
    return value


async def record_audit_event(
    db: AsyncSession,
    *,
    action: str,
    entity_type: str,
    entity_id: str | uuid.UUID | None,
    actor_user_id: uuid.UUID | None,
    company_id: uuid.UUID | None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    safe_metadata = _sanitize_metadata(metadata or {})
    log = AuditLog(
        actor_user_id=actor_user_id,
        company_id=company_id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        ip_address=ip_address,
        user_agent=user_agent,
        event_metadata=safe_metadata,
    )
    db.add(log)
    await db.flush()
    return log


def _audit_to_dict(log: AuditLog) -> dict:
    return {
        "id": log.id,
        "actor_user_id": log.actor_user_id,
        "company_id": log.company_id,
        "action": log.action,
        "entity_type": log.entity_type,
        "entity_id": log.entity_id,
        "occurred_at": log.occurred_at,
        "ip_address": log.ip_address,
        "user_agent": log.user_agent,
        "metadata": _sanitize_metadata(log.event_metadata),
    }


async def list_audit_logs(
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 20,
    company_id: uuid.UUID | None = None,
    actor_user_id: uuid.UUID | None = None,
    action: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
) -> dict:
    stmt = select(AuditLog)
    count_stmt = select(func.count()).select_from(AuditLog)

    if company_id is not None:
        stmt = stmt.where(AuditLog.company_id == company_id)
        count_stmt = count_stmt.where(AuditLog.company_id == company_id)
    if actor_user_id is not None:
        stmt = stmt.where(AuditLog.actor_user_id == actor_user_id)
        count_stmt = count_stmt.where(AuditLog.actor_user_id == actor_user_id)
    if action:
        stmt = stmt.where(AuditLog.action == action)
        count_stmt = count_stmt.where(AuditLog.action == action)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
        count_stmt = count_stmt.where(AuditLog.entity_type == entity_type)
    if entity_id:
        stmt = stmt.where(AuditLog.entity_id == str(entity_id))
        count_stmt = count_stmt.where(AuditLog.entity_id == str(entity_id))
    if from_date is not None:
        stmt = stmt.where(AuditLog.occurred_at >= from_date)
        count_stmt = count_stmt.where(AuditLog.occurred_at >= from_date)
    if to_date is not None:
        stmt = stmt.where(AuditLog.occurred_at <= to_date)
        count_stmt = count_stmt.where(AuditLog.occurred_at <= to_date)

    total = int((await db.execute(count_stmt)).scalar_one())
    stmt = stmt.order_by(AuditLog.occurred_at.desc()).offset((page - 1) * page_size).limit(page_size)
    logs = list((await db.execute(stmt)).scalars().all())
    return {
        "items": [_audit_to_dict(log) for log in logs],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
