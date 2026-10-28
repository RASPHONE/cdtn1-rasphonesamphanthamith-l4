from datetime import date, datetime, time, timedelta

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.routes.appointments import get_appointment_service
from src.routes.technician_skills import get_technician_skill_service
from src.routes.tickets import get_ticket_assignment_service
from src.services.appointment_service import AppointmentService
from src.services.technician_skill_service import TechnicianSkillService
from src.services.ticket_assignment_service import TicketAssignmentService
from src.routes.issue_categories import get_issue_category_service
from src.services.issue_category_service import IssueCategoryService
from tests.fakes import (
    FakeAppointmentRepository,
    FakeIssueCategoryRepository,
    FakeTechnicianRepository,
    FakeTechnicianSkillRepository,
    FakeTicketRepository,
    FakeTicketStatusLogRepository,
    fake_transaction,
)


def make_ticket(
    ticket_id,
    center_id,
    category_id,
    status,
    technician_id,
    is_warranty=True,
    is_deleted=False,
):
    category_name = "MAN_HINH"

    if category_id == 4:
        category_name = "PHAN_MEM"
    elif category_id == 7:
        category_name = "CU"

    return {
        "ticket_id": ticket_id,
        "ticket_code": f"PB-{center_id}-{ticket_id:05d}",
        "center_id": center_id,
        "customer_name": f"Customer {ticket_id}",
        "customer_phone": f"090{ticket_id:07d}",
        "serial_no": f"SN{ticket_id:012d}",
        "issue_desc": "Test issue",
        "category_id": category_id,
        "category_name": category_name,
        "priority": "CAO",
        "status": status,
        "technician_id": technician_id,
        "received_at": datetime.now(),
        "due_date": datetime.now() + timedelta(days=2),
        "closed_at": None,
        "is_warranty": is_warranty,
        "is_deleted": is_deleted,
    }


@pytest.fixture
def fake_repos():
    categories = [
        {
            "category_id": 1,
            "category_name": "MAN_HINH",
            "default_priority": "CAO",
            "is_active": True,
        },
        {
            "category_id": 4,
            "category_name": "PHAN_MEM",
            "default_priority": "THAP",
            "is_active": True,
        },
        {
            "category_id": 7,
            "category_name": "CU",
            "default_priority": "THAP",
            "is_active": False,
        },
    ]

    technicians = [
        {
            "technician_id": 1,
            "technician_code": "KT001",
            "ho_ten": "Nguyen Van A",
            "center_id": 1,
            "level": "TRUNG_CAP",
            "is_active": True,
        },
        {
            "technician_id": 2,
            "technician_code": "KT002",
            "ho_ten": "Tran Van B",
            "center_id": 1,
            "level": "CAO_CAP",
            "is_active": True,
        },
        {
            "technician_id": 3,
            "technician_code": "KT003",
            "ho_ten": "Le Van C",
            "center_id": 2,
            "level": "CAO_CAP",
            "is_active": True,
        },
    ]

    skills = [
        {
            "technician_id": 1,
            "category_id": 1,
            "category_name": "MAN_HINH",
            "proficiency": 4,
        },
        {
            "technician_id": 2,
            "category_id": 1,
            "category_name": "MAN_HINH",
            "proficiency": 3,
        },
        {
            "technician_id": 3,
            "category_id": 1,
            "category_name": "MAN_HINH",
            "proficiency": 4,
        },
    ]

    tickets = [
        make_ticket(
            ticket_id=101,
            center_id=1,
            category_id=1,
            status="MOI",
            technician_id=None,
        ),
        make_ticket(
            ticket_id=103,
            center_id=1,
            category_id=1,
            status="DA_PHAN_CONG",
            technician_id=1,
        ),
        make_ticket(
            ticket_id=201,
            center_id=2,
            category_id=1,
            status="MOI",
            technician_id=None,
        ),
    ]

    ticket_repo = FakeTicketRepository(tickets)
    # Result of the QT-08 suggestion query, keyed by (center_id, category_id).
    qualified = {
        (1, 1): [
            {"technician_id": 2, "technician_code": "KT002", "ho_ten": "Tran Van B",
             "level": "CAO_CAP", "proficiency": 3, "workload": 0},
            {"technician_id": 1, "technician_code": "KT001", "ho_ten": "Nguyen Van A",
             "level": "TRUNG_CAP", "proficiency": 4, "workload": 1},
        ],
        (2, 1): [
            {"technician_id": 3, "technician_code": "KT003", "ho_ten": "Le Van C",
             "level": "CAO_CAP", "proficiency": 4, "workload": 0},
        ],
    }
    technician_repo = FakeTechnicianRepository(technicians, qualified=qualified)
    category_repo = FakeIssueCategoryRepository(categories)
    skill_repo = FakeTechnicianSkillRepository(skills)
    status_log_repo = FakeTicketStatusLogRepository()
    appointment_repo = FakeAppointmentRepository()

    return {
        "ticket_repo": ticket_repo,
        "technician_repo": technician_repo,
        "category_repo": category_repo,
        "skill_repo": skill_repo,
        "status_log_repo": status_log_repo,
        "appointment_repo": appointment_repo,
    }


@pytest.fixture
def client(fake_repos, monkeypatch):
    def override_appointment_service():
        return AppointmentService(
            appointment_repository=fake_repos["appointment_repo"],
            ticket_repository=fake_repos["ticket_repo"],
            technician_repository=fake_repos["technician_repo"],
        )

    def override_technician_skill_service():
        return TechnicianSkillService(
            technician_repository=fake_repos["technician_repo"],
            category_repository=fake_repos["category_repo"],
            skill_repository=fake_repos["skill_repo"],
        )

    def override_ticket_assignment_service():
        return TicketAssignmentService(
            ticket_repository=fake_repos["ticket_repo"],
            technician_repository=fake_repos["technician_repo"],
            technician_skill_repository=fake_repos["skill_repo"],
            status_log_repository=fake_repos["status_log_repo"],
            transaction=fake_transaction,
        )

    def override_issue_category_service():
        return IssueCategoryService(category_repository=fake_repos["category_repo"])

    app.dependency_overrides[get_appointment_service] = override_appointment_service
    app.dependency_overrides[
        get_technician_skill_service
    ] = override_technician_skill_service
    app.dependency_overrides[
        get_ticket_assignment_service
    ] = override_ticket_assignment_service
    app.dependency_overrides[get_issue_category_service] = override_issue_category_service

    # /health pings the database; pretend it is up so tests never need PostgreSQL.
    monkeypatch.setattr("src.routes.health.ping", lambda: True)

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
