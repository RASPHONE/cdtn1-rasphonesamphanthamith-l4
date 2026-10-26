from datetime import date, time
from typing import Any, Dict, List, Optional, Tuple

from src.db import get_connection


class PostgresAppointmentRepository:
    BASE_SELECT = """
    SELECT
        appointment_id,
        ticket_id,
        technician_id,
        center_id,
        loai,
        trang_thai,
        ngay_hen,
        gio_bat_dau,
        gio_ket_thuc,
        is_deleted
    FROM appointment
    """

    def list(
        self,
        *,
        center_id: int,
        page: int,
        page_size: int,
        technician_id: Optional[int] = None,
        ticket_id: Optional[int] = None,
        ngay_hen: Optional[date] = None,
        trang_thai: Optional[str] = None,
        include_deleted: bool = False,
    ) -> Tuple[List[Dict[str, Any]], int]:
        where = ["center_id = %s"]
        params: List[Any] = [center_id]

        if not include_deleted:
            where.append("is_deleted = FALSE")

        if technician_id is not None:
            where.append("technician_id = %s")
            params.append(technician_id)

        if ticket_id is not None:
            where.append("ticket_id = %s")
            params.append(ticket_id)

        if ngay_hen is not None:
            where.append("ngay_hen = %s")
            params.append(ngay_hen)

        if trang_thai is not None:
            where.append("trang_thai = %s")
            params.append(trang_thai)

        where_sql = " AND ".join(where)

        count_sql = f"""
        SELECT COUNT(*) AS total
        FROM appointment
        WHERE {where_sql}
        """

        data_sql = f"""
        {self.BASE_SELECT}
        WHERE {where_sql}
        ORDER BY ngay_hen, gio_bat_dau
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

    def get_by_id(
        self,
        appointment_id: int,
        include_deleted: bool = False,
    ) -> Optional[Dict[str, Any]]:
        sql = f"""
        {self.BASE_SELECT}
        WHERE appointment_id = %s
        """

        if not include_deleted:
            sql += " AND is_deleted = FALSE"

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (appointment_id,))
                return cur.fetchone()

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        sql = """
        INSERT INTO appointment (
            ticket_id,
            technician_id,
            center_id,
            loai,
            trang_thai,
            ngay_hen,
            gio_bat_dau,
            gio_ket_thuc,
            is_deleted
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, FALSE)
        RETURNING *
        """

        params = (
            data["ticket_id"],
            data["technician_id"],
            data["center_id"],
            data["loai"],
            data["trang_thai"],
            data["ngay_hen"],
            data["gio_bat_dau"],
            data["gio_ket_thuc"],
        )

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchone()

    def update(
        self,
        appointment_id: int,
        fields: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        allowed_fields = {
            "loai",
            "trang_thai",
            "ngay_hen",
            "gio_bat_dau",
            "gio_ket_thuc",
        }

        set_parts: List[str] = []
        params: List[Any] = []

        for field, value in fields.items():
            if field in allowed_fields and value is not None:
                set_parts.append(f"{field} = %s")
                params.append(value)

        if not set_parts:
            return self.get_by_id(appointment_id, include_deleted=False)

        sql = f"""
        UPDATE appointment
        SET {", ".join(set_parts)}
        WHERE appointment_id = %s
          AND is_deleted = FALSE
        RETURNING *
        """

        params.append(appointment_id)

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchone()

    def soft_delete(self, appointment_id: int) -> Optional[Dict[str, Any]]:
        sql = """
        UPDATE appointment
        SET is_deleted = TRUE
        WHERE appointment_id = %s
          AND is_deleted = FALSE
        RETURNING *
        """

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (appointment_id,))
                return cur.fetchone()

    def has_conflict(
        self,
        *,
        technician_id: int,
        ngay_hen: date,
        gio_bat_dau: time,
        gio_ket_thuc: time,
        exclude_appointment_id: Optional[int] = None,
    ) -> bool:
        sql = """
        SELECT 1
        FROM appointment
        WHERE technician_id = %s
          AND ngay_hen = %s
          AND is_deleted = FALSE
          AND trang_thai IN ('DA_DAT', 'DA_XAC_NHAN')
          AND gio_bat_dau < %s
          AND gio_ket_thuc > %s
        """

        params: List[Any] = [
            technician_id,
            ngay_hen,
            gio_ket_thuc,
            gio_bat_dau,
        ]

        if exclude_appointment_id is not None:
            sql += " AND appointment_id <> %s"
            params.append(exclude_appointment_id)

        sql += " LIMIT 1"

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchone() is not None
