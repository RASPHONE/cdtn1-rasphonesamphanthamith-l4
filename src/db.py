from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

from src.config import get_settings


@contextmanager
def get_connection(row_factory=dict_row):
    """
    Database connection helper.

    Repositories use this. Each repository method opens and closes its own
    connection for simplicity in the BT2 prototype.
    """
    settings = get_settings()
    conn = psycopg.connect(
        settings.psycopg_conninfo,
        autocommit=False,
        row_factory=row_factory,
    )

    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
