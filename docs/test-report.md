# `docs/test-report.md` — Test Report (L4, track SE, BT3)

Plan: `docs/test-plan.md` · code: `tests/bt3/test_bt3_cases.py` · bugs: `docs/bug-log.md`.

**How each case is run.** One command per case prints the API calls it made, an
`observed:` line with the actual values, and PASSED/FAILED:
`pytest -s -v tests/bt3 -k tc05` (Docker database: prefix `DB_PORT=5433`). Database cases
start from a fresh copy of the seeded sample (Test Plan §4). The screenshot of that
terminal is `docs/screenshots/TC-xx.png`.

**Runs recorded** (05/11/2026, by the student; Linux, Python 3.14.8, pytest 8.3.4, PostgreSQL 16
from `docker compose up -d db`, so every command was prefixed with `DB_PORT=5433`).
**Run 1** = commit `cf58fa7` (cases added, no fix yet): the three cases that failed when the
cases were written — TC-08, TC-09, TC-11 — were run again to record the failure.
**Run 2** = commit `8990458` (after the three fixes): all 12 cases. A case that failed in run 1
shows both results and both screenshots (`TC-xx-run1.png`, `TC-xx.png`).
**Run 3** (12/11/2026, by the student) = commit `8f4cfdb` (the `v1.0` application code; `v1.0` only adds tests and documents), on the clean-machine
test: fresh clone in an empty folder, `docker compose up -d --build`, then
`docker compose exec api pytest -v tests/bt3/test_bt3_cases.py` inside the api container
(Python 3.12.7, pytest 9.1.1): all 12 PASS, the same actual results as run 2 except TC-12, whose
migrate line now reads "0 applied, 3 already up to date" (BT3 migration 003) · [run3](screenshots/run3.png).

Priority: **High** = a MUST rule or a security property · **Medium** = SHOULD behaviour or
message quality · **Low** = convenience.

