import pytest

from src.errors import AppError
from src.schemas.ticket import AssignmentCreate, AssignmentUpdate
from src.services.ticket_assignment_service import TicketAssignmentService


class FakeTicketRepository:
    def __init__(self, tickets):
        self.tickets = {ticket["ticket_id"]: dict(ticket) for ticket in tickets}

    def get_by_id(self, ticket_id):
        ticket = self.tickets.get(ticket_id)
        return dict(ticket) if ticket else None

    def list_unassigned(
        self,
        *,
        center_id,
        category_id=None,
        priority=None,
        page=1,
        page_size=20,
    ):
        items = [
            dict(ticket)
            for ticket in self.tickets.values()
            if ticket["center_id"] == center_id
            and ticket["is_deleted"] is False
            and ticket["is_warranty"] is True
            and ticket["status"] == "MOI"
            and ticket["technician_id"] is None
        ]

        if category_id is not None:
            items = [item for item in items if item["category_id"] == category_id]

        if priority is not None:
            items = [item for item in items if item["priority"] == priority]

        total = len(items)
        start = (page - 1) * page_size
        end = start + page_size

        return items[start:end], total

    def assign_technician(self, ticket_id, technician_id, new_status, conn=None):
        ticket = self.tickets.get(ticket_id)
        if not ticket:
            return None
        ticket["technician_id"] = technician_id
        ticket["status"] = new_status
        return dict(ticket)

    def update_technician(self, ticket_id, technician_id, conn=None):
        ticket = self.tickets.get(ticket_id)
        if not ticket:
            return None
        ticket["technician_id"] = technician_id
        return dict(ticket)


class FakeTechnicianRepository:
    def __init__(self, technicians):
        self.technicians = {
            technician["technician_id"]: dict(technician)
            for technician in technicians
        }

    def get_by_id(self, technician_id):
        technician = self.technicians.get(technician_id)
        return dict(technician) if technician else None

    def list_qualified_for_category(self, *, center_id, category_id):
        return []


class FakeTechnicianSkillRepository:
    def __init__(self, skills):
        self.skills = {
            (skill["technician_id"], skill["category_id"]): dict(skill)
            for skill in skills
        }

    def get_skill(self, technician_id, category_id):
        skill = self.skills.get((technician_id, category_id))
        return dict(skill) if skill else None


class FakeTicketStatusLogRepository:
    def __init__(self):
        self.logs = []
        self.next_log_id = 1000

    def create(
        self,
        *,
        ticket_id,
        from_status,
        to_status,
        changed_by,
        note=None,
        conn=None,
    ):
        log_id = self.next_log_id
        self.next_log_id += 1

        self.logs.append(
            {
                "log_id": log_id,
                "ticket_id": ticket_id,
                "from_status": from_status,
                "to_status": to_status,
                "changed_by": changed_by,
                "note": note,
            }
        )
        return log_id


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
