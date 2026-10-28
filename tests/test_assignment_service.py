import pytest

from src.errors import AppError
from src.schemas.ticket import AssignmentCreate, AssignmentUpdate
from src.services.ticket_assignment_service import TicketAssignmentService
from tests.fakes import (
    FakeTechnicianRepository,
    FakeTechnicianSkillRepository,
    FakeTicketRepository,
    FakeTicketStatusLogRepository,
    fake_transaction,
)


def make_ticket(
    ticket_id=101,
    center_id=1,
    category_id=1,
    status="MOI",
    technician_id=None,
    is_warranty=True,
    is_deleted=False,
):
    return {
        "ticket_id": ticket_id,
        "ticket_code": f"P{ticket_id}",
        "center_id": center_id,
        "category_id": category_id,
        "status": status,
        "technician_id": technician_id,
        "is_warranty": is_warranty,
        "is_deleted": is_deleted,
    }


def make_technician(technician_id, center_id=1, is_active=True):
    return {
        "technician_id": technician_id,
        "center_id": center_id,
        "is_active": is_active,
    }


def make_skill(technician_id, category_id=1, proficiency=4):
    return {
        "technician_id": technician_id,
        "category_id": category_id,
        "proficiency": proficiency,
    }


def make_service(ticket_overrides=None, technicians=None, skills=None):
    ticket = make_ticket(**(ticket_overrides or {}))

    if technicians is None:
        technicians = [
            make_technician(1, center_id=1, is_active=True),
            make_technician(2, center_id=1, is_active=True),
            make_technician(3, center_id=2, is_active=True),
            make_technician(4, center_id=1, is_active=True),
            make_technician(5, center_id=1, is_active=False),
        ]

    if skills is None:
        skills = [
            make_skill(1, category_id=1, proficiency=4),
            make_skill(2, category_id=1, proficiency=2),
            make_skill(3, category_id=1, proficiency=4),
            make_skill(4, category_id=1, proficiency=3),
            make_skill(5, category_id=1, proficiency=5),
        ]

    ticket_repo = FakeTicketRepository([ticket])
    technician_repo = FakeTechnicianRepository(technicians)
    skill_repo = FakeTechnicianSkillRepository(skills)
    log_repo = FakeTicketStatusLogRepository()

    service = TicketAssignmentService(
        ticket_repository=ticket_repo,
        technician_repository=technician_repo,
        technician_skill_repository=skill_repo,
        status_log_repository=log_repo,
        transaction=fake_transaction,
    )

    return service, log_repo, ticket_repo


def test_assign_valid_technician():
    service, log_repo, _ = make_service()
    payload = AssignmentCreate(technician_id=1)

    result = service.assign_technician(
        center_id=1,
        ticket_id=101,
        payload=payload,
        changed_by=1,
    )

    assert result["status"] == "DA_PHAN_CONG"
    assert result["technician_id"] == 1

    assert len(log_repo.logs) == 1
    assert log_repo.logs[0]["from_status"] == "MOI"
    assert log_repo.logs[0]["to_status"] == "DA_PHAN_CONG"


def test_assign_unqualified_technician_fails():
    service, _, _ = make_service()
    payload = AssignmentCreate(technician_id=2)

    with pytest.raises(AppError) as exc:
        service.assign_technician(
            center_id=1,
            ticket_id=101,
            payload=payload,
            changed_by=1,
        )

    assert exc.value.code == "technician_not_qualified"


def test_assign_technician_from_other_center_fails():
    service, _, _ = make_service()
    payload = AssignmentCreate(technician_id=3)

    with pytest.raises(AppError) as exc:
        service.assign_technician(
            center_id=1,
            ticket_id=101,
            payload=payload,
            changed_by=1,
        )

    assert exc.value.code == "technician_not_qualified"


def test_assign_inactive_technician_fails():
    service, _, _ = make_service()
    payload = AssignmentCreate(technician_id=5)

    with pytest.raises(AppError) as exc:
        service.assign_technician(
            center_id=1,
            ticket_id=101,
            payload=payload,
            changed_by=1,
        )

    assert exc.value.code == "technician_not_qualified"


def test_assign_missing_technician_fails():
    service, _, _ = make_service()
    payload = AssignmentCreate(technician_id=999)

    with pytest.raises(AppError) as exc:
        service.assign_technician(
            center_id=1,
            ticket_id=101,
            payload=payload,
            changed_by=1,
        )

    assert exc.value.code == "technician_not_found"


def test_assign_already_assigned_ticket_fails():
    service, _, _ = make_service(
        ticket_overrides={
            "status": "DA_PHAN_CONG",
            "technician_id": 1,
        }
    )
    payload = AssignmentCreate(technician_id=4)

    with pytest.raises(AppError) as exc:
        service.assign_technician(
            center_id=1,
            ticket_id=101,
            payload=payload,
            changed_by=1,
        )

    assert exc.value.code == "ticket_not_assignable"


def test_assign_closed_ticket_fails():
    service, _, _ = make_service(
        ticket_overrides={
            "status": "DA_DONG",
        }
    )
    payload = AssignmentCreate(technician_id=1)

    with pytest.raises(AppError) as exc:
        service.assign_technician(
            center_id=1,
            ticket_id=101,
            payload=payload,
            changed_by=1,
        )

    assert exc.value.code == "ticket_not_assignable"


