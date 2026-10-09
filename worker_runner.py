"""
Standalone Worker Process Entrypoint
Allows running the background worker independently as a decoupled process
(ideal for multi-container Docker Compose or production setups).
Usage:
    python worker_runner.py
"""

import sys

from app.core.config import settings
from app.core.logging import setup_logging
from app.db.base import Base
from app.db.session import engine
from app.services.worker import worker

if __name__ == "__main__":
    logger = setup_logging()
    logger.info("Initializing database schema for standalone worker...")
    Base.metadata.create_all(bind=engine)
    settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("Starting standalone background worker...")
    try:
        worker.run_worker_loop()
    except KeyboardInterrupt:
        logger.info("Worker process interrupted by user. Exiting.")
        sys.exit(0)
