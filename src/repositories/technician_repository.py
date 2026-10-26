from typing import Any, Dict, Optional

from src.db import get_connection


class PostgresTechnicianRepository:
    def get_by_id(self, technician_id: int) -> Optional[Dict[str, Any]]:
        sql = """
        SELECT
            technician_id,
            technician_code,
            ho_ten,
            center_id,
            level,
            is_active
        FROM technician
        WHERE technician_id = %s
        """

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (technician_id,))
                return cur.fetchone()
