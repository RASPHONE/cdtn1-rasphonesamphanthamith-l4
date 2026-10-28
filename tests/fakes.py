"""In-memory fake repositories shared by every test file.

They implement the same methods as the Postgres* repositories in
src/repositories, so services can be tested without PostgreSQL
(BT2 TP2: tests must not depend on data on the developer's machine).
"""
from contextlib import contextmanager

ACTIVE_APPOINTMENT_STATUSES = ("DA_DAT", "DA_XAC_NHAN")


@contextmanager
def fake_transaction():
    """Stand-in for repositories.transaction.postgres_transaction."""
    yield object()


class FakeTicketRepository:
    def __init__(self, tickets=None):
        self.tickets = {ticket["ticket_id"]: dict(ticket) for ticket in tickets or []}

    def get_by_id(self, ticket_id, conn=None):
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

        items.sort(key=lambda item: item.get("due_date") or 0)

        total = len(items)
        start = (page - 1) * page_size
        return items[start:start + page_size], total

    def assign_technician(self, ticket_id, technician_id, new_status, conn=None):
        ticket = self.tickets.get(ticket_id)
        # Same guard as the SQL: only a still-unassigned MOI ticket is updated.
        if not ticket or ticket["status"] != "MOI" or ticket["technician_id"] is not None:
            return None
        ticket["technician_id"] = technician_id
        ticket["status"] = new_status
        return dict(ticket)

    def update_technician(self, ticket_id, technician_id, expected_technician_id, conn=None):
        ticket = self.tickets.get(ticket_id)
        if not ticket or ticket["technician_id"] != expected_technician_id:
            return None
        ticket["technician_id"] = technician_id
        return dict(ticket)


class FakeTechnicianRepository:
    def __init__(self, technicians, qualified=None):
        self.technicians = {
            technician["technician_id"]: dict(technician)
            for technician in technicians
        }
        # {(center_id, category_id): [qualified technician rows]}
        self.qualified = qualified or {}

    def get_by_id(self, technician_id):
        technician = self.technicians.get(technician_id)
        return dict(technician) if technician else None

    def list_qualified_for_category(self, *, center_id, category_id):
        return [dict(row) for row in self.qualified.get((center_id, category_id), [])]


class FakeTechnicianSkillRepository:
    DEFAULT_CATEGORY_NAMES = {1: "MAN_HINH", 4: "PHAN_MEM", 7: "CU"}

    def __init__(self, skills=None, category_names=None):
        self.skills = {
            (skill["technician_id"], skill["category_id"]): dict(skill)
            for skill in skills or []
        }
        self.category_names = category_names or self.DEFAULT_CATEGORY_NAMES

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
        self.skills[(technician_id, category_id)] = {
            "technician_id": technician_id,
            "category_id": category_id,
            "category_name": self.category_names.get(category_id, f"CATEGORY_{category_id}"),
            "proficiency": proficiency,
        }

    def update_proficiency(self, technician_id, category_id, proficiency):
        key = (technician_id, category_id)
        if key in self.skills:
            self.skills[key]["proficiency"] = proficiency

    def delete_skill(self, technician_id, category_id):
        return self.skills.pop((technician_id, category_id), None) is not None


class FakeIssueCategoryRepository:
    def __init__(self, categories):
        self.categories = {
            category["category_id"]: dict(category)
            for category in categories
        }

    def get_by_id(self, category_id):
        category = self.categories.get(category_id)
        return dict(category) if category else None

    def list_active(self):
        return [dict(c) for c in self.categories.values() if c["is_active"]]


class FakeTicketStatusLogRepository:
    def __init__(self):
        self.logs = []
        self.next_log_id = 1000

    def create(self, *, ticket_id, from_status, to_status, changed_by, note=None, conn=None):
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


class FakeAppointmentRepository:
    def __init__(self, appointments=None):
        self.appointments = {}
        self.next_id = 1
        for appointment in appointments or []:
            self.appointments[appointment["appointment_id"]] = dict(appointment)
            self.next_id = max(self.next_id, appointment["appointment_id"] + 1)

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
        items = [dict(a) for a in self.appointments.values() if a["center_id"] == center_id]

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

        items.sort(key=lambda item: (item["ngay_hen"], item["gio_bat_dau"]), reverse=True)
        total = len(items)
        start = (page - 1) * page_size
        return items[start:start + page_size], total

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
        return {"appointment_id": appointment_id, "is_deleted": True}

    def find_conflicts(
        self,
        *,
        technician_id,
        ngay_hen,
        gio_bat_dau,
        gio_ket_thuc,
        exclude_appointment_id=None,
    ):
        conflicts = []
        for a in self.appointments.values():
            if (
                a["technician_id"] == technician_id
                and a["ngay_hen"] == ngay_hen
                and not a["is_deleted"]
                and a["trang_thai"] in ACTIVE_APPOINTMENT_STATUSES
                and a["appointment_id"] != exclude_appointment_id
                and a["gio_bat_dau"] < gio_ket_thuc
                and a["gio_ket_thuc"] > gio_bat_dau
            ):
                conflicts.append(
                    {
                        key: a[key]
                        for key in (
                            "appointment_id", "ticket_id", "ngay_hen",
                            "gio_bat_dau", "gio_ket_thuc", "trang_thai",
                        )
                    }
                )
        return sorted(conflicts, key=lambda c: c["gio_bat_dau"])
