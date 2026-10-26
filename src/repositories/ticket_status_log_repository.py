from typing import Optional

from src.db import get_connection


class PostgresTicketStatusLogRepository:
    def create(
        self,
        *,
        ticket_id: int,
        from_status: Optional[str],
        to_status: str,
        changed_by: int,
        note: Optional[str] = None,
    ) -> None:
        sql = """
        INSERT INTO ticket_status_log (
            ticket_id,
            from_status,
            to_status,
            changed_by,
            note
        )
        VALUES (%s, %s, %s, %s, %s)
        """

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (
                        ticket_id,
                        from_status,
                        to_status,
                        changed_by,
                        note,
                    ),
                )
