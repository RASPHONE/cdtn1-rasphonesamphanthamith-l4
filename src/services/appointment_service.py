from datetime import date, datetime, time
from typing import Any, Callable, Dict, List

from src.errors import AppError
from src.schemas.appointment import AppointmentCreate, AppointmentUpdate


class AppointmentService:
    """UC4: create / read / update / soft-delete appointments (FR6, FR7, FR11, QT-14)."""

    ALLOWED_LOAI = {"GIAO_MAY", "NHAN_MAY"}            # v0.2: KIEM_TRA_TAI_CHO deferred
    CLOSED_TICKET_STATUSES = {"HOAN_TAT", "DA_DONG", "DA_HUY"}

    def __init__(
        self,
        appointment_repository,
        ticket_repository,
        technician_repository,
        now_provider: Callable[[], datetime] = datetime.now,
    ):
        self.appointment_repo = appointment_repository
        self.ticket_repo = ticket_repository
        self.technician_repo = technician_repository
        # Injected clock (business timezone in production, fixed time in tests).
        self.now = now_provider

    def list_appointments(
        self,
        *,
        center_id: int,
        page: int,
        page_size: int,
        technician_id: int | None = None,
        ticket_id: int | None = None,
        ngay_hen: date | None = None,
        trang_thai: str | None = None,
        include_deleted: bool = False,
    ) -> Dict[str, Any]:
        items, total = self.appointment_repo.list(
            center_id=center_id,
            page=page,
            page_size=page_size,
            technician_id=technician_id,
            ticket_id=ticket_id,
            ngay_hen=ngay_hen,
            trang_thai=trang_thai,
            include_deleted=include_deleted,
        )

        return {
            "page": page,
            "page_size": page_size,
            "total": total,
            "items": items,
        }

    def get_appointment(
        self,
        *,
        center_id: int,
        appointment_id: int,
        include_deleted: bool = False,
    ) -> Dict[str, Any]:
        return self._get_owned_appointment(
            center_id=center_id,
            appointment_id=appointment_id,
            include_deleted=include_deleted,
        )

    def check_conflicts(
        self,
        *,
        center_id: int,
        technician_id: int,
        ngay_hen: date,
        gio_bat_dau: time,
        gio_ket_thuc: time,
        exclude_appointment_id: int | None = None,
    ) -> Dict[str, Any]:
        """FR7 pre-check used by M3 before saving (UC4 step 5).
        The save-time check in create/update remains authoritative."""
        technician = self.technician_repo.get_by_id(technician_id)

        if not technician:
            raise AppError("technician_not_found", "Technician not found.")

        if technician["center_id"] != center_id:
            raise AppError(
                "cross_center_access",
                "You cannot access another center's technician.",
            )

        self._validate_time_range(gio_bat_dau, gio_ket_thuc)

        return {
            "conflicts": self.appointment_repo.find_conflicts(
                technician_id=technician_id,
                ngay_hen=ngay_hen,
                gio_bat_dau=gio_bat_dau,
                gio_ket_thuc=gio_ket_thuc,
                exclude_appointment_id=exclude_appointment_id,
            )
        }

    def create_appointment(
        self,
        *,
        center_id: int,
        payload: AppointmentCreate,
    ) -> Dict[str, Any]:
        ticket = self.ticket_repo.get_by_id(payload.ticket_id)

        if not ticket or ticket["is_deleted"]:
            raise AppError(
                "ticket_not_found",
                "Ticket not found or already deleted.",
            )

        if ticket["center_id"] != center_id:
            raise AppError(
                "cross_center_access",
                "You cannot create an appointment for another center's ticket.",
            )

        if (
            not ticket["technician_id"]
            or not ticket["is_warranty"]
            or ticket["status"] in self.CLOSED_TICKET_STATUSES
        ):
            raise AppError(
                "ticket_not_assignable",
                "Appointment requires an assigned, active warranty ticket.",
            )

        if payload.loai not in self.ALLOWED_LOAI:
            raise AppError(
                "appointment_type_deferred",
                "Only GIAO_MAY and NHAN_MAY appointments are enabled in BT2.",
            )

        self._validate_time_range(payload.gio_bat_dau, payload.gio_ket_thuc)
        self._validate_future(payload.ngay_hen, payload.gio_bat_dau)
        self._ensure_no_conflict(
            technician_id=ticket["technician_id"],
            ngay_hen=payload.ngay_hen,
            gio_bat_dau=payload.gio_bat_dau,
            gio_ket_thuc=payload.gio_ket_thuc,
        )

        data = {
            "ticket_id": payload.ticket_id,
            "technician_id": ticket["technician_id"],
            "center_id": ticket["center_id"],
            "loai": payload.loai,
            "trang_thai": "DA_XAC_NHAN",
            "ngay_hen": payload.ngay_hen,
            "gio_bat_dau": payload.gio_bat_dau,
            "gio_ket_thuc": payload.gio_ket_thuc,
        }

        return self.appointment_repo.create(data)

    def update_appointment(
        self,
        *,
        center_id: int,
        appointment_id: int,
        payload: AppointmentUpdate,
    ) -> Dict[str, Any]:
        existing = self._get_owned_appointment(
            center_id=center_id,
            appointment_id=appointment_id,
            include_deleted=False,
        )

        if existing["trang_thai"] == "HOAN_TAT":
            raise AppError(
                "appointment_completed_cannot_update",
                "Completed appointments cannot be updated.",
            )

        fields = payload.model_dump(exclude_unset=True)

        if not fields:
            return existing

        if fields.get("loai") is not None and fields["loai"] not in self.ALLOWED_LOAI:
            raise AppError(
                "appointment_type_deferred",
                "Only GIAO_MAY and NHAN_MAY appointments are enabled in BT2.",
            )

        new_ngay_hen = fields.get("ngay_hen") or existing["ngay_hen"]
        new_gio_bat_dau = fields.get("gio_bat_dau") or existing["gio_bat_dau"]
        new_gio_ket_thuc = fields.get("gio_ket_thuc") or existing["gio_ket_thuc"]

        self._validate_time_range(new_gio_bat_dau, new_gio_ket_thuc)

        schedule_changed = any(
            fields.get(field) is not None
            for field in ("ngay_hen", "gio_bat_dau", "gio_ket_thuc")
        )

        if schedule_changed:
            self._validate_future(new_ngay_hen, new_gio_bat_dau)
            self._ensure_no_conflict(
                technician_id=existing["technician_id"],
                ngay_hen=new_ngay_hen,
                gio_bat_dau=new_gio_bat_dau,
                gio_ket_thuc=new_gio_ket_thuc,
                exclude_appointment_id=appointment_id,
            )

        update_fields = {
            key: value
            for key, value in fields.items()
            if key in {"loai", "trang_thai", "ngay_hen", "gio_bat_dau", "gio_ket_thuc"}
            and value is not None
        }

        if not update_fields:
            return existing

        updated = self.appointment_repo.update(appointment_id, update_fields)

        if not updated:
            raise AppError(
                "appointment_not_found",
                "Appointment not found.",
            )

        return updated

    def soft_delete_appointment(
        self,
        *,
        center_id: int,
        appointment_id: int,
    ) -> Dict[str, Any]:
        existing = self._get_owned_appointment(
            center_id=center_id,
            appointment_id=appointment_id,
            include_deleted=False,
        )

        if existing["trang_thai"] == "HOAN_TAT":
            raise AppError(
                "appointment_completed_cannot_delete",
                "Completed appointments cannot be deleted.",
            )

        deleted = self.appointment_repo.soft_delete(appointment_id)

        if not deleted:
            raise AppError(
                "appointment_not_found",
                "Appointment not found.",
            )

        return {
            "appointment_id": deleted["appointment_id"],
            "is_deleted": True,
        }

    def _ensure_no_conflict(
        self,
        *,
        technician_id: int,
        ngay_hen: date,
        gio_bat_dau: time,
        gio_ket_thuc: time,
        exclude_appointment_id: int | None = None,
    ) -> None:
        """FR7: block saving when the technician already has an overlapping
        active appointment. Touching intervals (10:00-11:00 after 09:00-10:00)
        are allowed."""
        conflicts: List[Dict[str, Any]] = self.appointment_repo.find_conflicts(
            technician_id=technician_id,
            ngay_hen=ngay_hen,
            gio_bat_dau=gio_bat_dau,
            gio_ket_thuc=gio_ket_thuc,
            exclude_appointment_id=exclude_appointment_id,
        )

        if conflicts:
            raise AppError(
                "appointment_conflict",
                "The technician already has an overlapping active appointment.",
                extra={"conflicts": conflicts},
            )

    def _get_owned_appointment(
        self,
        *,
        center_id: int,
        appointment_id: int,
        include_deleted: bool,
    ) -> Dict[str, Any]:
        appointment = self.appointment_repo.get_by_id(
            appointment_id,
            include_deleted=include_deleted,
        )

        if not appointment:
            raise AppError(
                "appointment_not_found",
                "Appointment not found.",
            )

        if appointment["center_id"] != center_id:
            raise AppError(
                "cross_center_access",
                "You cannot access another center's appointment.",
            )

        return appointment

    def _validate_time_range(self, gio_bat_dau: time, gio_ket_thuc: time) -> None:
        """CON-01: end time must be after start time."""
        if gio_ket_thuc <= gio_bat_dau:
            raise AppError(
                "invalid_time_range",
                "End time must be after start time.",
            )

    def _validate_future(self, ngay_hen: date, gio_bat_dau: time) -> None:
        """US5 AC2: the appointment start must be strictly after 'now'."""
        start_dt = datetime.combine(ngay_hen, gio_bat_dau)

        if start_dt <= self.now():
            raise AppError(
                "appointment_in_past",
                "Appointment time must be in the future.",
            )
