from typing import Any, Dict, Optional

from src.db import get_connection


class PostgresTicketRepository:
    """
    Minimal ticket repository needed for appointment creation.
    Later will extend this for assignment endpoints.
    """

    def get_by_id(self, ticket_id: int) -> Optional[Dict[str, Any]]:
        sql = """
        SELECT
            ticket_id,
            ticket_code,
            center_id,
            customer_name,
            customer_phone,
            serial_no,
            issue_desc,
            category_id,
            priority,
            status,
            technician_id,
            received_at,
            due_date,
            closed_at,
            is_warranty,
            is_deleted
        FROM ticket
        WHERE ticket_id = %s
        """

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (ticket_id,))
                return cur.fetchone()
