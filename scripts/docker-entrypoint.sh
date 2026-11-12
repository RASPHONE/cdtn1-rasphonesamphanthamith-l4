#!/bin/sh
# Container start-up for the "api" service: build/upgrade the schema, load the
# sample data (idempotent: second run adds 0 rows), then start the API.
set -e
python scripts/migrate.py
python scripts/seed.py
# Port: PORT when the platform sets one (Render), else 8000 (docker compose).
exec uvicorn src.main:app --host 0.0.0.0 --port "${PORT:-8000}"