| ID · type · source | Preconditions | Steps | Test data | Expected result | Priority | Actual result | P/F |
|---|---|---|---|---|---|---|---|
| **TC-01** · happy path · QT-08, FR2, US2 AC1 · API + DB | Fresh sample DB. Ticket BH-008036/2026: center 2, `MOI`, category 1 (MAN_HINH). Logged in as `manager2` | 1. `GET /api/tickets/8036/qualified-technicians` 2. Compare with an independent SQL query (center 2, active, proficiency ≥ 3 in category 1) | ticket 8036; technicians of center 2 with a category-1 skill: 5 (prof. 2), 8 (4), 25 (3), 29 (4), 30 (5) | 200; exactly technicians {8, 25, 29, 30}; lowest proficiency 3; technician 5 (prof. 2) absent | High | 200; returned [8, 25, 29, 30] = SQL [8, 25, 29, 30]; lowest proficiency 3 · [TC-01](screenshots/TC-01.png) | PASS |
| **TC-02** · happy path · QT-07, QT-06, NFR5, FR3, US4 AC1 · API + DB | As TC-01; ticket 8036 has 1 status-log row (creation) | 1. `POST /api/tickets/8036/assignment` 2. Read the ticket and its status-log rows | `{"technician_id": 29}` (proficiency 4) | 200; ticket `DA_PHAN_CONG`, technician 29; status-log rows 1 → 2, last row `MOI → DA_PHAN_CONG` | High | 200; ticket `DA_PHAN_CONG`, technician 29; log rows 1 → 2, last `MOI → DA_PHAN_CONG` · [TC-02](screenshots/TC-02.png) | PASS |
| **TC-03** · happy path · FR6, FR7, US5 AC1 · API + DB | Ticket BH-000194/2025: center 2, warranty, `DA_PHAN_CONG`, technician 30. Technician 30 has no active appointment overlapping the slot (checked by SQL) | 1. `POST /api/appointments` 2. Count appointments before/after | `{"ticket_id": 194, "loai": "NHAN_MAY", "ngay_hen": today + 30 days, "gio_bat_dau": "14:00", "gio_ket_thuc": "15:00"}` | 201; `trang_thai = DA_XAC_NHAN`; `technician_id = 30` (from the ticket); appointments 80 → 81 | High | Overlaps before: 0; 201; `DA_XAC_NHAN`; technician 30; appointments 80 → 81 · [TC-03](screenshots/TC-03.png) | PASS |
| **TC-04** · happy path · QT-14, FR1, US1 AC1/AC3 · API + DB | Fresh sample DB: 27 open warranty `MOI` tickets in center 1 and 27 in center 2 | 1. `GET /api/tickets/unassigned?page_size=100` as `manager1` 2. Same as `manager2` 3. Compare ids | page_size 100 | Each list: total = SQL count for that center (27), only that `center_id`; no ticket id in both lists | High | manager1: total 27 (SQL 27), centers {1}; manager2: total 27 (SQL 27), centers {2}; shared ids 0 · [TC-04](screenshots/TC-04.png) | PASS |
| **TC-05** · happy path · QT-15, NFR4 · API + DB | As TC-04 | 1. Same list with a `TECHNICIAN`-role token for center 2 2. Same list as `manager2` 3. Check each `customer_phone` | role `TECHNICIAN`, center 2; pattern `^\d{3}\*{4}\d{3}$` (masked) / `^\d{10}$` (full) | Technician: 27/27 numbers masked (100 %, NFR4); manager: 27/27 full numbers | High | Technician: 27/27 masked (e.g. `095****878`); manager: 27/27 full; SQL 27 · [TC-05](screenshots/TC-05.png) | PASS |
| **TC-06** · boundary (inside) · QT-08, US4 AC3 · unit | Service with in-memory data mirroring ticket 8036; technician 25 has proficiency **3** in category 1 | 1. `assign_technician(ticket 8036, technician 25)` | proficiency 3 (= threshold) | Accepted: status `DA_PHAN_CONG`, technician 25, 1 log row | High | Accepted: `DA_PHAN_CONG`, technician 25, 1 log row · [TC-06](screenshots/TC-06.png) | PASS |
| **TC-07** · boundary (outside) · QT-08, US4 AC3 · unit | As TC-06; technician 5 has proficiency **2** in category 1 | 1. `assign_technician(ticket 8036, technician 5)` | proficiency 2 (threshold − 1) | Rejected with `technician_not_qualified`; ticket stays `MOI` with no technician; 0 log rows | High | `technician_not_qualified`; ticket `MOI`, technician none; 0 log rows · [TC-07](screenshots/TC-07.png) | PASS |
| **TC-08** · invalid data · BT2 C7, API contract §1 · API | Logged in as `manager1` (fakes behind the API) | 1. `POST /api/appointments` with a body that is not valid JSON | `{"ticket_id": 103, "loai": "NHAN_MAY"` (closing brace missing) | 400 `bad_request`; message exactly "Request body is not valid JSON."; `details[0].field = "body"` | Medium | **Run 1:** 400 `bad_request`, message "Request data is missing or malformed: 37.", field `"37"` → **BUG-013** · [TC-08-run1](screenshots/TC-08-run1.png)<br>**Run 2:** 400 `bad_request`, "Request body is not valid JSON.", field `body` · [TC-08](screenshots/TC-08.png) | **FAIL** → PASS |
| **TC-09** · invalid data · QT-07, FR5 · API + DB | Ticket BH-000194/2025 assigned to technician 30; logged in as `manager2` | 1. Count its status-log rows 2. `PATCH /api/tickets/194/assignment` 3. Count again | `{"technician_id": 30, "reason": "Khách yêu cầu giữ nguyên KTV"}` (the current technician) | 422 `same_technician`, message "The ticket is already assigned to this technician."; status-log rows unchanged | High | **Run 1:** **200**, no error; log rows 2 → 3 → **BUG-012** · [TC-09-run1](screenshots/TC-09-run1.png)<br>**Run 2:** 422 `same_technician`, "The ticket is already assigned to this technician."; log rows 2 → 2 · [TC-09](screenshots/TC-09.png) | **FAIL** → PASS |
| **TC-10** · security (OWASP A01) · QT-14, NFR3 · API + DB | Appointment 900004 belongs to center 2, 09:00–10:00. Logged in as `manager1` (center 1) | 1. `PATCH /api/appointments/900004` 2. Read the row again | `{"gio_bat_dau": "10:00", "gio_ket_thuc": "11:00"}` with manager1's token | 403 `cross_center_access`; the row still 09:00–10:00 | High | 403 `cross_center_access`; row 09:00–10:00 before and after · [TC-10](screenshots/TC-10.png) | PASS |
| **TC-11** · security (OWASP A07/A02) · QT-14, FR12 · API | API configured exactly as README/Docker: settings from `.env.example` | 1. Sign a `CENTER_MANAGER` token for center 1 with each secret published in the repository 2. `GET /api/tickets/unassigned` with it | secrets: the v0.2 `.env.example` value, the v0.2 `config.py` default, and the current `.env.example` value if any | Every forged token → 401 `unauthorized` | High | **Run 1:** v0.2 `.env.example` secret → **200**, v0.2 `config.py` default → 401, current `.env.example` value (the same sample) → **200** → **BUG-011** · [TC-11-run1](screenshots/TC-11-run1.png)<br>**Run 2:** both published secrets → 401; `.env.example` has no value any more · [TC-11](screenshots/TC-11.png) | **FAIL** → PASS |
| **TC-12** · reproducibility · BT2 C5, BT3 C8 · system | Test DB already migrated and seeded once (`migrate.py` + `seed.py`) | 1. Count rows in the 6 tables 2. `python scripts/migrate.py` 3. `python scripts/seed.py` 4. Count again | the committed sample `data/sample/` | migrate: "0 applied, *n* already up to date" (*n* = files in `db/migrations/`: 2 at run 2, 3 since BT3 migration 003); seed: every table `+0`; counts unchanged (6 / 38 / 159 / 487 / 1390 / 80) | High | migrate "0 applied, 2 already up to date"; every table `+0`; totals 6 / 38 / 159 / 487 / 1390 / 80 · [TC-12](screenshots/TC-12.png) | PASS |

