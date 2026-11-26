from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import AsyncSessionFactory
from app.services.document_service import process_document_job
from app.services.processing_job_service import (
    JobHandler,
    process_next_processing_job,
)

configure_logging()
logger = logging.getLogger(__name__)

JOB_HANDLERS: dict[str, JobHandler] = {}
JOB_HANDLERS["extract"] = process_document_job


async def run_worker(handlers: Mapping[str, JobHandler] | None = None) -> None:
    settings = get_settings()
    registered_handlers = JOB_HANDLERS if handlers is None else handlers
    if not registered_handlers:
        logger.warning(
            "Worker started without registered document job handlers; "
            "queued jobs will remain untouched"
        )
    while True:
        async with AsyncSessionFactory() as db:
            processed = await process_next_processing_job(
                db,
                handlers=registered_handlers,
                worker_id="document-worker",
                lease_seconds=settings.worker_lease_seconds,
            )
        if not processed:
            await asyncio.sleep(settings.worker_poll_interval_seconds)


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
