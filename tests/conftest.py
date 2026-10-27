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

        items.sort(key=lambda item: item["due_date"])

        total = len(items)
        start = (page - 1) * page_size
        end = start + page_size

        return items[start:end], total

    def assign_technician(self, ticket_id, technician_id, new_status):
        ticket = self.tickets.get(ticket_id)
        if not ticket:
            return None

        ticket["technician_id"] = technician_id
        ticket["status"] = new_status

        return dict(ticket)

    def update_technician(self, ticket_id, technician_id):
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
        if center_id == 1 and category_id == 1:
            return [
                {
                    "technician_id": 2,
                    "technician_code": "KT002",
                    "ho_ten": "Tran Van B",
                    "level": "CAO_CAP",
                    "proficiency": 3,
                    "workload": 0,
                },
                {
                    "technician_id": 1,
                    "technician_code": "KT001",
                    "ho_ten": "Nguyen Van A",
                    "level": "TRUNG_CAP",
                    "proficiency": 4,
                    "workload": 1,
                },
            ]

        if center_id == 2 and category_id == 1:
            return [
                {
                    "technician_id": 3,
                    "technician_code": "KT003",
                    "ho_ten": "Le Van C",
                    "level": "CAO_CAP",
                    "proficiency": 4,
                    "workload": 0,
                }
            ]

        return []


class FakeTechnicianSkillRepository:
    def __init__(self, skills, category_names=None):
        self.skills = {
            (skill["technician_id"], skill["category_id"]): dict(skill)
            for skill in skills
        }
        self.category_names = category_names or {
            1: "MAN_HINH",
            4: "PHAN_MEM",
            7: "CU",
        }

    def list_by_technician(self, technician_id):
        return [
            dict(skill)
            for skill in self.skills.values()
            if skill["technician_id"] == technician_id
        ]

    def get_skill(self, technician_id, category_id):
        skill = self.skills.get((technician_id, category_id))
        return dict(skill) if skill else None

    def create(self, technician_id, category_id, proficiency):
        key = (technician_id, category_id)

        self.skills[key] = {
            "technician_id": technician_id,
            "category_id": category_id,
            "category_name": self.category_names.get(
                category_id,
                f"CATEGORY_{category_id}",
            ),
            "proficiency": proficiency,
        }

    def update_proficiency(self, technician_id, category_id, proficiency):
        key = (technician_id, category_id)

        if key not in self.skills:
            return

        self.skills[key]["proficiency"] = proficiency

    def delete_skill(self, technician_id, category_id):
        key = (technician_id, category_id)
        return self.skills.pop(key, None) is not None


class FakeIssueCategoryRepository:
    def __init__(self, categories):
        self.categories = {
            category["category_id"]: dict(category)
            for category in categories
        }

    def get_by_id(self, category_id):
        category = self.categories.get(category_id)
        return dict(category) if category else None


class FakeTicketStatusLogRepository:
    def __init__(self):
        self.logs = []

    def create(
        self,
        *,
        ticket_id,
        from_status,
        to_status,
        changed_by,
        note=None,
    ):
        self.logs.append(
            {
                "ticket_id": ticket_id,
                "from_status": from_status,
                "to_status": to_status,
                "changed_by": changed_by,
                "note": note,
            }
        )


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
    technician_repo = FakeTechnicianRepository(technicians)
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
def client(fake_repos):
    def override_appointment_service():
        return AppointmentService(
            appointment_repository=fake_repos["appointment_repo"],
            ticket_repository=fake_repos["ticket_repo"],
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
        )

    app.dependency_overrides[get_appointment_service] = override_appointment_service
    app.dependency_overrides[
        get_technician_skill_service
    ] = override_technician_skill_service
    app.dependency_overrides[
        get_ticket_assignment_service
    ] = override_ticket_assignment_service

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
