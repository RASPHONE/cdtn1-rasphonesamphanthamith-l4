# Backend API (FastAPI) — built by docker-compose.yml as service "api".
# Base image pinned to an exact version (no "latest").
FROM python:3.12.7-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=Asia/Ho_Chi_Minh

WORKDIR /app

# Lock file first: this layer is reused when only the source code changes.
COPY requirements.txt .
RUN pip install -r requirements.txt

# Unprivileged user (no root inside the container).
RUN useradd --create-home --uid 10001 app

COPY src ./src
COPY scripts ./scripts
COPY db ./db
COPY data/sample ./data/sample

USER app
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=6 \
  CMD python -c "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status == 200 else 1)"

# migrate -> seed -> start API (both scripts are safe to re-run).
CMD ["sh", "scripts/docker-entrypoint.sh"]
