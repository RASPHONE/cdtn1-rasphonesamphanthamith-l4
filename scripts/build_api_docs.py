"""Build docs/api-docs/README.md (API reference, BT3 TP6 / SE S1) and docs/api-docs/openapi.json.

Each endpoint gets the 7 required items: method + path, business purpose, authentication,
parameters/body, success response, error table, limits/notes. The examples are REAL: the
script calls a running API (default http://localhost:8000) on the demo data and pastes the
request and the response it got.

Checks before writing (the script stops if one fails):
  - the documented endpoints are exactly the routes the application serves;
  - every documented error code exists in src/errors.py with the documented HTTP status;
  - every example call returned the status the table says.

Usage (system running, e.g. `docker compose up -d`; best on fresh data: `down -v` first):
    python scripts/build_api_docs.py                  # or API=http://host:port python ...
The run changes demo data (assigns ticket 8036, creates then deletes an appointment and a
skill), like a user would.
"""
import json
import logging
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("JWT_SECRET", "docs-build-only-" + "x" * 32)  # only to import the app

from src.errors import HTTP_BY_CODE  # noqa: E402
from src.main import app  # noqa: E402

logging.getLogger("httpx").setLevel(logging.WARNING)   # the app sets INFO; keep the output to the result line

API = os.environ.get("API", "http://localhost:8000").rstrip("/")
OUT = ROOT / "docs" / "api-docs"
DAY = (date.today() + timedelta(days=40)).isoformat()      # a free future day for the examples

AUTH = "Bearer token from `POST /api/auth/login` (role `CENTER_MANAGER`). The caller's center comes from the token (QT-14)."
COMMON = [(401, "unauthorized", "token missing, malformed, expired or signed with another key"),
          (503, "database_unavailable", "PostgreSQL cannot be reached"),
          (500, "internal_error", "unexpected error; the body carries a `request_id`, no internal details")]
PAGING = [("page", "query", "int", "no", "≥ 1, default 1"), ("page_size", "query", "int", "no", "1–100, default 20")]

# ----------------------------------------------------------------------------- endpoints
# example: list of calls; each call = dict(method, path, json/params, expect, title).
# Paths may use {appointment_id} / {free_category}: filled from earlier responses.
E = []


def endpoint(no, method, path, purpose, trace, params, body, success, errors, notes, examples, auth=AUTH, common=None):
    E.append(dict(no=no, method=method, path=path, purpose=purpose, trace=trace, params=params, body=body,
                  success=success, errors=errors + (COMMON if common is None else common), notes=notes,
                  examples=examples, auth=auth))


endpoint(1, "GET", "/health", "Shows that the API runs and whether it can reach the database (used by Docker health checks and the Deployment Guide).",
         "infrastructure", [], [], "200 — `status` is always `ok` while the API answers; `database` is `up` or `down`.",
         [], "No business data; no authentication so that health checks need no token. A database outage does not make it fail: it answers 200 with `\"database\": \"down\"`.",
         [dict(method="GET", path="/health", expect=200)], auth="None.", common=COMMON[2:])
endpoint(2, "POST", "/api/auth/login", "Demo login: checks a username and password against table `app_user` (PBKDF2 hashes) and returns a signed token carrying the user's role and center.",
         "US14 · FR12", [], [("username", "string", "yes", "demo account, e.g. `manager1`, `manager2`"), ("password", "string", "yes", "the demo password (`DEMO_PASSWORD`, default `manager123`)")],
         "200 — `access_token` (HS256, expires after `ACCESS_TOKEN_EXPIRE_MINUTES`), `token_type`, `role`, `center_id`.",
         [(400, "bad_request", "field missing or body not JSON"), (401, "invalid_credentials", "unknown user or wrong password — same message for both")],
         "Demo authentication for the prototype, not a production identity provider. The token is kept in the browser's localStorage by the UI.",
         [dict(method="POST", path="/api/auth/login", json={"username": "manager2", "password": "wrong-password"}, expect=401, title="wrong password"),
          dict(method="POST", path="/api/auth/login", json={"username": "manager2", "password": "manager123"}, expect=200, auth=False)],
         auth="None (this endpoint issues the token).", common=COMMON[1:])
