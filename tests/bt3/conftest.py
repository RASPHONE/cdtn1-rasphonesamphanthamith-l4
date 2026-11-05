"""Fixtures for the BT3 Test Report cases (docs/test-report.md, TC-01 ... TC-12).

Cases marked "API + PostgreSQL" run the real application (routes -> services ->
Postgres repositories) against a real PostgreSQL 16 database:

- Connection settings come from the same DB_HOST / DB_PORT / DB_USER /
  DB_PASSWORD as the application (.env or environment variables).
- The tests never touch the application database. Once per session they build
  `<DB_NAME>_test_tpl` with the real commands (`python scripts/migrate.py`,
  `python scripts/seed.py`), and before EACH test they recreate `<DB_NAME>_test`
  as a copy of it, so every case starts from the same known data
  (Test Plan section 4).
- When PostgreSQL cannot be reached, these cases are skipped with the reason;
  the cases without a database still run.

Every case prints one "observed:" line with the concrete values it saw, so
`pytest -s -v tests/bt3 -k tc05` shows the actual result for the Test Report.
"""
import os
import subprocess
import sys
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg.rows import dict_row

from src.config import Settings, get_settings

ROOT = Path(__file__).resolve().parents[2]


def observe(case: str, **values) -> None:
    """Print the actual result of a test case on one line (shown with pytest -s)."""
    text = " · ".join(f"{key}={value}" for key, value in values.items())
    print(f"\n  {case} observed: {text}")


def _server_settings() -> Settings:
    return Settings()


def _admin_connect(settings: Settings):
    return psycopg.connect(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        dbname="postgres",
        autocommit=True,
        connect_timeout=settings.db_connect_timeout,
    )


def _run_script(script: str, db_name: str) -> str:
    env = {**os.environ, "DB_NAME": db_name}
    result = subprocess.run(
        [sys.executable, f"scripts/{script}"],
        cwd=ROOT, env=env, capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"{script} failed:\n{result.stdout}\n{result.stderr}")
    return result.stdout


@pytest.fixture(scope="session")
def pg_template():
    """Build <DB_NAME>_test_tpl once: migrate + seed exactly as README step 8-9."""
    settings = _server_settings()
    base = settings.db_name
    template, working = f"{base}_test_tpl", f"{base}_test"
    try:
        admin = _admin_connect(settings)
    except psycopg.OperationalError as exc:
        pytest.skip(
            "PostgreSQL not reachable with DB_HOST/DB_PORT/DB_USER/DB_PASSWORD "
            f"({settings.db_host}:{settings.db_port}): {str(exc).splitlines()[0]}"
        )
    with admin:
        admin.execute(f'DROP DATABASE IF EXISTS "{working}" WITH (FORCE)')
        admin.execute(f'DROP DATABASE IF EXISTS "{template}" WITH (FORCE)')
        admin.execute(f'CREATE DATABASE "{template}"')
    first_run = _run_script("migrate.py", template) + _run_script("seed.py", template)
    yield {"settings": settings, "template": template, "working": working, "first_run": first_run}
    with _admin_connect(settings) as admin:
        admin.execute(f'DROP DATABASE IF EXISTS "{working}" WITH (FORCE)')
        admin.execute(f'DROP DATABASE IF EXISTS "{template}" WITH (FORCE)')


@pytest.fixture
def pg(pg_template, monkeypatch):
    """Fresh copy of the seeded template for one test; the app is pointed at it."""
    settings, working = pg_template["settings"], pg_template["working"]
    with _admin_connect(settings) as admin:
        admin.execute(f'DROP DATABASE IF EXISTS "{working}" WITH (FORCE)')
        admin.execute(f'CREATE DATABASE "{working}" TEMPLATE "{pg_template["template"]}"')
    monkeypatch.setenv("DB_NAME", working)
    get_settings.cache_clear()

    def query(sql, params=None):
        with psycopg.connect(
            host=settings.db_host, port=settings.db_port, user=settings.db_user,
            password=settings.db_password, dbname=working, row_factory=dict_row,
        ) as conn:
            return conn.execute(sql, params).fetchall()

    yield {"query": query, "db_name": working, "template": pg_template}
    get_settings.cache_clear()


@pytest.fixture
def api(pg):
    """The real application (no fakes) on the per-test database."""
    from src.main import app

    app.dependency_overrides.clear()
    with TestClient(app) as client:
        yield client


def login(client: TestClient, username: str) -> dict:
    response = client.post("/api/auth/login", json={"username": username, "password": "manager123"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
