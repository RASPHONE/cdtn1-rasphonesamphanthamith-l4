"""FR1 order, FR8 workload and FR9 filter on the real database (SRS §6.2 "Test case" column).

These three behaviours are computed in SQL, so the expected values come from independent
queries on the same fresh copy of the sample data.
"""
from datetime import datetime

from tests.bt3.conftest import login, observe

OPEN_UNASSIGNED = """FROM ticket WHERE center_id = 2 AND status = 'MOI' AND technician_id IS NULL
                     AND is_warranty AND NOT is_deleted"""


def test_fr1_unassigned_list_is_sorted_by_due_date(api, pg):
    response = api.get("/api/tickets/unassigned", headers=login(api, "manager2"), params={"page_size": 100})
    items = response.json()["items"]
    due = [datetime.fromisoformat(item["due_date"]) for item in items]
    expected = {row["ticket_id"] for row in pg["query"](f"SELECT ticket_id {OPEN_UNASSIGNED}")}
    observe("FR1", status=response.status_code, rows=len(items), first_due=due[0].isoformat(), last_due=due[-1].isoformat())
    assert response.status_code == 200
    assert {item["ticket_id"] for item in items} == expected
    assert due == sorted(due)          # most urgent SLA first


def test_fr8_workload_is_the_live_count_of_open_assigned_tickets(api, pg):
    headers = login(api, "manager2")

    def workloads():
        body = api.get("/api/tickets/8036/qualified-technicians", headers=headers).json()
        return {item["technician_id"]: item["workload"] for item in body["items"]}

    def counted(technician_id):
        return pg["query"]("""SELECT count(*) AS n FROM ticket WHERE technician_id = %s AND is_warranty
                              AND NOT is_deleted AND status IN ('DA_PHAN_CONG', 'DANG_XU_LY', 'CHO_LINH_KIEN')""",
                           (technician_id,))[0]["n"]

    before = workloads()
    assert before == {technician_id: counted(technician_id) for technician_id in before}
    assert api.post("/api/tickets/8036/assignment", headers=headers, json={"technician_id": 29}).status_code == 200
    after = workloads()
    observe("FR8", technician_29_before=before[29], technician_29_after=after[29], sql_after=counted(29))
    assert after[29] == before[29] + 1 == counted(29)
    assert {k: v for k, v in after.items() if k != 29} == {k: v for k, v in before.items() if k != 29}


def test_fr9_filter_returns_only_matching_tickets(api, pg):
    headers = login(api, "manager2")
    response = api.get("/api/tickets/unassigned", headers=headers,
                       params={"category_id": 1, "priority": "CAO", "page_size": 100})
    body = response.json()
    expected = pg["query"](f"SELECT count(*) AS n {OPEN_UNASSIGNED} AND category_id = 1 AND priority = 'CAO'")[0]["n"]
    unfiltered = api.get("/api/tickets/unassigned", headers=headers, params={"page_size": 100}).json()["total"]
    observe("FR9", status=response.status_code, total=body["total"], expected_by_sql=expected, unfiltered=unfiltered)
    assert response.status_code == 200
    assert 0 < body["total"] == expected < unfiltered
    assert all(item["category_id"] == 1 and item["priority"] == "CAO" for item in body["items"])
