# ============================================================================
# BAIS Platform - Production Dockerfile
# Best practices: Multi-stage builds, Security, Optimization
# ============================================================================

# Build stage
FROM python:3.11-slim as builder

# Set build arguments
ARG BUILDPLATFORM
ARG TARGETPLATFORM

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create build directory
WORKDIR /build

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy requirements and install Python dependencies
COPY requirements.txt .
COPY backend/production/requirements.txt ./backend/production/

# Install Python dependencies
RUN pip install --user --no-cache-dir \
    -r requirements.txt \
    -r backend/production/requirements.txt

# Install additional production dependencies
RUN pip install --user --no-cache-dir \
    gunicorn[gevent] \
    psycopg2-binary \
    redis \
    prometheus-client \
    structlog

# Production stage
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/home/bais/.local/bin:$PATH \
    PORT=8000 \
    WORKERS=4 \
    TIMEOUT=120 \
    KEEPALIVE=5 \
    MAX_REQUESTS=1000 \
    MAX_REQUESTS_JITTER=100

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    libpq5 \
    libffi7 \
    libssl3 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && groupadd -r bais \
    && useradd -r -g bais -d /app -s /bin/bash bais

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/bais/.local

# Copy application code
COPY --chown=bais:bais . .

# Create necessary directories
RUN mkdir -p /app/logs /app/tmp /app/backups \
    && chown -R bais:bais /app

# Switch to non-root user
USER bais

# Create health check script
RUN echo '#!/bin/bash\ncurl -f http://localhost:${PORT}/health || exit 1' > /app/healthcheck.sh \
    && chmod +x /app/healthcheck.sh

# Expose port
EXPOSE ${PORT}

# Health check
HEALTHCHECK --interval=30s \
            --timeout=10s \
            --start-period=40s \
            --retries=3 \
            CMD /app/healthcheck.sh

# Default command
CMD ["sh", "-c", "gunicorn backend.production.main:app -w ${WORKERS} -b 0.0.0.0:${PORT} --timeout ${TIMEOUT} --keep-alive ${KEEPALIVE} --max-requests ${MAX_REQUESTS} --max-requests-jitter ${MAX_REQUESTS_JITTER} --worker-class gevent --worker-connections 1000 --access-logfile - --error-logfile - --log-level info"]
