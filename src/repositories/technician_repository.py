from typing import Any, Dict, List, Optional

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

    def list_qualified_for_category(
        self,
        *,
        center_id: int,
        category_id: int,
    ) -> List[Dict[str, Any]]:
        """
        QT-08:
        - same center
        - active technician
        - proficiency >= 3 for the ticket category

        FR8:
        - workload = number of active warranty tickets currently assigned
        """
        sql = """
        SELECT
            t.technician_id,
            t.technician_code,
            t.ho_ten,
            t.level,
            ts.proficiency,
            (
                SELECT COUNT(*)
                FROM ticket tk
                WHERE tk.technician_id = t.technician_id
                  AND tk.is_deleted = FALSE
                  AND tk.is_warranty = TRUE
                  AND tk.status IN (
                      'DA_PHAN_CONG',
                      'DANG_XU_LY',
                      'CHO_LINH_KIEN'
                  )
            ) AS workload
        FROM technician t
        JOIN technician_skill ts
          ON ts.technician_id = t.technician_id
        WHERE t.center_id = %s
          AND t.is_active = TRUE
          AND ts.category_id = %s
          AND ts.proficiency >= 3
        ORDER BY workload ASC, t.ho_ten ASC
        """

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (center_id, category_id))
                return cur.fetchall()
