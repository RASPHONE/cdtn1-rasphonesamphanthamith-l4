"""Security checklist item 2 (OWASP A05 Injection) on the real database.

Free text and query values reach PostgreSQL only as bound parameters: an SQL payload is
stored as plain text or refused by validation, and never runs.
"""
from tests.bt3.conftest import login

PAYLOAD = "Đổi KTV'); DROP TABLE ticket; --"


def test_sql_in_free_text_is_stored_as_text(api, pg):
    headers = login(api, "manager2")
    response = api.patch("/api/tickets/194/assignment", headers=headers,
                         json={"technician_id": 8, "reason": PAYLOAD})
    assert response.status_code == 200, response.text
    note = pg["query"]("SELECT note FROM ticket_status_log WHERE log_id = %s",
                       (response.json()["log_id"],))[0]["note"]
    tickets = pg["query"]("SELECT count(*) AS n FROM ticket")[0]["n"]
    print(f"\n  A05 observed: stored note={note!r} · ticket rows={tickets}")
    assert note == PAYLOAD
    assert tickets == 487


def test_sql_in_a_query_value_is_refused(api, pg):
    headers = login(api, "manager2")
    response = api.get("/api/tickets/unassigned", headers=headers,
                       params={"priority": "CAO' OR '1'='1"})
    assert response.status_code == 400
    assert response.json()["details"][0]["field"] == "priority"