endpoint(3, "GET", "/api/issue-categories", "Lists the active issue categories for the M1 filter, read from the database so a new category needs no code change (NFR7).",
         "US8 · FR9", [], [], "200 — array of `{category_id, category_name, default_priority}`, active categories only.",
         [], "Read-only.", [dict(method="GET", path="/api/issue-categories", expect=200)])
endpoint(4, "GET", "/api/tickets/unassigned", "Lists the caller's center's open warranty tickets that have no technician yet, most urgent SLA first (screen M1).",
         "US1, US8 · FR1, FR9 · QT-14, QT-15", PAGING + [("category_id", "query", "int", "no", "≥ 1"), ("priority", "query", "enum", "no", "`CAO`, `TRUNG_BINH`, `THAP`")], [],
         "200 — `{page, page_size, total, items[]}`; items sorted by `due_date` ascending.",
         [(400, "bad_request", "invalid `page`, `page_size`, `category_id` or `priority` (`details` names the field)")],
         "Fixed server-side filter: status `MOI`, no technician, warranty, not deleted, caller's center. `customer_phone` is masked (`090****567`) for every role except `CENTER_MANAGER` / `BOARD_OF_DIRECTORS` (QT-15).",
         [dict(method="GET", path="/api/tickets/unassigned", params={"priority": "URGENT"}, expect=400, title="unknown priority"),
          dict(method="GET", path="/api/tickets/unassigned", params={"page_size": 2}, expect=200)])
endpoint(5, "GET", "/api/tickets/{ticket_id}", "Returns one ticket's summary for the M2 and M3 headers.",
         "US2, US4, US5 · FR2, FR6 · QT-14, QT-15", [("ticket_id", "path", "int", "yes", "")], [],
         "200 — the list fields plus `status`, `technician_id`, `technician_ho_ten`, `closed_at`.",
         [(400, "bad_request", "`ticket_id` not an integer"), (403, "cross_center_access", "ticket of another center"), (404, "ticket_not_found", "no such ticket, or soft-deleted")],
         "Same phone masking as endpoint 4.",
         [dict(method="GET", path="/api/tickets/8001", expect=403, title="ticket of center 1, caller in center 2"),
          dict(method="GET", path="/api/tickets/8036", expect=200)])
endpoint(6, "GET", "/api/tickets/{ticket_id}/qualified-technicians", "Suggests only the technicians allowed to take the ticket (same center, active, proficiency ≥ 3 in its category) with their current workload (M2).",
         "US2, US3 · FR2, FR8 · QT-08", [("ticket_id", "path", "int", "yes", "")], [],
         "200 — `{ticket_id, items[]}`, each item `technician_id, technician_code, ho_ten, level, proficiency, workload`.",
         [(400, "bad_request", "`ticket_id` not an integer"), (403, "cross_center_access", "ticket of another center"), (404, "ticket_not_found", "no such ticket"),
          (422, "ticket_not_assignable", "not a warranty ticket, or closed")],
         "`workload` = tickets the technician holds in `DA_PHAN_CONG`, `DANG_XU_LY` or `CHO_LINH_KIEN`, counted at query time (never stored).",
         [dict(method="GET", path="/api/tickets/999999/qualified-technicians", expect=404, title="unknown ticket"),
          dict(method="GET", path="/api/tickets/8036/qualified-technicians", expect=200)])
