# `docs/test-plan.md` — Test Plan (L4, track SE, BT3)

Flow **L4 — Technician Assignment & Appointment Scheduling** · system as tagged `v0.2`
plus BT3 changes · written in Session 14 (05/11/2026), test counts and environment updated
for tag `v1.0` (Session 15–16). Results: `docs/test-report.md` ·
bugs: `docs/bug-log.md` · cases in code: `tests/bt3/test_bt3_cases.py`.

## 1. Scope

**Tested** — every business rule the system implements, plus the two behaviours the
grading steps exercise (rejecting bad input, re-running the data load):

| Area | Rule / requirement | Cases |
|---|---|---|
| Eligible technicians | QT-08 (same center, active, proficiency ≥ 3) · FR2, FR4 | TC-01, TC-06, TC-07 |
| One technician, logged change | QT-07, QT-06 · FR3, FR5 · NFR5 (ticket + log written together) | TC-02, TC-09 |
| Appointment overlap | FR6, FR7 | TC-03 |
| Own-center data only | QT-14 · NFR3 · OWASP A01 | TC-04, TC-10 |
| Phone masking | QT-15 · NFR4 (100 % of rows masked for other roles) | TC-05 |
| Authentication | Demo login tokens (FR12) · OWASP A07 / A02 | TC-11 |
| Rejecting bad input | BT2 C7 / API contract §1 (clear 4xx, no raw library error) | TC-08, TC-09 |
| Re-running migration and seed | BT2 C5 / BT3 C8 | TC-12 |

**Not tested, on purpose**

- **Screens M1–M3 as automated UI tests.** They contain no business rule (every rule is in
  the API, tested here); their three states were checked by hand with screenshots in BT2.
- **NFR1/NFR2 response times and NFR6 usability.** They need load tooling and real users;
  out of scope for the prototype (course: performance and UAT belong to CĐTN2).
- **Features that are not implemented:** `KIEM_TRA_TAI_CHO` appointments, cancellation /
  no-show (US10), technician screens (US7), customer portal (US11) — SRS §1.3, §3.3.
- **Real parallel load on the assignment guard.** The race is covered by a unit test
  (`test_assignment_lost_race_is_rejected_without_log`); two live clients are not simulated.

## 2. Test types and numbers per layer

**12 Test Report cases.** Each one is an automated test that prints its actual result.

| Layer | What runs | Cases | Count |
|---|---|---|---|
| Unit | Service + in-memory fakes | TC-06, TC-07 | 2 |
| API | Real routes and error handlers, fakes behind the services | TC-08, TC-11 | 2 |
| API + PostgreSQL (integration) | Routes → services → SQL repositories on a fresh copy of the sample | TC-01 – TC-05, TC-09, TC-10 | 7 |
| System | The real `migrate.py` / `seed.py` commands | TC-12 | 1 |

The base of the pyramid is the **81 unit and API tests from BT2** plus 15 regression tests
added with the BT3 changes (`tests/test_*.py`, 96 tests, in-memory fakes, no database), 4
database security tests (`tests/bt3/test_password_storage_db.py`, `test_injection_db.py`,
security checklist items 2 and 4) and 3 database tests for the FR behaviours computed in SQL
(`tests/bt3/test_fr_coverage_db.py`: FR1 order by due date, FR8 workload, FR9 filter).
Everything runs with the same command: **115 tests**. SRS §6.2 maps every FR to its cases.
The report cases lean on the database because QT-14, FR7 and the assignment guard are
enforced partly in SQL: only a real database shows that no extra row was written.

**The five BT3 types:** happy path ×5 (TC-01 – TC-05, one per rule: QT-08, QT-07 + NFR5,
FR7, QT-14, QT-15) · boundary ×2 (TC-06 / TC-07, both sides of proficiency ≥ 3) ·
invalid data ×2 (TC-08, TC-09; status code **and** message checked) · security ×2
(TC-10 A01, TC-11 A07) · reproducibility ×1 (TC-12).

**Choosing test data**

- *Boundary values:* proficiency 3 (accepted) and 2 (rejected), the two values next to the
  QT-08 threshold. The regression suite also checks FR7 next to an existing 09:00–10:00
  appointment: 10:00–11:00 (touching, allowed) and 09:59–11:00 (one minute of overlap,
  blocked), and the reason length at 4 (rejected) and 5 characters (accepted).
- *Equivalence partitions:* token missing, malformed (regression suite) or signed with a
  secret published in the repository (TC-11); request body valid, missing fields
  (BT2 TC-03) or not JSON at all (TC-08); reassignment to another qualified technician
  (TC-02 path) or to the current one (TC-09). Not covered: a reason longer than 255
  characters (rejected in a manual check, no automated case).
- *Side effects are measured, not assumed:* each database case counts rows before and after
  (status log, appointments), or reads the changed row back.

## 3. Success criteria (set before the run)

- 12/12 cases executed, each with a concrete actual result and a screenshot in
  `docs/screenshots/TC-xx.png`; a case is PASS only when every expected value matches.
- Each implemented rule (QT-07, QT-08, QT-14, QT-15, FR7, NFR5) has ≥ 1 happy-path case,
  and the QT-08 threshold is tested on both sides.
- NFR4 measured in TC-05: 100 % of phone numbers returned to a non-manager role are masked.
- No **Critical** bug open at tag `v1.0`; every Major bug fixed, or its reason and plan recorded.
- `pytest -q` ends with 0 failed; with PostgreSQL reachable, 0 skipped.

## 4. Environment and test data

| Item | Value |
|---|---|
| Runtime | Python 3.11–3.14 virtual environment from `requirements.txt` (README §3), or the api container of `docker compose` (Python 3.12.7, tests included in the image) |
| Database | PostgreSQL 16: a local server with the DB_* values from `.env`, or the Docker one (`docker compose up -d db`, then `DB_PORT=5433` because Docker publishes it on host port 5433) |
| Data | The committed sample `data/sample/` (fixed ids). Cases use ticket BH-008036/2026 (center 2, MOI, category 1), BH-000194/2025 (center 2, assigned to technician 30), technicians 5, 8, 25, 29, 30, and demo appointment 900004 (center 2) |
| Set-up | Once per run, the tests create `<DB_NAME>_test_tpl` with the real `python scripts/migrate.py` and `python scripts/seed.py`. **Before every database case** they recreate `<DB_NAME>_test` as a copy of it, so no case depends on another or on leftover data. Both databases are dropped at the end; the application database is never touched |
| Unit / API cases | In-memory fakes (`tests/fakes.py`); no database, no `.env` |
| Commands | All tests: `pytest -q`, or in Docker `docker compose exec api pytest -q` · one case with its actual-result line: `pytest -s -v tests/bt3 -k tc05` (Docker: `docker compose exec api pytest -s -v tests/bt3 -k tc05`) |
| CI | `.github/workflows/ci.yml` runs the same command on a clean GitHub runner with a PostgreSQL 16 service, on every push |
