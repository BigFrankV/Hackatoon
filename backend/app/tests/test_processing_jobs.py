from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.exceptions import ConflictError
from app.core.security import hash_password
from app.models.company import Company
from app.models.enums import CompanyStatus, UserRole, UserStatus
from app.models.processing_job import ProcessingJob
from app.models.role import Role
from app.models.user import User
from app.services.processing_job_service import (
    claim_next_processing_job,
    complete_processing_job,
    enqueue_processing_job,
    fail_processing_job,
    process_next_processing_job,
    retry_processing_job,
)


async def _create_company_admin(db_session) -> User:
    company = Company(
        legal_name=f"Jobs {uuid.uuid4().hex[:8]} SpA",
        status=CompanyStatus.ACTIVE,
    )
    role = await db_session.scalar(select(Role).where(Role.code == UserRole.ADMIN.value))
    user = User(
        company=company,
        role=role,
        email=f"jobs-{uuid.uuid4().hex[:8]}@example.test",
        first_name="Job",
        last_name="Admin",
        password_hash=hash_password("Password123!"),
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def _enqueue(db_session, actor: User, **overrides) -> ProcessingJob:
    data = {
        "company_id": actor.company_id,
        "document_version_id": uuid.uuid4(),
        "job_type": "extract",
        "idempotency_key": f"job-{uuid.uuid4()}",
        "payload": {"source": "test"},
        "max_attempts": 2,
    }
    data.update(overrides)
    return await enqueue_processing_job(db_session, actor=actor, **data)


@pytest.mark.asyncio
async def test_enqueue_is_idempotent_and_rejects_reused_key_for_other_input(db_session):
    actor = await _create_company_admin(db_session)
    key = f"same-{uuid.uuid4()}"
    first = await _enqueue(db_session, actor, idempotency_key=key)
    duplicate = await _enqueue(
        db_session,
        actor,
        idempotency_key=key,
        document_version_id=first.document_version_id,
    )

    assert duplicate.id == first.id

    with pytest.raises(ConflictError):
        await _enqueue(db_session, actor, idempotency_key=key)

    with pytest.raises(ConflictError):
        await _enqueue(
            db_session,
            actor,
            idempotency_key=key,
            document_version_id=first.document_version_id,
            payload={"source": "different"},
        )


@pytest.mark.asyncio
async def test_job_failure_retries_then_completes_without_duplicate_job(db_session):
    actor = await _create_company_admin(db_session)
    now = datetime.now(UTC)
    job = await _enqueue(db_session, actor, max_attempts=2, now=now)

    claimed = await claim_next_processing_job(
        db_session, job_types=("extract",), worker_id="worker-1", now=now
    )
    assert claimed is not None
    assert claimed.id == job.id
    assert claimed.attempt_count == 1

    await fail_processing_job(
        db_session,
        claimed,
        error_code="provider_timeout",
        retry_delay_seconds=5,
        now=now,
    )
    assert claimed.status == "queued"
    assert claimed.last_error_code == "provider_timeout"

    assert (
        await claim_next_processing_job(
            db_session,
            job_types=("extract",),
            worker_id="worker-2",
            now=now + timedelta(seconds=5),
        )
    ) is not None
    assert claimed.attempt_count == 2

    await complete_processing_job(
        db_session, claimed, now=now + timedelta(seconds=6)
    )
    assert claimed.status == "completed"
    assert claimed.completed_at == now + timedelta(seconds=6)


@pytest.mark.asyncio
async def test_failed_job_can_be_retried_idempotently_by_its_tenant(db_session):
    actor = await _create_company_admin(db_session)
    job = await _enqueue(db_session, actor, max_attempts=1)
    claimed = await claim_next_processing_job(
        db_session,
        job_types=("extract",),
        worker_id="worker-1",
        now=datetime.now(UTC),
    )
    assert claimed is not None
    await fail_processing_job(
        db_session,
        claimed,
        error_code="provider_unavailable",
        now=datetime.now(UTC),
    )
    assert claimed.status == "failed"

    retried = await retry_processing_job(db_session, actor=actor, job=claimed)
    repeated = await retry_processing_job(db_session, actor=actor, job=claimed)

    assert retried.id == job.id
    assert repeated.status == "queued"
    assert repeated.attempt_count == 0


@pytest.mark.asyncio
async def test_expired_worker_lease_is_reclaimed_and_exhausted_job_is_failed(db_session):
    actor = await _create_company_admin(db_session)
    now = datetime.now(UTC)
    job = await _enqueue(db_session, actor, max_attempts=2, now=now)
    first_claim = await claim_next_processing_job(
        db_session,
        job_types=("extract",),
        worker_id="worker-crashed",
        lease_seconds=1,
        now=now,
    )
    assert first_claim is not None

    second_claim = await claim_next_processing_job(
        db_session,
        job_types=("extract",),
        worker_id="worker-recovered",
        lease_seconds=1,
        now=now + timedelta(seconds=2),
    )
    assert second_claim is not None
    assert second_claim.id == job.id
    assert second_claim.attempt_count == 2

    terminal = await claim_next_processing_job(
        db_session,
        job_types=("extract",),
        worker_id="worker-final",
        lease_seconds=1,
        now=now + timedelta(seconds=4),
    )
    assert terminal is None
    assert job.status == "failed"
    assert job.last_error_code == "worker_lease_expired"


@pytest.mark.asyncio
async def test_worker_persists_terminal_failure_without_logging_exception_text(
    db_session, caplog
):
    actor = await _create_company_admin(db_session)
    await _enqueue(db_session, actor, max_attempts=1)

    async def failing_handler(job: ProcessingJob) -> None:
        raise RuntimeError("credential=must-not-be-logged")

    processed = await process_next_processing_job(
        db_session,
        handlers={"extract": failing_handler},
        worker_id="worker-test",
        now=datetime.now(UTC),
    )

    assert processed is True
    job = await db_session.scalar(select(ProcessingJob))
    assert job is not None
    assert job.status == "failed"
    assert job.last_error_code == "job_execution_failed"
    assert "must-not-be-logged" not in caplog.text
