from typing import Any, Dict, Optional

from src.db import get_connection


class PostgresUserRepository:
    def get_active_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        sql = """
        SELECT user_id, username, password_hash, role, center_id
        FROM app_user
        WHERE username = %s AND is_active
        """
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (username,))
                return cur.fetchone()
