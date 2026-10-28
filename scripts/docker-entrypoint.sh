#!/bin/sh
# Container start-up for the "api" service: build/upgrade the schema, load the
# sample data (idempotent: second run adds 0 rows), then start the API.
set -e
python scripts/migrate.py
python scripts/seed.py
exec uvicorn src.main:app --host 0.0.0.0 --port 8000
