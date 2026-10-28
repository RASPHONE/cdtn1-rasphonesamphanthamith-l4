from datetime import date, time, timedelta

import pytest

from src.errors import AppError
from src.schemas.appointment import AppointmentCreate, AppointmentUpdate
from src.services.appointment_service import AppointmentService


class FakeTicketRepository:
    def __init__(self, tickets=None):
        self.tickets = {ticket["ticket_id"]: dict(ticket) for ticket in tickets or []}

    def get_by_id(self, ticket_id):
        return self.tickets.get(ticket_id)


class FakeAppointmentRepository:
    def __init__(self):
        self.appointments = {}
        self.next_id = 1

    def get_by_id(self, appointment_id, include_deleted=False):
        appointment = self.appointments.get(appointment_id)
        if not appointment:
            return None
        if not include_deleted and appointment["is_deleted"]:
            return None
        return dict(appointment)

    def list(
        self,
        *,
        center_id,
        page,
        page_size,
        technician_id=None,
        ticket_id=None,
        ngay_hen=None,
        trang_thai=None,
        include_deleted=False,
    ):
        items = [
            dict(appointment)
            for appointment in self.appointments.values()
            if appointment["center_id"] == center_id
        ]

        if not include_deleted:
            items = [item for item in items if not item["is_deleted"]]

        if technician_id is not None:
            items = [item for item in items if item["technician_id"] == technician_id]

        if ticket_id is not None:
            items = [item for item in items if item["ticket_id"] == ticket_id]

        if ngay_hen is not None:
            items = [item for item in items if item["ngay_hen"] == ngay_hen]

        if trang_thai is not None:
            items = [item for item in items if item["trang_thai"] == trang_thai]

        items.sort(key=lambda item: (item["ngay_hen"], item["gio_bat_dau"]))
        total = len(items)

        start = (page - 1) * page_size
        end = start + page_size

        return items[start:end], total

    def create(self, data):
        appointment = dict(data)
        appointment["appointment_id"] = self.next_id
        appointment.setdefault("is_deleted", False)
        self.next_id += 1
        self.appointments[appointment["appointment_id"]] = dict(appointment)
        return dict(appointment)

    def update(self, appointment_id, fields):
        appointment = self.appointments.get(appointment_id)
        if not appointment or appointment["is_deleted"]:
            return None
        appointment.update(fields)
        return dict(appointment)

    def soft_delete(self, appointment_id):
        appointment = self.appointments.get(appointment_id)
        if not appointment or appointment["is_deleted"]:
            return None
        appointment["is_deleted"] = True
        return dict(appointment)

    def has_conflict(
        self,
        *,
        technician_id,
        ngay_hen,
        gio_bat_dau,
        gio_ket_thuc,
        exclude_appointment_id=None,
    ):
        for appointment in self.appointments.values():
            if appointment["technician_id"] != technician_id:
                continue
            if appointment["ngay_hen"] != ngay_hen:
                continue
            if appointment["is_deleted"]:
                continue
            if appointment["trang_thai"] not in ("DA_DAT", "DA_XAC_NHAN"):
                continue
            if exclude_appointment_id == appointment["appointment_id"]:
                continue

            if (
                appointment["gio_bat_dau"] < gio_ket_thuc
                and appointment["gio_ket_thuc"] > gio_bat_dau
            ):
                return True

        return False


def make_ticket(
    ticket_id=101,
    center_id=1,
    technician_id=1,
    status="DA_PHAN_CONG",
    is_warranty=True,
    is_deleted=False,
):
    return {
        "ticket_id": ticket_id,
        "center_id": center_id,
        "technician_id": technician_id,
        "status": status,
        "is_warranty": is_warranty,
        "is_deleted": is_deleted,
    }


def future_date(days=1):
    return date.today() + timedelta(days=days)


def make_service(tickets=None):
    ticket_repo = FakeTicketRepository(tickets or [make_ticket()])
    appointment_repo = FakeAppointmentRepository()
    service = AppointmentService(appointment_repo, ticket_repo)
    return service, appointment_repo


def make_create_payload(**kwargs):
    defaults = {
        "ticket_id": 101,
        "loai": "GIAO_MAY",
        "ngay_hen": future_date(1),
        "gio_bat_dau": time(9, 0),
        "gio_ket_thuc": time(10, 0),
    }
    defaults.update(kwargs)
    return AppointmentCreate(**defaults)


def test_create_valid_appointment():
    service, _ = make_service()
    payload = make_create_payload()

    result = service.create_appointment(center_id=1, payload=payload)

    assert result["ticket_id"] == 101
    assert result["technician_id"] == 1
    assert result["center_id"] == 1
    assert result["loai"] == "GIAO_MAY"
    assert result["trang_thai"] == "DA_XAC_NHAN"
    assert result["is_deleted"] is False


