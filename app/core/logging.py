"""
Structured Logging Configuration with Correlation Context
Configures uniform, readable application logging across FastAPI and worker processes
with distributed request and worker job correlation context.
"""

import contextvars
import logging
import sys

from app.core.config import settings

# Thread-local / async-safe correlation contexts
request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")
job_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("job_id", default="-")


class ObservabilityLogFilter(logging.Filter):
    """Enriches each log record with correlation identifier (Request ID or Job ID)."""

    def filter(self, record: logging.LogRecord) -> bool:
        req_id = request_id_ctx.get()
        j_id = job_id_ctx.get()

        if req_id != "-":
            record.correlation_id = f"req:{req_id}"
        elif j_id != "-":
            record.correlation_id = f"job:{j_id[:8]}"
        else:
            record.correlation_id = "-"

        return True


def setup_logging():
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO
    log_format = "%(asctime)s | %(levelname)-8s | [%(correlation_id)s] | %(name)s:%(lineno)d | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(fmt=log_format, datefmt=date_format))
    handler.addFilter(ObservabilityLogFilter())

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers = [handler]

    # Silence overly verbose third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    logger = logging.getLogger("bulk_certificate_generator")
    logger.info("Structured logging initialized at %s level with correlation filter", logging.getLevelName(log_level))
    return logger
