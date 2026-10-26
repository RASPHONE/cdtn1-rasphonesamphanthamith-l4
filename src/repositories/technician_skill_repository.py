from typing import Any, Dict, List, Optional

from src.db import get_connection


class PostgresTechnicianSkillRepository:
    BASE_SELECT = """
    SELECT
        ts.technician_id,
        ts.category_id,
        ts.proficiency,
        ic.category_name
    FROM technician_skill ts
    JOIN issue_category ic
      ON ic.category_id = ts.category_id
    """

    def list_by_technician(self, technician_id: int) -> List[Dict[str, Any]]:
        sql = f"""
        {self.BASE_SELECT}
        WHERE ts.technician_id = %s
        ORDER BY ic.category_name
        """

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (technician_id,))
                return cur.fetchall()

    def get_skill(
        self,
        technician_id: int,
        category_id: int,
    ) -> Optional[Dict[str, Any]]:
        sql = f"""
        {self.BASE_SELECT}
        WHERE ts.technician_id = %s
          AND ts.category_id = %s
        """

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (technician_id, category_id))
                return cur.fetchone()

    def create(
        self,
        technician_id: int,
        category_id: int,
        proficiency: int,
    ) -> None:
        sql = """
        INSERT INTO technician_skill (
            technician_id,
            category_id,
            proficiency
        )
        VALUES (%s, %s, %s)
        """

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (technician_id, category_id, proficiency))

    def update_proficiency(
        self,
        technician_id: int,
        category_id: int,
        proficiency: int,
    ) -> None:
        sql = """
        UPDATE technician_skill
        SET proficiency = %s
        WHERE technician_id = %s
          AND category_id = %s
        """

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (proficiency, technician_id, category_id))

    def delete_skill(
        self,
        technician_id: int,
        category_id: int,
    ) -> bool:
        sql = """
        DELETE FROM technician_skill
        WHERE technician_id = %s
          AND category_id = %s
        """

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (technician_id, category_id))
                return cur.rowcount > 0
