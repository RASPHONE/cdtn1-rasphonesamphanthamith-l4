"""BT3 Test Report cases TC-01 ... TC-12 (docs/test-report.md, plan: docs/test-plan.md).

Run all:            pytest -q
Run one, show the actual result line:   pytest -s -v tests/bt3 -k tc05

Each case names its source (FR / QT / acceptance criterion) and its layer:
unit (service + in-memory fakes), API (real routes, fakes behind them),
API + PostgreSQL (real routes, services and repositories on a fresh copy of
the seeded sample, see conftest.py), system (the real scripts).
Sample-data ids used below come from data/sample/ (fixed ids, see SRS §1.5).
"""
import re
from datetime import date, datetime, timedelta

import jwt
import pytest

from src.config import Settings, get_settings
from src.errors import AppError
from src.schemas.ticket import AssignmentCreate
from src.services.ticket_assignment_service import TicketAssignmentService
from tests.bt3.conftest import ROOT, _run_script, login, observe
from tests.fakes import (
    FakeTechnicianRepository,
    FakeTechnicianSkillRepository,
    FakeTicketRepository,
    FakeTicketStatusLogRepository,
    fake_transaction,
)

MASKED = re.compile(r"^\d{3}\*{4}\d{3}$")
FULL = re.compile(r"^\d{10}$")


def log_count(pg, ticket_id):
    return pg["query"]("SELECT count(*) AS n FROM ticket_status_log WHERE ticket_id = %s", (ticket_id,))[0]["n"]


# ---------------------------------------------------------------- 1. happy path (one per implemented rule)

def test_tc01_qt08_suggests_only_qualified_technicians(api, pg):
    """TC-01 · happy path · QT-08 / FR2 / US2 AC1 · API + PostgreSQL.
    Ticket BH-008036/2026 (center 2, category 1 MAN_HINH). Expected list = technicians of
    center 2, active, proficiency >= 3 in category 1, computed by an independent SQL query."""
    expected = {
        row["technician_id"]
        for row in pg["query"](
            """SELECT t.technician_id FROM technician t
               JOIN technician_skill s ON s.technician_id = t.technician_id
               WHERE t.center_id = 2 AND t.is_active AND s.category_id = 1 AND s.proficiency >= 3"""
        )
    }
    response = api.get("/api/tickets/8036/qualified-technicians", headers=login(api, "manager2"))
    body = response.json()
    returned = {item["technician_id"] for item in body["items"]}
    observe("TC-01", status=response.status_code, returned=sorted(returned), expected_by_sql=sorted(expected),
            min_proficiency=min(item["proficiency"] for item in body["items"]))
    assert response.status_code == 200
    assert returned == expected == {8, 25, 29, 30}
    assert all(item["proficiency"] >= 3 for item in body["items"])


def test_tc02_qt07_assignment_writes_ticket_and_one_log_row(api, pg):
    """TC-02 · happy path · QT-07, QT-06, NFR5 / FR3 / US4 AC1 · API + PostgreSQL.
    Assign BH-008036/2026 (status MOI) to technician 29 (proficiency 4)."""
    before = log_count(pg, 8036)
    response = api.post("/api/tickets/8036/assignment", json={"technician_id": 29}, headers=login(api, "manager2"))
    ticket = pg["query"]("SELECT status, technician_id FROM ticket WHERE ticket_id = 8036")[0]
    last_log = pg["query"](
        "SELECT from_status, to_status FROM ticket_status_log WHERE ticket_id = 8036 ORDER BY log_id DESC LIMIT 1"
    )[0]
    after = log_count(pg, 8036)
    observe("TC-02", status=response.status_code, ticket_status=ticket["status"], technician=ticket["technician_id"],
            log_rows=f"{before}->{after}", last_log=f"{last_log['from_status']}->{last_log['to_status']}")
    assert response.status_code == 200
    assert ticket == {"status": "DA_PHAN_CONG", "technician_id": 29}
    assert after == before + 1
    assert (last_log["from_status"], last_log["to_status"]) == ("MOI", "DA_PHAN_CONG")


