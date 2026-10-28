from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

from src.config import get_settings


class DatabaseUnavailableError(Exception):
    """Raised when PostgreSQL cannot be reached (server down, wrong host/port)."""


@contextmanager
def get_connection(row_factory=dict_row):
    """
    Open one connection = one transaction.

    Commits when the block finishes, rolls back on any exception.
    Connection-level failures are translated into DatabaseUnavailableError so
    the API can answer 503 instead of leaking a driver error.
    """
    settings = get_settings()
    try:
        conn = psycopg.connect(
            settings.psycopg_conninfo,
            autocommit=False,
            row_factory=row_factory,
            connect_timeout=settings.db_connect_timeout,
        )
    except psycopg.OperationalError as exc:
        raise DatabaseUnavailableError(str(exc).splitlines()[0]) from exc

    try:
        yield conn
        conn.commit()
    except psycopg.OperationalError as exc:
        conn.rollback()
        raise DatabaseUnavailableError(str(exc).splitlines()[0]) from exc
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def ping() -> bool:
    """True when the database answers `SELECT 1` (used by /health)."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        return True
    except DatabaseUnavailableError:
        return False