endpoint(7, "POST", "/api/tickets/{ticket_id}/assignment", "First assignment of a technician to a new ticket; writes the ticket and its status-log row in one transaction.",
         "US4 · FR3, FR4 · QT-06, QT-07, QT-08, NFR5", [("ticket_id", "path", "int", "yes", "")], [("technician_id", "int", "yes", "eligible under QT-08")],
         "200 — `{ticket_id, technician_id, status: \"DA_PHAN_CONG\", log_id}`.",
         [(400, "bad_request", "field missing or malformed"), (403, "cross_center_access", "ticket of another center"),
          (404, "ticket_not_found", "no such ticket"), (404, "technician_not_found", "no such technician"),
          (422, "technician_not_qualified", "QT-08 not met (other center, inactive, or proficiency < 3)"),
          (422, "ticket_not_assignable", "not `MOI`, already assigned (also by a concurrent request), not warranty, or closed")],
         "Guarded UPDATE: of two simultaneous assignments only one succeeds; the other gets 422 and writes nothing.",
         [dict(method="POST", path="/api/tickets/8036/assignment", json={"technician_id": 5}, expect=422, title="technician 5 has proficiency 2"),
          dict(method="POST", path="/api/tickets/8036/assignment", json={"technician_id": 29}, expect=200)])
endpoint(8, "PATCH", "/api/tickets/{ticket_id}/assignment", "Reassigns an assigned ticket to another eligible technician; the reason is mandatory and logged.",
         "US4 · FR5 · QT-07, QT-08", [("ticket_id", "path", "int", "yes", "")],
         [("technician_id", "int", "yes", "eligible under QT-08, not the current technician"), ("reason", "string", "yes", "5–255 characters after trimming")],
         "200 — same shape as endpoint 7, with the new `log_id`.",
         [(400, "bad_request", "field malformed"), (403, "cross_center_access", "ticket of another center"),
          (404, "ticket_not_found", "no such ticket"), (404, "technician_not_found", "no such technician"),
          (422, "reason_required", "reason omitted, blank, shorter than 5 or longer than 255"),
          (422, "same_technician", "the requested technician already holds the ticket (BUG-012)"),
          (422, "technician_not_qualified", "QT-08 not met"),
          (422, "ticket_not_assignable", "ticket not assigned, closed, or changed by someone else meanwhile")],
         "Nothing is written when the request is refused.",
         [dict(method="PATCH", path="/api/tickets/8036/assignment", json={"technician_id": 30}, expect=422, title="no reason"),
          dict(method="PATCH", path="/api/tickets/8036/assignment", json={"technician_id": 30, "reason": "Khách yêu cầu đổi KTV"}, expect=200)])
endpoint(9, "GET", "/api/appointments/conflicts", "Checks, before saving, whether a time slot overlaps the technician's active appointments (warning on M3).",
         "US6 · FR7", [("technician_id", "query", "int", "yes", "technician of the caller's center"), ("ngay_hen", "query", "date", "yes", "YYYY-MM-DD"),
                       ("gio_bat_dau", "query", "time", "yes", "HH:MM"), ("gio_ket_thuc", "query", "time", "yes", "HH:MM, after the start"),
                       ("exclude_appointment_id", "query", "int", "no", "the appointment being edited")], [],
         "200 — `{conflicts: [...]}`; empty array when the slot is free.",
         [(400, "bad_request", "parameter missing or malformed"), (403, "cross_center_access", "technician of another center"),
          (404, "technician_not_found", "no such technician"), (422, "invalid_time_range", "end not after start (CON-01)")],
         "Advisory only: saving (endpoints 10 and 13) repeats the check and is authoritative. Slots that only touch (09:00–10:00, 10:00–11:00) do not conflict.",
         [dict(method="GET", path="/api/appointments/conflicts", params={"technician_id": 30, "ngay_hen": DAY, "gio_bat_dau": "15:00", "gio_ket_thuc": "14:00"}, expect=422, title="end before start"),
          dict(method="GET", path="/api/appointments/conflicts", params={"technician_id": 30, "ngay_hen": DAY, "gio_bat_dau": "14:00", "gio_ket_thuc": "15:00"}, expect=200)])