def test_tc03_fr7_appointment_in_free_slot_is_created(api, pg):
    """TC-03 · happy path · FR6, FR7 / US5 AC1 · API + PostgreSQL.
    Ticket BH-000194/2025 (center 2, warranty, DA_PHAN_CONG, technician 30), NHAN_MAY,
    today + 30 days, 14:00-15:00, a slot where technician 30 has no active appointment."""
    day = date.today() + timedelta(days=30)
    clash = pg["query"](
        """SELECT count(*) AS n FROM appointment WHERE technician_id = 30 AND ngay_hen = %s
           AND trang_thai IN ('DA_DAT','DA_XAC_NHAN') AND NOT is_deleted
           AND gio_bat_dau < '15:00' AND gio_ket_thuc > '14:00'""", (day,))[0]["n"]
    before = pg["query"]("SELECT count(*) AS n FROM appointment")[0]["n"]
    response = api.post("/api/appointments", headers=login(api, "manager2"), json={
        "ticket_id": 194, "loai": "NHAN_MAY", "ngay_hen": day.isoformat(),
        "gio_bat_dau": "14:00", "gio_ket_thuc": "15:00",
    })
    after = pg["query"]("SELECT count(*) AS n FROM appointment")[0]["n"]
    body = response.json()
    observe("TC-03", precondition_overlaps=clash, status=response.status_code, trang_thai=body.get("trang_thai"),
            technician=body.get("technician_id"), appointments=f"{before}->{after}")
    assert clash == 0
    assert response.status_code == 201
    assert body["trang_thai"] == "DA_XAC_NHAN" and body["technician_id"] == 30
    assert after == before + 1


def test_tc04_qt14_lists_contain_only_the_callers_center(api, pg):
    """TC-04 · happy path · QT-14 / FR1 / US1 AC1, AC3 · API + PostgreSQL.
    manager1 (center 1) and manager2 (center 2) read the unassigned list (page_size 100)."""
    lists = {}
    for user, center in (("manager1", 1), ("manager2", 2)):
        body = api.get("/api/tickets/unassigned?page_size=100", headers=login(api, user)).json()
        expected = pg["query"](
            """SELECT count(*) AS n FROM ticket WHERE center_id = %s AND status = 'MOI'
               AND technician_id IS NULL AND is_warranty AND NOT is_deleted""", (center,))[0]["n"]
        lists[user] = (body, expected, {item["center_id"] for item in body["items"]})
    ids1 = {item["ticket_id"] for item in lists["manager1"][0]["items"]}
    ids2 = {item["ticket_id"] for item in lists["manager2"][0]["items"]}
    observe("TC-04", manager1=f"total {lists['manager1'][0]['total']} (sql {lists['manager1'][1]}) centers {lists['manager1'][2]}",
            manager2=f"total {lists['manager2'][0]['total']} (sql {lists['manager2'][1]}) centers {lists['manager2'][2]}",
            shared_ids=len(ids1 & ids2))
    for user, center in (("manager1", 1), ("manager2", 2)):
        body, expected, centers = lists[user]
        assert body["total"] == expected and centers == {center}
    assert not ids1 & ids2


def test_tc05_qt15_phone_masked_for_every_non_manager_row(api, pg):
    """TC-05 · happy path · QT-15 / NFR4 (100% of phones masked for non-manager roles) · API + PostgreSQL.
    Same list read with a TECHNICIAN-role token (center 2) and with manager2's token."""
    secret = get_settings().jwt_secret
    technician_token = jwt.encode(
        {"sub": "kt025", "user_id": 25, "role": "TECHNICIAN", "center_id": 2,
         "exp": datetime.now().astimezone() + timedelta(minutes=5)}, secret, algorithm="HS256")
    as_technician = api.get("/api/tickets/unassigned?page_size=100",
                            headers={"Authorization": f"Bearer {technician_token}"}).json()["items"]
    as_manager = api.get("/api/tickets/unassigned?page_size=100", headers=login(api, "manager2")).json()["items"]
    expected = pg["query"](
        """SELECT count(*) AS n FROM ticket WHERE center_id = 2 AND status = 'MOI'
           AND technician_id IS NULL AND is_warranty AND NOT is_deleted""")[0]["n"]
    masked = sum(bool(MASKED.match(item["customer_phone"])) for item in as_technician)
    full = sum(bool(FULL.match(item["customer_phone"])) for item in as_manager)
    observe("TC-05", technician=f"{masked}/{len(as_technician)} masked (e.g. {as_technician[0]['customer_phone']})",
            manager=f"{full}/{len(as_manager)} full", rows_by_sql=expected)
    assert len(as_technician) == expected and masked == expected
    assert len(as_manager) == expected and full == expected


