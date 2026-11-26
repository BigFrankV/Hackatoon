from __future__ import annotations

import logging
import re
import uuid
from collections.abc import Awaitable, Callable, Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import Select, and_, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.integrations.contracts import IntegrationFailure
from app.models.processing_job import ProcessingJob
from app.models.user import User
from app.services.tenant_service import assert_company_access

logger = logging.getLogger(__name__)
JobHandler = Callable[[ProcessingJob], Awaitable[None]]
_SAFE_ERROR_CODE = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")


def _now(value: datetime | None = None) -> datetime:
    return value or datetime.now(UTC)


def _validate_error_code(error_code: str) -> str:
    if not _SAFE_ERROR_CODE.fullmatch(error_code):
        raise ValueError("error_code must be a short machine-readable code")
    return error_code


async def enqueue_processing_job(
    db: AsyncSession,
    *,
    actor: User,
    company_id: uuid.UUID,
    document_version_id: uuid.UUID,
    job_type: str,
    idempotency_key: str,
    payload: dict[str, Any] | None = None,
    max_attempts: int = 3,
    now: datetime | None = None,
) -> ProcessingJob:
    assert_company_access(actor, company_id)
    if job_type not in {"extract", "chunk", "embed"}:
        raise ValueError("Unsupported document processing job type")
    if not idempotency_key or len(idempotency_key) > 180:
        raise ValueError("idempotency_key must contain 1 to 180 characters")
    if max_attempts < 1:
        raise ValueError("max_attempts must be greater than zero")

    existing = await db.scalar(
        select(ProcessingJob).where(ProcessingJob.idempotency_key == idempotency_key)
    )
    if existing is not None:
        if (
            existing.company_id != company_id
            or existing.document_version_id != document_version_id
            or existing.job_type != job_type
            or existing.payload != (payload or {})
            or existing.max_attempts != max_attempts
        ):
            raise ConflictError(
                "Idempotency key was already used for a different job",
                code="idempotency_key_conflict",
            )
        return existing

    job = ProcessingJob(
        company_id=company_id,
        document_version_id=document_version_id,
        requested_by=actor.id,
        job_type=job_type,
        status="queued",
        attempt_count=0,
        max_attempts=max_attempts,
        idempotency_key=idempotency_key,
        payload=payload or {},
        available_at=_now(now),
    )
    try:
        async with db.begin_nested():
            db.add(job)
            await db.flush()
    except IntegrityError as exc:
        existing = await db.scalar(
            select(ProcessingJob).where(ProcessingJob.idempotency_key == idempotency_key)
        )
        if existing is None:
            raise
        if (
            existing.company_id != company_id
            or existing.document_version_id != document_version_id
            or existing.job_type != job_type
            or existing.payload != (payload or {})
            or existing.max_attempts != max_attempts
        ):
            raise ConflictError(
                "Idempotency key was already used for a different job",
                code="idempotency_key_conflict",
            ) from exc
        return existing
    return job