endpoint(10, "POST", "/api/appointments", "Books a device hand-over or receipt appointment for an assigned ticket; refuses a slot that overlaps the technician's active appointments.",
         "US5, US6 · FR6, FR7", [],
         [("ticket_id", "int", "yes", "assigned warranty ticket of the caller's center"), ("loai", "enum", "yes", "`NHAN_MAY` or `GIAO_MAY`"),
          ("ngay_hen", "date", "yes", "with the start time, strictly in the future (APP_TIMEZONE)"), ("gio_bat_dau", "time", "yes", "HH:MM"), ("gio_ket_thuc", "time", "yes", "HH:MM, after the start")],
         "201 — the appointment: `trang_thai` is `DA_XAC_NHAN`; `technician_id` and `center_id` are taken from the ticket.",
         [(400, "bad_request", "field missing or malformed (`details` lists every field)"), (403, "cross_center_access", "ticket of another center"),
          (404, "ticket_not_found", "no such ticket"), (409, "appointment_conflict", "overlap with an active appointment; body adds `conflicts[]`"),
          (422, "ticket_not_assignable", "ticket without technician, not warranty, or closed"),
          (422, "appointment_type_deferred", "`KIEM_TRA_TAI_CHO` (not available in this version)"),
          (422, "appointment_in_past", "start not in the future"), (422, "invalid_time_range", "end not after start")],
         "Active = `DA_DAT` or `DA_XAC_NHAN` and not deleted. Two submits for the same free slot at the same instant are not locked (accepted: one manager per center).",
         [dict(method="POST", path="/api/appointments", json={"ticket_id": 8036, "loai": "NHAN_MAY", "ngay_hen": DAY, "gio_bat_dau": "14:00", "gio_ket_thuc": "15:00"}, expect=201, save="appointment"),
          dict(method="POST", path="/api/appointments", json={"ticket_id": 8036, "loai": "GIAO_MAY", "ngay_hen": DAY, "gio_bat_dau": "14:30", "gio_ket_thuc": "15:30"}, expect=409, title="overlaps the appointment just created")])
endpoint(11, "GET", "/api/appointments", "Lists the caller's center's appointments, newest first, with ticket code and technician name for display (M3).",
         "US5, US13 · FR6, FR11", PAGING + [("technician_id", "query", "int", "no", ""), ("ticket_id", "query", "int", "no", ""), ("ngay_hen", "query", "date", "no", ""),
                                             ("trang_thai", "query", "enum", "no", "CON-03 values"), ("include_deleted", "query", "bool", "no", "default `false`")], [],
         "200 — `{page, page_size, total, items[]}` ordered by `ngay_hen`, `gio_bat_dau` descending.",
         [(400, "bad_request", "invalid paging or filter value")],
         "Soft-deleted appointments are hidden unless `include_deleted=true`. There is no center parameter: only the caller's center is listed.",
         [dict(method="GET", path="/api/appointments", params={"ticket_id": 8036}, expect=200)])
endpoint(12, "GET", "/api/appointments/{appointment_id}", "Returns one appointment.",
         "US5, US13 · FR6, FR11", [("appointment_id", "path", "int", "yes", "")], [], "200 — the appointment.",
         [(400, "bad_request", "`appointment_id` not an integer"), (403, "cross_center_access", "appointment of another center"), (404, "appointment_not_found", "no such appointment, or soft-deleted")],
         "Read-only.",
         [dict(method="GET", path="/api/appointments/999999", expect=404, title="unknown id"),
          dict(method="GET", path="/api/appointments/{appointment}", expect=200)])
endpoint(13, "PATCH", "/api/appointments/{appointment_id}", "Changes an appointment's type, day or time, or confirms it; the overlap check runs again.",
         "US5, US6 · FR6, FR7", [("appointment_id", "path", "int", "yes", "")],
         [("loai", "enum", "no", "as endpoint 10"), ("ngay_hen", "date", "no", "future"), ("gio_bat_dau", "time", "no", ""), ("gio_ket_thuc", "time", "no", "after the start"),
          ("trang_thai", "enum", "no", "only `DA_XAC_NHAN` in this version")],
         "200 — the updated appointment.",
         [(400, "bad_request", "field malformed, or `trang_thai` other than `DA_XAC_NHAN`"), (403, "cross_center_access", "appointment of another center"),
          (404, "appointment_not_found", "no such appointment, or soft-deleted"), (409, "appointment_conflict", "new slot overlaps (the appointment itself excluded)"),
          (422, "appointment_completed_cannot_update", "appointment already `HOAN_TAT`"), (422, "appointment_type_deferred", "`KIEM_TRA_TAI_CHO`"),
          (422, "appointment_in_past", "new start not in the future"), (422, "invalid_time_range", "end not after start")],
         "Only the fields sent are changed.",
         [dict(method="PATCH", path="/api/appointments/{appointment}", json={"ngay_hen": "2020-01-06"}, expect=422, title="day in the past"),
          dict(method="PATCH", path="/api/appointments/{appointment}", json={"gio_bat_dau": "15:00", "gio_ket_thuc": "16:00"}, expect=200)])
