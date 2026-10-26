from contextlib import contextmanager

import psycopg

from src.config import get_settings


@contextmanager
def get_connection():
    """
    Database connection helper.
    """
    settings = get_settings()
    conn = psycopg.connect(settings.psycopg_conninfo, autocommit=False)

    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