async def claim_next_processing_job(
    db: AsyncSession,
    *,
    job_types: tuple[str, ...],
    worker_id: str,
    lease_seconds: int = 300,
    now: datetime | None = None,
) -> ProcessingJob | None:
    if not job_types:
        return None
    if not worker_id or len(worker_id) > 120:
        raise ValueError("worker_id must contain 1 to 120 characters")
    if lease_seconds < 1:
        raise ValueError("lease_seconds must be greater than zero")
    timestamp = _now(now)
    job_type_filter = ProcessingJob.job_type.in_(job_types)
    expired_processing = and_(
        ProcessingJob.status == "processing",
        ProcessingJob.lease_expires_at <= timestamp,
    )
    await db.execute(
        update(ProcessingJob)
        .where(
            job_type_filter,
            expired_processing,
            ProcessingJob.attempt_count >= ProcessingJob.max_attempts,
        )
        .values(
            status="failed",
            completed_at=timestamp,
            lease_expires_at=None,
            locked_at=None,
            locked_by=None,
            last_error_code="worker_lease_expired",
            updated_at=timestamp,
        )
    )
    ready = and_(
        ProcessingJob.status == "queued",
        ProcessingJob.available_at <= timestamp,
    )
    claimable_expired = and_(
        expired_processing,
        ProcessingJob.attempt_count < ProcessingJob.max_attempts,
    )
    statement: Select[tuple[ProcessingJob]] = (
        select(ProcessingJob)
        .where(job_type_filter, or_(ready, claimable_expired))
        .order_by(ProcessingJob.available_at, ProcessingJob.created_at, ProcessingJob.id)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    job = await db.scalar(statement)
    if job is None:
        await db.flush()
        return None

    job.status = "processing"
    job.attempt_count += 1
    job.started_at = timestamp
    job.completed_at = None
    job.locked_at = timestamp
    job.lease_expires_at = timestamp + timedelta(seconds=lease_seconds)
    job.locked_by = worker_id
    job.updated_at = timestamp
    await db.flush()
    return job


async def complete_processing_job(
    db: AsyncSession,
    job: ProcessingJob,
    *,
    now: datetime | None = None,
) -> ProcessingJob:
    if job.status != "processing":
        raise ConflictError("Only a processing job can be completed", code="invalid_job_state")
    timestamp = _now(now)
    job.status = "completed"
    job.completed_at = timestamp
    job.lease_expires_at = None
    job.locked_at = None
    job.locked_by = None
    job.last_error_code = None
    job.updated_at = timestamp
    await db.flush()
    return job


async def fail_processing_job(
    db: AsyncSession,
    job: ProcessingJob,
    *,
    error_code: str,
    retry_delay_seconds: int = 30,
    now: datetime | None = None,
) -> ProcessingJob:
    if job.status != "processing":
        raise ConflictError("Only a processing job can fail", code="invalid_job_state")
    if retry_delay_seconds < 0:
        raise ValueError("retry_delay_seconds cannot be negative")
    timestamp = _now(now)
    job.last_error_code = _validate_error_code(error_code)
    job.status = "failed" if job.attempt_count >= job.max_attempts else "queued"
    job.available_at = timestamp + timedelta(seconds=retry_delay_seconds)
    job.completed_at = timestamp if job.status == "failed" else None
    job.lease_expires_at = None
    job.locked_at = None
    job.locked_by = None
    job.updated_at = timestamp
    await db.flush()
    return job


async def retry_processing_job(
    db: AsyncSession,
    *,
    actor: User,
    job: ProcessingJob,
    now: datetime | None = None,
) -> ProcessingJob:
    assert_company_access(actor, job.company_id)
    if job.status in {"queued", "processing"}:
        return job
    if job.status != "failed":
        raise ConflictError("Only a failed job can be retried", code="job_not_retryable")
    timestamp = _now(now)
    job.status = "queued"
    job.attempt_count = 0
    job.available_at = timestamp
    job.started_at = None
    job.completed_at = None
    job.locked_at = None
    job.lease_expires_at = None
    job.locked_by = None
    job.last_error_code = None
    job.updated_at = timestamp
    await db.flush()
    return job


async def process_next_processing_job(
    db: AsyncSession,
    *,
    handlers: Mapping[str, JobHandler],
    worker_id: str,
    lease_seconds: int = 300,
    retry_delay_seconds: int = 30,
    now: datetime | None = None,
) -> bool:
    job = await claim_next_processing_job(
        db,
        job_types=tuple(handlers),
        worker_id=worker_id,
        lease_seconds=lease_seconds,
        now=now,
    )
    if job is None:
        await db.commit()
        return False
    await db.commit()

    try:
        await handlers[job.job_type](job)
    except Exception as exc:  # noqa: BLE001 - handler failures must be persisted.
        error_code = (
            exc.code
            if isinstance(exc, IntegrationFailure)
            else "job_execution_failed"
        )
        await fail_processing_job(
            db,
            job,
            error_code=error_code,
            retry_delay_seconds=retry_delay_seconds,
            now=now,
        )
        await db.commit()
        logger.error(
            "Processing job failed: job_id=%s job_type=%s error_type=%s",
            job.id,
            job.job_type,
            type(exc).__name__,
        )
        return True

    await complete_processing_job(db, job, now=now)
    await db.commit()
    return True