endpoint(14, "DELETE", "/api/appointments/{appointment_id}", "Soft-deletes an appointment: the row stays for traceability, flagged `is_deleted`.",
         "US13 · FR11", [("appointment_id", "path", "int", "yes", "")], [], "200 — `{appointment_id, is_deleted: true}`.",
         [(400, "bad_request", "`appointment_id` not an integer"), (403, "cross_center_access", "appointment of another center"), (404, "appointment_not_found", "no such appointment, or already deleted"),
          (422, "appointment_completed_cannot_delete", "appointment already `HOAN_TAT`")],
         "A deleted appointment no longer counts in conflict checks.",
         [dict(method="DELETE", path="/api/appointments/{appointment}", expect=200),
          dict(method="DELETE", path="/api/appointments/{appointment}", expect=404, title="the same appointment again")])
endpoint(15, "GET", "/api/technicians/{technician_id}/skills", "Lists one technician's skills (issue category + proficiency 1–5).",
         "US12 · FR10", [("technician_id", "path", "int", "yes", "")], [], "200 — `{technician_id, items[]}`, each `technician_id, category_id, category_name, proficiency`.",
         [(400, "bad_request", "`technician_id` not an integer"), (403, "cross_center_access", "technician of another center"), (404, "technician_not_found", "no such technician")],
         "API only; no screen in this version.",
         [dict(method="GET", path="/api/technicians/1/skills", expect=403, title="technician of center 1"),
          dict(method="GET", path="/api/technicians/30/skills", expect=200, save="skills")])
endpoint(16, "POST", "/api/technicians/{technician_id}/skills", "Adds a skill to a technician.",
         "US12 · FR10 · QT-08 (input data)", [("technician_id", "path", "int", "yes", "")],
         [("category_id", "int", "yes", "existing, active category"), ("proficiency", "int", "yes", "1–5 (CON-04)")],
         "201 — the created skill.",
         [(400, "bad_request", "field missing or malformed"), (403, "cross_center_access", "technician of another center"),
          (404, "technician_not_found", "no such technician"), (404, "category_not_found", "no such category"),
          (409, "skill_already_exists", "the technician already has this category"),
          (422, "proficiency_out_of_range", "not between 1 and 5"), (422, "category_inactive", "category not active")],
         "The new skill counts at once in endpoint 6 (eligibility).",
         [dict(method="POST", path="/api/technicians/30/skills", json={"category_id": "{free_category}", "proficiency": 6}, expect=422, title="proficiency 6"),
          dict(method="POST", path="/api/technicians/30/skills", json={"category_id": "{free_category}", "proficiency": 4}, expect=201)])
endpoint(17, "GET", "/api/technicians/{technician_id}/skills/{category_id}", "Returns one skill of a technician.",
         "US12 · FR10", [("technician_id", "path", "int", "yes", ""), ("category_id", "path", "int", "yes", "")], [], "200 — the skill.",
         [(400, "bad_request", "`technician_id` or `category_id` not an integer"), (403, "cross_center_access", "technician of another center"), (404, "technician_not_found", "no such technician"), (404, "skill_not_found", "the technician has no skill in this category")],
         "Read-only.", [dict(method="GET", path="/api/technicians/30/skills/{free_category}", expect=200)])
