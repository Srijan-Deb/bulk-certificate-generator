# ==============================================================================
# Production Dockerfile for Bulk Certificate Generator
# Multi-stage lightweight, non-root, secure container image
# ==============================================================================

FROM python:3.13-slim AS base

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production

WORKDIR /app

# Install security updates and runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies in isolated layer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user and persistent storage directory
RUN useradd -m -u 1001 appuser && \
    mkdir -p /app/storage/certificates && \
    chown -R appuser:appuser /app

# Copy application source code
COPY . /app
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# Health check probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Default entrypoint starts FastAPI with Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