def test_assign_cross_center_ticket_fails():
    service, _, _ = make_service(
        ticket_overrides={
            "center_id": 2,
        }
    )
    payload = AssignmentCreate(technician_id=1)

    with pytest.raises(AppError) as exc:
        service.assign_technician(
            center_id=1,
            ticket_id=101,
            payload=payload,
            changed_by=1,
        )

    assert exc.value.code == "cross_center_access"


def test_reassign_with_reason():
    service, log_repo, _ = make_service(
        ticket_overrides={
            "status": "DA_PHAN_CONG",
            "technician_id": 1,
        }
    )
    payload = AssignmentUpdate(technician_id=4, reason="Rebalance workload")

    result = service.reassign_technician(
        center_id=1,
        ticket_id=101,
        payload=payload,
        changed_by=1,
    )

    assert result["technician_id"] == 4

    assert len(log_repo.logs) == 1
    assert log_repo.logs[0]["note"] == "Rebalance workload"


def test_reassign_without_reason_fails():
    service, _, _ = make_service(
        ticket_overrides={
            "status": "DA_PHAN_CONG",
            "technician_id": 1,
        }
    )
    payload = AssignmentUpdate(technician_id=4, reason="   ")

    with pytest.raises(AppError) as exc:
        service.reassign_technician(
            center_id=1,
            ticket_id=101,
            payload=payload,
            changed_by=1,
        )

    assert exc.value.code == "reason_required"


def test_reassign_unassigned_ticket_fails():
    service, _, _ = make_service()
    payload = AssignmentUpdate(technician_id=4, reason="Need reassignment")

    with pytest.raises(AppError) as exc:
        service.reassign_technician(
            center_id=1,
            ticket_id=101,
            payload=payload,
            changed_by=1,
        )

    assert exc.value.code == "ticket_not_assignable"


def test_reassign_to_inactive_technician_fails():
    service, _, _ = make_service(
        ticket_overrides={
            "status": "DA_PHAN_CONG",
            "technician_id": 1,
        }
    )
    payload = AssignmentUpdate(technician_id=5, reason="Reassign")

    with pytest.raises(AppError) as exc:
        service.reassign_technician(
            center_id=1,
            ticket_id=101,
            payload=payload,
            changed_by=1,
        )

    assert exc.value.code == "technician_not_qualified"


# ---------------------------------------------------------------------------
# Boundary values (BT2 TP2 type 2)
# ---------------------------------------------------------------------------

def test_boundary_proficiency_exactly_3_is_qualified():
    # QT-08: proficiency >= 3. Technician 4 has exactly 3.
    service, _, _ = make_service()

    result = service.assign_technician(
        center_id=1, ticket_id=101, payload=AssignmentCreate(technician_id=4), changed_by=1
    )

    assert result["technician_id"] == 4


def test_boundary_proficiency_2_is_not_qualified():
    # QT-08: one below the threshold. Technician 2 has proficiency 2.
    service, log_repo, _ = make_service()

    with pytest.raises(AppError) as exc:
        service.assign_technician(
            center_id=1, ticket_id=101, payload=AssignmentCreate(technician_id=2), changed_by=1
        )

    assert exc.value.code == "technician_not_qualified"
    assert log_repo.logs == []


def test_boundary_reason_with_5_characters_is_accepted():
    # QT-07: 5 characters is the minimum accepted reason length.
    service, log_repo, _ = make_service(
        ticket_overrides={"status": "DA_PHAN_CONG", "technician_id": 1}
    )

    service.reassign_technician(
        center_id=1, ticket_id=101,
        payload=AssignmentUpdate(technician_id=4, reason="Om 3n"), changed_by=1,
    )

    assert log_repo.logs[0]["note"] == "Om 3n"


def test_boundary_reason_with_4_characters_is_rejected():
    service, log_repo, _ = make_service(
        ticket_overrides={"status": "DA_PHAN_CONG", "technician_id": 1}
    )

    with pytest.raises(AppError) as exc:
        service.reassign_technician(
            center_id=1, ticket_id=101,
            payload=AssignmentUpdate(technician_id=4, reason="Bom!"), changed_by=1,
        )

    assert exc.value.code == "reason_required"
    assert log_repo.logs == []


# ---------------------------------------------------------------------------
# Invalid data (BT2 TP2 type 3)
# ---------------------------------------------------------------------------

def test_reassign_with_missing_reason_fails():
    # Field omitted entirely -> still the QT-07 business error, not a crash.
    service, _, _ = make_service(
        ticket_overrides={"status": "DA_PHAN_CONG", "technician_id": 1}
    )

    with pytest.raises(AppError) as exc:
        service.reassign_technician(
            center_id=1, ticket_id=101,
            payload=AssignmentUpdate(technician_id=4), changed_by=1,
        )

    assert exc.value.code == "reason_required"


def test_assignment_lost_race_is_rejected_without_log():
    # Another manager assigned the ticket between our read and our update:
    # the guarded UPDATE matches no row and nothing is logged (NFR5).
    service, log_repo, ticket_repo = make_service()
    original_assign = ticket_repo.assign_technician

    def assign_after_someone_else(ticket_id, technician_id, new_status, conn=None):
        ticket_repo.tickets[ticket_id]["technician_id"] = 99
        return original_assign(ticket_id, technician_id, new_status, conn=conn)

    ticket_repo.assign_technician = assign_after_someone_else

    with pytest.raises(AppError) as exc:
        service.assign_technician(
            center_id=1, ticket_id=101, payload=AssignmentCreate(technician_id=1), changed_by=1
        )

    assert exc.value.code == "ticket_not_assignable"
    assert log_repo.logs == []