endpoint(18, "PATCH", "/api/technicians/{technician_id}/skills/{category_id}", "Changes the proficiency of one skill.",
         "US12 · FR10", [("technician_id", "path", "int", "yes", ""), ("category_id", "path", "int", "yes", "")], [("proficiency", "int", "yes", "1–5 (CON-04)")],
         "200 — the updated skill.",
         [(400, "bad_request", "field missing or malformed"), (403, "cross_center_access", "technician of another center"),
          (404, "technician_not_found", "no such technician"), (404, "skill_not_found", "no such skill"), (422, "proficiency_out_of_range", "not between 1 and 5")],
         "Lowering a proficiency below 3 removes the technician from future suggestions for that category; existing assignments are not changed.",
         [dict(method="PATCH", path="/api/technicians/30/skills/{free_category}", json={"proficiency": 5}, expect=200)])
endpoint(19, "DELETE", "/api/technicians/{technician_id}/skills/{category_id}", "Removes one skill of a technician.",
         "US12 · FR10", [("technician_id", "path", "int", "yes", ""), ("category_id", "path", "int", "yes", "")], [], "204 — no body.",
         [(400, "bad_request", "`technician_id` or `category_id` not an integer"), (403, "cross_center_access", "technician of another center"), (404, "technician_not_found", "no such technician"), (404, "skill_not_found", "no such skill")],
         "Hard delete: a skill is reference data, not a record QT-13 protects.",
         [dict(method="DELETE", path="/api/technicians/30/skills/{free_category}", expect=204),
          dict(method="DELETE", path="/api/technicians/30/skills/{free_category}", expect=404, title="the same skill again")])


# ----------------------------------------------------------------------------- checks
def status_of(success: str) -> int:
    return int(success.split()[0])


def check_routes_and_codes():
    spec = app.openapi()
    served = {(m.upper(), p) for p, ops in spec["paths"].items() for m in ops}
    documented = {(e["method"], e["path"]) for e in E}
    if served != documented:
        sys.exit(f"Routes and docs differ.\n  not documented: {served - documented}\n  documented but not served: {documented - served}")
    for e in E:
        where = f"{e['method']} {e['path']}"
        responses = spec["paths"][e["path"]][e["method"].lower()]["responses"]
        for status, code, _ in e["errors"]:
            if HTTP_BY_CODE.get(code) != status:
                sys.exit(f"{where}: {code} documented as {status}, src/errors.py says {HTTP_BY_CODE.get(code)}")
        if ("400" in responses) != any(status == 400 for status, _, _ in e["errors"]):
            sys.exit(f"{where}: the code accepts input that can be invalid (400) but the docs do not say so, or the reverse")
        success = [code for code in responses if code.startswith("2")]
        if success != [str(status_of(e["success"]))]:
            sys.exit(f"{where}: success documented as {status_of(e['success'])}, the route answers {success}")
        allowed = {status_of(e["success"])} | {status for status, _, _ in e["errors"]}
        for call in e["examples"]:
            if call["expect"] not in allowed:
                sys.exit(f"{where}: an example expects {call['expect']}, which the docs do not list")


# ----------------------------------------------------------------------------- live run
def fill(value, state):
    if isinstance(value, str):
        for key, val in state.items():
            value = value.replace("{" + key + "}", str(val))
        return int(value) if value.isdigit() else value
    if isinstance(value, dict):
        return {k: fill(v, state) for k, v in value.items()}
    return value


def shorten(body):
    """Long lists are cut in the docs; the last entry says how many items were left out."""
    if isinstance(body, dict) and isinstance(body.get("items"), list) and len(body["items"]) > 2:
        return {**body, "items": body["items"][:2] + [f"… {len(body['items']) - 2} more items"]}
    if isinstance(body, list) and len(body) > 3:
        return body[:3] + [f"… {len(body) - 3} more items"]
    if isinstance(body, dict) and "access_token" in body:
        return {**body, "access_token": body["access_token"][:16] + "…(truncated)"}
    return body


