from typing import Any, Dict, List, Optional

from src.db import get_connection


class PostgresIssueCategoryRepository:
    def get_by_id(self, category_id: int) -> Optional[Dict[str, Any]]:
        sql = """
        SELECT
            category_id,
            category_name,
            default_priority,
            is_active
        FROM issue_category
        WHERE category_id = %s
        """

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (category_id,))
                return cur.fetchone()

    def list_active(self) -> List[Dict[str, Any]]:
        sql = """
        SELECT
            category_id,
            category_name,
            default_priority
        FROM issue_category
        WHERE is_active = TRUE
        ORDER BY category_id
        """

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                return cur.fetchall()
