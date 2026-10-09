"""
Structured Logging Configuration
Configures uniform, readable application logging across FastAPI and worker processes.
"""

import logging
import sys

from app.core.config import settings


def setup_logging():
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        level=log_level, format=log_format, datefmt=date_format, handlers=[logging.StreamHandler(sys.stdout)]
    )

    # Silence overly verbose third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    logger = logging.getLogger("bulk_certificate_generator")
    logger.info("Structured logging initialized at %s level", logging.getLevelName(log_level))
    return logger