# ---------------------------------------------------------------- 2. boundary (two sides of one boundary)

def _assignment_service():
    """Service with in-memory data mirroring BH-008036/2026 (center 2, category 1):
    technician 25 has proficiency 3 (exactly the QT-08 threshold), technician 5 has 2."""
    ticket = {"ticket_id": 8036, "ticket_code": "BH-008036/2026", "center_id": 2, "category_id": 1,
              "status": "MOI", "technician_id": None, "is_warranty": True, "is_deleted": False}
    technicians = [{"technician_id": 25, "center_id": 2, "is_active": True},
                   {"technician_id": 5, "center_id": 2, "is_active": True}]
    skills = [{"technician_id": 25, "category_id": 1, "proficiency": 3},
              {"technician_id": 5, "category_id": 1, "proficiency": 2}]
    logs = FakeTicketStatusLogRepository()
    service = TicketAssignmentService(
        ticket_repository=FakeTicketRepository([ticket]),
        technician_repository=FakeTechnicianRepository(technicians),
        technician_skill_repository=FakeTechnicianSkillRepository(skills),
        status_log_repository=logs, transaction=fake_transaction,
    )
    return service, logs


def test_tc06_boundary_proficiency_3_is_accepted():
    """TC-06 · boundary (inside) · QT-08 proficiency >= 3 / US4 AC3 · unit (service + fakes)."""
    service, logs = _assignment_service()
    result = service.assign_technician(center_id=2, ticket_id=8036,
                                       payload=AssignmentCreate(technician_id=25), changed_by=2)
    observe("TC-06", proficiency=3, status=result["status"], technician=result["technician_id"], log_rows=len(logs.logs))
    assert result["status"] == "DA_PHAN_CONG" and result["technician_id"] == 25
    assert len(logs.logs) == 1


def test_tc07_boundary_proficiency_2_is_rejected():
    """TC-07 · boundary (outside) · QT-08 proficiency >= 3 / US4 AC3 · unit (service + fakes)."""
    service, logs = _assignment_service()
    with pytest.raises(AppError) as error:
        service.assign_technician(center_id=2, ticket_id=8036,
                                  payload=AssignmentCreate(technician_id=5), changed_by=2)
    ticket = service.ticket_repo.get_by_id(8036)
    observe("TC-07", proficiency=2, error=error.value.code, ticket_status=ticket["status"],
            technician=ticket["technician_id"], log_rows=len(logs.logs))
    assert error.value.code == "technician_not_qualified"
    assert ticket["status"] == "MOI" and ticket["technician_id"] is None
    assert logs.logs == []


# ---------------------------------------------------------------- 3. invalid data (status AND message)

