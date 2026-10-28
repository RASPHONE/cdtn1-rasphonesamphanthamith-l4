from typing import Any, Dict, List, Optional, Tuple

from src.db import get_connection


class PostgresTicketRepository:
    BASE_SELECT = """
    SELECT
        t.ticket_id,
        t.ticket_code,
        t.center_id,
        t.customer_name,
        t.customer_phone,
        t.serial_no,
        t.issue_desc,
        t.category_id,
        ic.category_name,
        t.priority,
        t.status,
        t.technician_id,
        t.received_at,
        t.due_date,
        t.closed_at,
        t.is_warranty,
        t.is_deleted
    FROM ticket t
    JOIN issue_category ic
      ON ic.category_id = t.category_id
    """

    def get_by_id(self, ticket_id: int, conn=None):
        sql = f"""
        {self.BASE_SELECT}
        WHERE t.ticket_id = %s
        """

        def _query(c):
            with c.cursor() as cur:
                cur.execute(sql, (ticket_id,))
                return cur.fetchone()

        if conn is not None:
            return _query(conn)

        with get_connection() as c:
            return _query(c)

    def list_unassigned(
        self,
        *,
        center_id: int,
        category_id: Optional[int] = None,
        priority: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int]:
        where = [
            "t.center_id = %s",
            "t.is_deleted = FALSE",
            "t.is_warranty = TRUE",
            "t.status = 'MOI'",
            "t.technician_id IS NULL",
        ]

        params: List[Any] = [center_id]

        if category_id is not None:
            where.append("t.category_id = %s")
            params.append(category_id)

        if priority is not None:
            where.append("t.priority = %s")
            params.append(priority)

        where_sql = " AND ".join(where)

        count_sql = f"""
        SELECT COUNT(*) AS total
        FROM ticket t
        WHERE {where_sql}
        """

        data_sql = f"""
        {self.BASE_SELECT}
        WHERE {where_sql}
        ORDER BY t.due_date ASC
        LIMIT %s OFFSET %s
        """

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(count_sql, params)
                total = cur.fetchone()["total"]

                cur.execute(
                    data_sql,
                    params + [page_size, (page - 1) * page_size],
                )
                items = cur.fetchall()

        return items, total

    def assign_technician(
        self,
        ticket_id: int,
        technician_id: int,
        new_status: str,
        conn=None,
    ):
        update_sql = """
        UPDATE ticket
        SET technician_id = %s,
            status = %s
        WHERE ticket_id = %s
          AND is_deleted = FALSE
        """

        def _do(c):
            with c.cursor() as cur:
                cur.execute(update_sql, (technician_id, new_status, ticket_id))
            return self.get_by_id(ticket_id, conn=c)

        if conn is not None:
            return _do(conn)

        with get_connection() as c:
            return _do(c)

    def update_technician(
        self,
        ticket_id: int,
        technician_id: int,
        conn=None,
    ):
        update_sql = """
        UPDATE ticket
        SET technician_id = %s
        WHERE ticket_id = %s
          AND is_deleted = FALSE
        """

        def _do(c):
            with c.cursor() as cur:
                cur.execute(update_sql, (technician_id, ticket_id))
            return self.get_by_id(ticket_id, conn=c)

        if conn is not None:
            return _do(conn)

        with get_connection() as c:
            return _do(c)