def run_examples():
    client = httpx.Client(base_url=API, timeout=15)
    token = client.post("/api/auth/login", json={"username": "manager2", "password": os.environ.get("DEMO_PASSWORD", "manager123")})
    if token.status_code != 200:
        sys.exit(f"Login failed at {API}: {token.status_code} {token.text}")
    headers = {"Authorization": f"Bearer {token.json()['access_token']}"}
    owned = {s["category_id"] for s in client.get("/api/technicians/30/skills", headers=headers).json()["items"]}
    categories = [c["category_id"] for c in client.get("/api/issue-categories", headers=headers).json()]
    state = {"free_category": next(c for c in categories if c not in owned)}
    for e in E:
        for call in e["examples"]:
            path = fill(call["path"], state)
            sent = fill(call["json"], state) if "json" in call else None
            authenticated = call.get("auth", e["auth"] == AUTH)
            response = client.request(call["method"], path, json=sent, params=call.get("params"),
                                      headers=headers if authenticated else None)
            if response.status_code != call["expect"]:
                sys.exit(f"{call['method']} {path}: expected {call['expect']}, got {response.status_code} {response.text[:300]}")
            body = response.json() if response.content else None
            if call.get("save") == "appointment":
                state["appointment"] = body["appointment_id"]
            call["result"] = dict(path=path, status=response.status_code, body=body, sent=sent, authenticated=authenticated)


# ----------------------------------------------------------------------------- output
def table(header, rows):
    if not rows:
        return "None.\n"
    out = "| " + " | ".join(header) + " |\n|" + "---|" * len(header) + "\n"
    return out + "".join("| " + " | ".join(str(c) for c in row) + " |\n" for row in rows)


def request_text(call):
    r = call["result"]
    query = ("?" + "&".join(f"{k}={v}" for k, v in call["params"].items())) if call.get("params") else ""
    lines = [f"{call['method']} {r['path']}{query}"]
    if r["authenticated"]:
        lines.append("Authorization: Bearer <access_token of manager2, center 2>")
    if r["sent"] is not None:
        lines += ["Content-Type: application/json", "", json.dumps(r["sent"], ensure_ascii=False)]
    return "\n".join(lines)


