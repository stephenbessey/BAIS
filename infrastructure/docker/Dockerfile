FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r bais && useradd -r -g bais -d /app bais

WORKDIR /app

# Copy requirements
COPY requirements.txt .
COPY backend/production/requirements.txt ./backend/production/
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -r backend/production/requirements.txt \
    && pip install --no-cache-dir uvicorn gunicorn

# Copy the FULL application
COPY --chown=bais:bais backend ./backend
COPY --chown=bais:bais frontend ./frontend
COPY --chown=bais:bais scripts ./scripts

RUN mkdir -p /app/logs && chown -R bais:bais /app

USER bais

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "backend.production.main:app", "--host", "0.0.0.0", "--port", "8000"]
