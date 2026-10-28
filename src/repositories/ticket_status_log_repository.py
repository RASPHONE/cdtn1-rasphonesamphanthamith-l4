from typing import Optional

from src.db import get_connection


class PostgresTicketStatusLogRepository:
    def create(
        self,
        *,
        ticket_id: int,
        from_status,
        to_status: str,
        changed_by: int,
        note=None,
        conn=None,
    ):
        sql = """
        INSERT INTO ticket_status_log (
            ticket_id,
            from_status,
            to_status,
            changed_by,
            note
        )
        VALUES (%s, %s, %s, %s, %s)
        RETURNING log_id
        """

        def _do(c):
            with c.cursor() as cur:
                cur.execute(
                    sql,
                    (ticket_id, from_status, to_status, changed_by, note),
                )
                row = cur.fetchone()
                return row["log_id"] if row else None

        if conn is not None:
            return _do(conn)

        with get_connection() as c:
            return _do(c)