def render():
    lines = [
        "# API reference — L4 Technician Assignment & Appointment Scheduling (v1.0)\n",
        "*Generated by `scripts/build_api_docs.py`: the descriptions are written in that script, and every example is a real request and the response a running "
        f"system returned (demo data, {date.today().strftime('%d/%m/%Y')}). The script refuses to write this file when the documented endpoints differ from the routes "
        "the code serves, when an error code's HTTP status differs from `src/errors.py`, or when an example call returns another status than documented.*\n",
        "Machine-readable version: [`openapi.json`](openapi.json) — the specification the API serves at `/openapi.json` (interactive page: `/docs`), "
        "with the error codes of each endpoint and the examples below added.\n",
        "## Common rules\n",
        "- Base URL `http://localhost:8000` (Docker or native). JSON in and out; dates `YYYY-MM-DD`, times `HH:MM` in requests and `HH:MM:SS` in responses.",
        "- **Authentication:** `Authorization: Bearer <access_token>` on every endpoint except 1 and 2. Tokens are HS256, expire after "
        "`ACCESS_TOKEN_EXPIRE_MINUTES` (default 60), and must carry `exp`, `sub`, `user_id`, `role`, `center_id`. Demo accounts: `manager1` (center 1), "
        "`manager2` (center 2); password `DEMO_PASSWORD` (default `manager123`). The examples use `manager2`.",
        "- **Center scoping (QT-14):** the center always comes from the token. Lists contain only the caller's center; addressing a record of another "
        "center gives `403 cross_center_access`.",
        "- **Errors** always use `{\"error\": \"<code>\", \"message\": \"<text>\"}`, plus `details: [{field, message}]` for invalid input, `conflicts: [...]` "
        "for 409, and `request_id` for 500. No stack trace, SQL, table name or connection string is ever returned. Unknown path → `404 not_found`; "
        "method not allowed → `405 method_not_allowed`.",
        "- **Every protected endpoint** can also answer `401 unauthorized`, `503 database_unavailable` and `500 internal_error`; they are repeated in each table.\n",
        "Trying it from a terminal (bash):\n",
        "```bash\n"
        "TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login -H 'Content-Type: application/json' \\\n"
        "  -d '{\"username\": \"manager2\", \"password\": \"manager123\"}' | python3 -c 'import sys, json; print(json.load(sys.stdin)[\"access_token\"])')\n"
        "curl -s 'http://localhost:8000/api/tickets/unassigned?page_size=2' -H \"Authorization: Bearer $TOKEN\"\n"
        "```\n",
        "## Endpoints\n",
        table(["#", "Method", "Path", "Requirement"], [(e["no"], e["method"], f"[`{e['path']}`](#ep-{e['no']})", e["trace"]) for e in E]),
    ]
    for e in E:
        lines += [
            f'<a id="ep-{e["no"]}"></a>\n',
            f"## {e['no']}. `{e['method']} {e['path']}`\n",
            f"**Purpose** — {e['purpose']} *({e['trace']})*\n",
            f"**Authentication** — {e['auth']}\n",
            "**Parameters**\n", table(["Name", "In", "Type", "Required", "Rule"], e["params"]),
            "**Request body**\n", table(["Field", "Type", "Required", "Rule"], e["body"]),
            f"**Success** — {e['success']}\n",
            "**Errors**\n", table(["HTTP", "error", "When"], [(s, f"`{c}`", w) for s, c, w in e["errors"]]),
            f"**Limits and notes** — {e['notes']}\n",
            "**Real example" + ("s" if len(e["examples"]) > 1 else "") + "**\n",
        ]
        for call in e["examples"]:
            r = call["result"]
            title = f" — {call['title']}" if call.get("title") else ""
            lines += [f"*Request{title}*\n", "```http\n" + request_text(call) + "\n```\n"]
            if r["body"] is None:
                lines.append(f"*Response — HTTP {r['status']}, no body*\n")
            else:
                lines += [f"*Response — HTTP {r['status']}*\n",
                          "```json\n" + json.dumps(shorten(r["body"]), ensure_ascii=False, indent=2) + "\n```\n"]
    return "\n".join(lines)


def enriched_openapi():
    """The served specification plus each endpoint's error codes and the real examples."""
    spec = json.loads(json.dumps(app.openapi()))
    error_ref = {"$ref": "#/components/schemas/ErrorResponse"}
    for e in E:
        operation = spec["paths"][e["path"]][e["method"].lower()]
        operation["summary"] = f"{e['no']}. {e['purpose'].split('.')[0]}"
        operation["description"] = f"{e['purpose']}\n\nRequirement: {e['trace']}.\n\n{e['notes']}"
        responses = operation["responses"]
        by_status = {}
        for status, code, when in e["errors"]:
            by_status.setdefault(str(status), []).append(f"`{code}` — {when}")
        for status, items in by_status.items():
            responses[status] = {"description": "; ".join(items),
                                 "content": {"application/json": {"schema": error_ref}}}
        for i, call in enumerate(e["examples"], 1):
            r = call["result"]
            name = call.get("title") or "success"
            if r["body"] is not None:
                content = responses[str(r["status"])].setdefault("content", {}).setdefault("application/json", {})
                content.setdefault("examples", {})[f"example{i}"] = {"summary": name, "value": shorten(r["body"])}
            if r["sent"] is not None and "requestBody" in operation:
                body = operation["requestBody"]["content"]["application/json"]
                body.setdefault("examples", {})[f"example{i}"] = {"summary": name, "value": r["sent"]}
    return spec


def main():
    check_routes_and_codes()
    run_examples()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "README.md").write_text(render(), encoding="utf-8")
    (OUT / "openapi.json").write_text(json.dumps(enriched_openapi(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote docs/api-docs/README.md ({len(E)} endpoints, {sum(len(e['examples']) for e in E)} real examples) and docs/api-docs/openapi.json")


if __name__ == "__main__":
    main()
