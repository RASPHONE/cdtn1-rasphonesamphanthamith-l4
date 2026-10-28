"""BT2 TP2 evidence: one representative test for each of the three required types.

Run only these:  pytest -v tests/test_bt2_three_types.py
Traceability:    FR3/FR4 -> US4 -> UC3 (QT-08) and FR5 -> US4 (QT-07).
The full suite (pytest -q) contains many more cases of each type.
"""
import pytest

from src.errors import AppError
from src.schemas.ticket import AssignmentCreate
from src.services.ticket_assignment_service import TicketAssignmentService
from tests.fakes import (
    FakeTechnicianRepository,
    FakeTechnicianSkillRepository,
    FakeTicketRepository,
    FakeTicketStatusLogRepository,
    fake_transaction,
)


def build_service():
    ticket = {
        "ticket_id": 101, "ticket_code": "BH-000101/2026", "center_id": 1,
        "category_id": 1, "status": "MOI", "technician_id": None,
        "is_warranty": True, "is_deleted": False,
    }
    technicians = [
        {"technician_id": 7, "center_id": 1, "is_active": True},
        {"technician_id": 8, "center_id": 1, "is_active": True},
    ]
    skills = [
        {"technician_id": 7, "category_id": 1, "proficiency": 3},  # exactly the threshold
        {"technician_id": 8, "category_id": 1, "proficiency": 2},  # one below
    ]
    log_repo = FakeTicketStatusLogRepository()
    service = TicketAssignmentService(
        ticket_repository=FakeTicketRepository([ticket]),
        technician_repository=FakeTechnicianRepository(technicians),
        technician_skill_repository=FakeTechnicianSkillRepository(skills),
        status_log_repository=log_repo,
        transaction=fake_transaction,
    )
    return service, log_repo


def test_tc01_happy_path_assign_qualified_technician():
    """TC-01 (happy path): a qualified technician of the same center is assigned,
    the ticket moves MOI -> DA_PHAN_CONG and one status log row is written."""
    service, log_repo = build_service()

    result = service.assign_technician(
        center_id=1, ticket_id=101, payload=AssignmentCreate(technician_id=7), changed_by=1
    )

    assert result["status"] == "DA_PHAN_CONG"
    assert result["technician_id"] == 7
    assert [(log["from_status"], log["to_status"]) for log in log_repo.logs] == [("MOI", "DA_PHAN_CONG")]


def test_tc02_boundary_proficiency_3_accepted_2_rejected():
    """TC-02 (boundary): QT-08 requires proficiency >= 3.
    Exactly 3 is accepted; 2 (one below) is rejected with technician_not_qualified."""
    service, _ = build_service()
    with pytest.raises(AppError) as exc:
        service.assign_technician(
            center_id=1, ticket_id=101, payload=AssignmentCreate(technician_id=8), changed_by=1
        )
    assert exc.value.code == "technician_not_qualified"

    result = service.assign_technician(
        center_id=1, ticket_id=101, payload=AssignmentCreate(technician_id=7), changed_by=1
    )
    assert result["technician_id"] == 7


def test_tc03_invalid_data_rejected_with_clear_message(client):
    """TC-03 (invalid data): through the real HTTP API.
    (a) a missing required field -> 400 naming the field;
    (b) reassignment without a reason -> 422 reason_required (QT-07).
    Neither crashes nor leaks a raw library error."""
    login = client.post("/api/auth/login", json={"username": "manager1", "password": "manager123"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    missing_field = client.post("/api/appointments", json={"ticket_id": 103}, headers=headers)
    assert missing_field.status_code == 400
    assert missing_field.json()["error"] == "bad_request"
    assert {d["field"] for d in missing_field.json()["details"]} == {
        "loai", "ngay_hen", "gio_bat_dau", "gio_ket_thuc",
    }

    no_reason = client.patch("/api/tickets/103/assignment", json={"technician_id": 2}, headers=headers)
    assert no_reason.status_code == 422
    assert no_reason.json() == {
        "error": "reason_required",
        "message": "Reason is required when changing technician (5-255 characters).",
        "details": [{"field": "reason", "message": "5-255 characters required"}],
    }
