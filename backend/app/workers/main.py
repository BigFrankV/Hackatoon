"""Worker entrypoint placeholder.

Background job processing will be implemented in later tranches.
"""

import logging
import time

from app.core.logging import configure_logging

configure_logging()
logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("Worker placeholder started. No background jobs configured in Tramo 1.")
    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()
