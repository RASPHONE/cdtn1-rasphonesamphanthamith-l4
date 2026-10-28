from datetime import date, time
from typing import Any, Dict, List, Optional, Tuple

from src.db import get_connection

ACTIVE_STATUSES = ("DA_DAT", "DA_XAC_NHAN")


class PostgresAppointmentRepository:
    BASE_SELECT = """
    SELECT
        a.appointment_id,
        a.ticket_id,
        t.ticket_code,
        a.technician_id,
        tech.ho_ten AS technician_ho_ten,
        a.center_id,
        a.loai,
        a.trang_thai,
        a.ngay_hen,
        a.gio_bat_dau,
        a.gio_ket_thuc,
        a.is_deleted
    FROM appointment a
    JOIN ticket t
      ON t.ticket_id = a.ticket_id
    JOIN technician tech
      ON tech.technician_id = a.technician_id
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
        where = ["a.center_id = %s"]
        params: List[Any] = [center_id]

        if not include_deleted:
            where.append("a.is_deleted = FALSE")

        if technician_id is not None:
            where.append("a.technician_id = %s")
            params.append(technician_id)

        if ticket_id is not None:
            where.append("a.ticket_id = %s")
            params.append(ticket_id)

        if ngay_hen is not None:
            where.append("a.ngay_hen = %s")
            params.append(ngay_hen)

        if trang_thai is not None:
            where.append("a.trang_thai = %s")
            params.append(trang_thai)

        where_sql = " AND ".join(where)

        count_sql = f"""
        SELECT COUNT(*) AS total
        FROM appointment a
        WHERE {where_sql}
        """

        # Newest dates first so upcoming and recent appointments are on page 1.
        data_sql = f"""
        {self.BASE_SELECT}
        WHERE {where_sql}
        ORDER BY a.ngay_hen DESC, a.gio_bat_dau DESC
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
        with get_connection() as conn:
            return self._get(conn, appointment_id, include_deleted)

    def _get(self, conn, appointment_id: int, include_deleted: bool) -> Optional[Dict[str, Any]]:
        sql = f"""
        {self.BASE_SELECT}
        WHERE a.appointment_id = %s
        """

        if not include_deleted:
            sql += " AND a.is_deleted = FALSE"

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
        RETURNING appointment_id
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
                appointment_id = cur.fetchone()["appointment_id"]
            return self._get(conn, appointment_id, include_deleted=False)

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
        """

        params.append(appointment_id)

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                if cur.rowcount == 0:
                    return None
            return self._get(conn, appointment_id, include_deleted=False)

    def soft_delete(self, appointment_id: int) -> Optional[Dict[str, Any]]:
        sql = """
        UPDATE appointment
        SET is_deleted = TRUE
        WHERE appointment_id = %s
          AND is_deleted = FALSE
        RETURNING appointment_id, is_deleted
        """

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (appointment_id,))
                return cur.fetchone()

    def find_conflicts(
        self,
        *,
        technician_id: int,
        ngay_hen: date,
        gio_bat_dau: time,
        gio_ket_thuc: time,
        exclude_appointment_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Active, non-deleted appointments of the technician on the same day
        whose time interval overlaps [gio_bat_dau, gio_ket_thuc)."""
        sql = """
        SELECT
            appointment_id,
            ticket_id,
            ngay_hen,
            gio_bat_dau,
            gio_ket_thuc,
            trang_thai
        FROM appointment
        WHERE technician_id = %s
          AND ngay_hen = %s
          AND is_deleted = FALSE
          AND trang_thai = ANY(%s)
          AND gio_bat_dau < %s
          AND gio_ket_thuc > %s
        """

        params: List[Any] = [
            technician_id,
            ngay_hen,
            list(ACTIVE_STATUSES),
            gio_ket_thuc,
            gio_bat_dau,
        ]

        if exclude_appointment_id is not None:
            sql += " AND appointment_id <> %s"
            params.append(exclude_appointment_id)

        sql += " ORDER BY gio_bat_dau"

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchall()
