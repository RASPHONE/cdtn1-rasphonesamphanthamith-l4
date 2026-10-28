from datetime import date, datetime, time, timedelta

import pytest

from src.errors import AppError
from src.schemas.appointment import AppointmentCreate, AppointmentUpdate
from src.services.appointment_service import AppointmentService
from tests.fakes import (
    FakeAppointmentRepository,
    FakeTechnicianRepository,
    FakeTicketRepository,
)


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


def make_service(tickets=None, now_provider=datetime.now):
    ticket_repo = FakeTicketRepository(tickets or [make_ticket()])
    appointment_repo = FakeAppointmentRepository()
    technician_repo = FakeTechnicianRepository(
        [{"technician_id": 1, "center_id": 1, "is_active": True},
         {"technician_id": 3, "center_id": 2, "is_active": True}]
    )
    service = AppointmentService(
        appointment_repository=appointment_repo,
        ticket_repository=ticket_repo,
        technician_repository=technician_repo,
        now_provider=now_provider,
    )
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


# ---------------------------------------------------------------------------
# Boundary values for FR7 (overlap) and US5 AC2 (future time)
# ---------------------------------------------------------------------------

def test_boundary_back_to_back_appointments_do_not_conflict():
    # 09:00-10:00 then 10:00-11:00: intervals touch but do not overlap.
    service, _ = make_service()
    service.create_appointment(center_id=1, payload=make_create_payload())

    second = service.create_appointment(
        center_id=1,
        payload=make_create_payload(gio_bat_dau=time(10, 0), gio_ket_thuc=time(11, 0)),
    )

    assert second["gio_bat_dau"] == time(10, 0)


def test_boundary_one_minute_overlap_conflicts_and_lists_the_conflict():
    service, _ = make_service()
    first = service.create_appointment(center_id=1, payload=make_create_payload())

    with pytest.raises(AppError) as exc:
        service.create_appointment(
            center_id=1,
            payload=make_create_payload(gio_bat_dau=time(9, 59), gio_ket_thuc=time(11, 0)),
        )

    assert exc.value.code == "appointment_conflict"
    assert [c["appointment_id"] for c in exc.value.extra["conflicts"]] == [first["appointment_id"]]


def test_boundary_start_exactly_now_is_rejected_one_minute_later_is_accepted():
    fixed_now = datetime(2026, 11, 2, 9, 0)
    service, _ = make_service(now_provider=lambda: fixed_now)

    with pytest.raises(AppError) as exc:
        service.create_appointment(
            center_id=1,
            payload=make_create_payload(
                ngay_hen=date(2026, 11, 2), gio_bat_dau=time(9, 0), gio_ket_thuc=time(10, 0)
            ),
        )
    assert exc.value.code == "appointment_in_past"

    created = service.create_appointment(
        center_id=1,
        payload=make_create_payload(
            ngay_hen=date(2026, 11, 2), gio_bat_dau=time(9, 1), gio_ket_thuc=time(10, 0)
        ),
    )
    assert created["trang_thai"] == "DA_XAC_NHAN"


# ---------------------------------------------------------------------------
# Conflict pre-check (GET /api/appointments/conflicts)
# ---------------------------------------------------------------------------

def test_check_conflicts_returns_overlapping_appointments():
    service, _ = make_service()
    first = service.create_appointment(center_id=1, payload=make_create_payload())

    result = service.check_conflicts(
        center_id=1, technician_id=1, ngay_hen=future_date(1),
        gio_bat_dau=time(9, 30), gio_ket_thuc=time(10, 30),
    )

    assert [c["appointment_id"] for c in result["conflicts"]] == [first["appointment_id"]]


def test_check_conflicts_empty_when_free():
    service, _ = make_service()

    result = service.check_conflicts(
        center_id=1, technician_id=1, ngay_hen=future_date(1),
        gio_bat_dau=time(9, 0), gio_ket_thuc=time(10, 0),
    )

    assert result == {"conflicts": []}


def test_check_conflicts_for_other_center_technician_fails():
    service, _ = make_service()

    with pytest.raises(AppError) as exc:
        service.check_conflicts(
            center_id=1, technician_id=3, ngay_hen=future_date(1),
            gio_bat_dau=time(9, 0), gio_ket_thuc=time(10, 0),
        )

    assert exc.value.code == "cross_center_access"