def test_tc08_malformed_json_body_is_rejected_with_a_clear_message(client):
    """TC-08 · invalid data · C7 (clear rejection, no raw library error) / API contract §1 · API (fakes).
    POST /api/appointments with a truncated JSON body."""
    token = client.post("/api/auth/login", json={"username": "manager1", "password": "manager123"}).json()["access_token"]
    response = client.post("/api/appointments", content=b'{"ticket_id": 103, "loai": "NHAN_MAY"',
                           headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    body = response.json()
    observe("TC-08", status=response.status_code, error=body.get("error"), message=repr(body.get("message")),
            fields=[d["field"] for d in body.get("details", [])])
    assert response.status_code == 400 and body["error"] == "bad_request"
    assert body["message"] == "Request body is not valid JSON."
    assert [d["field"] for d in body["details"]] == ["body"]


def test_tc09_reassigning_to_the_current_technician_is_rejected(api, pg):
    """TC-09 · invalid data · QT-07 ("changing the technician must be logged with a reason":
    no change, so nothing to log) / FR5 · API + PostgreSQL.
    BH-000194/2025 is assigned to technician 30; PATCH asks for technician 30 again."""
    before = log_count(pg, 194)
    response = api.patch("/api/tickets/194/assignment", headers=login(api, "manager2"),
                         json={"technician_id": 30, "reason": "Khách yêu cầu giữ nguyên KTV"})
    after = log_count(pg, 194)
    body = response.json()
    observe("TC-09", status=response.status_code, error=body.get("error"), message=repr(body.get("message")),
            log_rows=f"{before}->{after}")
    assert response.status_code == 422 and body["error"] == "same_technician"
    assert body["message"] == "The ticket is already assigned to this technician."
    assert after == before


# ---------------------------------------------------------------- 4. security (OWASP A01, A07)

def test_tc10_a01_manager_cannot_change_another_centers_appointment(api, pg):
    """TC-10 · security · OWASP A01 / QT-14 / NFR3 · API + PostgreSQL.
    manager1 (center 1) moves appointment 900004 (center 2, 09:00-10:00) to 10:00-11:00."""
    row = "SELECT center_id, gio_bat_dau::text AS start, gio_ket_thuc::text AS end FROM appointment WHERE appointment_id = 900004"
    before = pg["query"](row)[0]
    response = api.patch("/api/appointments/900004", headers=login(api, "manager1"),
                         json={"gio_bat_dau": "10:00", "gio_ket_thuc": "11:00"})
    after = pg["query"](row)[0]
    observe("TC-10", status=response.status_code, error=response.json().get("error"),
            row_before=f"{before['start']}-{before['end']}", row_after=f"{after['start']}-{after['end']}")
    assert before["center_id"] == 2
    assert response.status_code == 403 and response.json()["error"] == "cross_center_access"
    assert after == before


# Secrets that anyone can read in the public repository (tag v0.2 and its history).
PUBLISHED_SECRETS = {
    "v0.2 .env.example": "change_me_to_a_long_random_string_32_chars_min",
    "v0.2 config.py default": "dev_only_change_me_in_env",
}


@pytest.mark.filterwarnings("ignore::jwt.warnings.InsecureKeyLengthWarning")  # the attacker's short key is the point
def test_tc11_a07_token_signed_with_a_published_secret_is_rejected(client, monkeypatch):
    """TC-11 · security · OWASP A07 (authentication) / A02 (misconfiguration) / QT-14 · API (fakes).
    The API is configured exactly as README and Docker do it (`cp .env.example .env`); an attacker
    signs a manager token for center 1 with each secret that is published in the repository."""
    monkeypatch.delenv("JWT_SECRET", raising=False)
    readme_settings = Settings(_env_file=ROOT / ".env.example")
    monkeypatch.setattr("src.security.get_settings", lambda: readme_settings)
    candidates = dict(PUBLISHED_SECRETS)
    sample = next((line.split("=", 1)[1].strip() for line in (ROOT / ".env.example").read_text().splitlines()
                   if line.startswith("JWT_SECRET=")), "")
    if sample:
        candidates[".env.example JWT_SECRET"] = sample
    results = {}
    for label, secret in candidates.items():
        if not secret:
            continue
        forged = jwt.encode({"sub": "attacker", "user_id": 999, "role": "CENTER_MANAGER", "center_id": 1,
                             "exp": datetime.now().astimezone() + timedelta(hours=1)}, secret, algorithm="HS256")
        results[label] = client.get("/api/tickets/unassigned", headers={"Authorization": f"Bearer {forged}"}).status_code
    observe("TC-11", **{label.replace(" ", "_"): code for label, code in results.items()})
    assert set(results.values()) == {401}


# ---------------------------------------------------------------- 5. reproducibility

def test_tc12_second_migrate_and_seed_change_nothing(pg):
    """TC-12 · reproducibility · BT2 C5 / BT3 C8 · system (the real scripts on a seeded database).
    The test database was already migrated and seeded once; run both commands again."""
    tables = ["issue_category", "technician", "technician_skill", "ticket", "ticket_status_log", "appointment"]
    count_sql = " UNION ALL ".join(f"SELECT '{t}' AS t, count(*) AS n FROM {t}" for t in tables)
    before = {row["t"]: row["n"] for row in pg["query"](count_sql)}
    migrate_out = _run_script("migrate.py", pg["db_name"])
    seed_out = _run_script("seed.py", pg["db_name"])
    after = {row["t"]: row["n"] for row in pg["query"](count_sql)}
    added = dict(re.findall(r"^\s+(\w+)\s+\+(\d+)", seed_out, re.M))
    observe("TC-12", migrate=migrate_out.strip().splitlines()[-1], added=added, totals=after)
    migrations = len(list((ROOT / "db" / "migrations").glob("[0-9][0-9][0-9]_*.sql")))
    assert f"0 applied, {migrations} already up to date" in migrate_out
    assert added and set(added.values()) == {"0"}
    assert after == before