## Summary

| | Run 1 (`cf58fa7`, before the fixes) | Run 2 (`8990458`, after the fixes) | Run 3 (`8f4cfdb`, `v1.0` application code, clean machine, Docker) |
|---|---|---|---|
| Cases run | 3 (TC-08, TC-09, TC-11) | 12 (TC-01 … TC-12) | 12 (TC-01 … TC-12) · [run3](screenshots/run3.png) |
| PASS / FAIL | 0 / 3 | 12 / 0 | 12 / 0 |
| Bugs opened | BUG-011 (Critical), BUG-012 (Major), BUG-013 (Minor) | none | none (BUG-014 … 016 came from the security checklist) |
| Whole suite, one command | — | `pytest -q` → **98 passed** · [full-suite](screenshots/full-suite.png) | `docker compose exec api pytest -q` → **113 passed** · [clean-2](screenshots/clean-2.png) |

**Success criteria (Test Plan §3):** 12/12 cases run with a concrete actual result and a
screenshot · every implemented rule has a happy-path case and QT-08 is tested on both sides ·
NFR4 measured at 27/27 = 100 % masked (TC-05) · no Critical or Major bug open · `pytest -q`
0 failed, 0 skipped — **all met.**

Five BT3 types: happy path TC-01 – TC-05 · boundary TC-06, TC-07 · invalid data TC-08, TC-09 ·
security TC-10, TC-11 · reproducibility TC-12.