def test_create_appointment_for_unassigned_ticket_fails():
    service, _ = make_service([make_ticket(technician_id=None)])
    payload = make_create_payload()

    with pytest.raises(AppError) as exc:
        service.create_appointment(center_id=1, payload=payload)

    assert exc.value.code == "ticket_not_assignable"


def test_create_appointment_for_non_warranty_ticket_fails():
    service, _ = make_service([make_ticket(is_warranty=False)])
    payload = make_create_payload()

    with pytest.raises(AppError) as exc:
        service.create_appointment(center_id=1, payload=payload)

    assert exc.value.code == "ticket_not_assignable"


def test_create_appointment_cross_center_fails():
    service, _ = make_service([make_ticket(center_id=1)])
    payload = make_create_payload()

    with pytest.raises(AppError) as exc:
        service.create_appointment(center_id=2, payload=payload)

    assert exc.value.code == "cross_center_access"


def test_create_appointment_with_invalid_time_range_fails():
    service, _ = make_service()
    payload = make_create_payload(
        gio_bat_dau=time(10, 0),
        gio_ket_thuc=time(9, 0),
    )

    with pytest.raises(AppError) as exc:
        service.create_appointment(center_id=1, payload=payload)

    assert exc.value.code == "invalid_time_range"


def test_create_appointment_in_past_fails():
    service, _ = make_service()
    payload = make_create_payload(
        ngay_hen=date.today() - timedelta(days=1),
        gio_bat_dau=time(9, 0),
        gio_ket_thuc=time(10, 0),
    )

    with pytest.raises(AppError) as exc:
        service.create_appointment(center_id=1, payload=payload)

    assert exc.value.code == "appointment_in_past"


def test_create_conflicting_appointment_fails():
    service, _ = make_service()
    payload = make_create_payload()

    service.create_appointment(center_id=1, payload=payload)

    with pytest.raises(AppError) as exc:
        service.create_appointment(center_id=1, payload=payload)

    assert exc.value.code == "appointment_conflict"


def test_soft_deleted_appointment_does_not_cause_conflict():
    service, _ = make_service()
    payload = make_create_payload()

    created = service.create_appointment(center_id=1, payload=payload)
    service.soft_delete_appointment(
        center_id=1,
        appointment_id=created["appointment_id"],
    )

    recreated = service.create_appointment(center_id=1, payload=payload)
    assert recreated["is_deleted"] is False


def test_soft_delete_active_appointment():
    service, _ = make_service()
    payload = make_create_payload()

    created = service.create_appointment(center_id=1, payload=payload)
    result = service.soft_delete_appointment(
        center_id=1,
        appointment_id=created["appointment_id"],
    )

    assert result["appointment_id"] == created["appointment_id"]
    assert result["is_deleted"] is True


def test_soft_delete_completed_appointment_fails():
    service, appointment_repo = make_service()
    payload = make_create_payload()

    created = service.create_appointment(center_id=1, payload=payload)
    appointment_repo.appointments[created["appointment_id"]]["trang_thai"] = "HOAN_TAT"

    with pytest.raises(AppError) as exc:
        service.soft_delete_appointment(
            center_id=1,
            appointment_id=created["appointment_id"],
        )

    assert exc.value.code == "appointment_completed_cannot_delete"


def test_update_completed_appointment_fails():
    service, appointment_repo = make_service()
    payload = make_create_payload()

    created = service.create_appointment(center_id=1, payload=payload)
    appointment_repo.appointments[created["appointment_id"]]["trang_thai"] = "HOAN_TAT"

    update_payload = AppointmentUpdate(gio_bat_dau=time(11, 0), gio_ket_thuc=time(12, 0))

    with pytest.raises(AppError) as exc:
        service.update_appointment(
            center_id=1,
            appointment_id=created["appointment_id"],
            payload=update_payload,
        )

    assert exc.value.code == "appointment_completed_cannot_update"


def test_update_appointment_schedule():
    service, _ = make_service()
    payload = make_create_payload()

    created = service.create_appointment(center_id=1, payload=payload)

    update_payload = AppointmentUpdate(
        ngay_hen=future_date(2),
        gio_bat_dau=time(11, 0),
        gio_ket_thuc=time(12, 0),
    )

    updated = service.update_appointment(
        center_id=1,
        appointment_id=created["appointment_id"],
        payload=update_payload,
    )

    assert updated["ngay_hen"] == future_date(2)
    assert updated["gio_bat_dau"] == time(11, 0)
    assert updated["gio_ket_thuc"] == time(12, 0)
