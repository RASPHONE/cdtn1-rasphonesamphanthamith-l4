# `docs/bug-log.md` — Bug Log (L4)

Template (course, 7 lines): **ID & severity** · **Found by** · **Symptom** · **How to reproduce** ·
**Root cause** · **Fix** · **Commit & confirmation**.
Severity: Critical (main flow or grading check blocked) · Major (wrong result, workaround exists) · Minor.
Commit links: `https://github.com/RASPHONE/cdtn1-rasphonesamphanthamith-l4/commit/<sha>`.

### BUG-001 · Major — first assignment after seeding failed with a duplicate key
- **Found by:** using the API after seeding (fix recorded in commit `7361e02`, "prevent unique violations"); reproduced again in Session 12 from the pre-fix seed.
- **Symptom:** the first insert into `ticket_status_log` — i.e. the first assignment — failed: `duplicate key value violates unique constraint "ticket_status_log_pkey"`, `Key (log_id)=(1) already exists` (API answer: 500).
- **Reproduce:** empty DB → migrate → run the seed of commit `7361e02~1` (status-log rows inserted with explicit ids 1–5) → insert a status-log row without an id.
- **Root cause:** inserting explicit ids does not advance a `BIGSERIAL` sequence, so the next generated `log_id` (1) collided with a seeded row. Appointments did not fail only because their seeded ids (201–204) were above the sequence start.
- **Fix:** `setval()` every sequence to `MAX(id)` after seeding (now `sync_sequences()` in `scripts/seed.py`).
- **Commit & confirmation:** `7361e02`; with the current seed, assignments write status-log rows without error (`test_ticket_assignment_flow`, browser run).

### BUG-002 · Major — new appointments were saved as `DA_DAT`
- **Found by:** review against SRS US5 AC1 / API contract 3.5.
- **Symptom:** a newly created appointment showed status "Đã đặt" instead of "Đã xác nhận".
- **Reproduce:** `POST /api/appointments` with a valid body → response `trang_thai = DA_DAT`.
- **Root cause:** the service hard-coded `DA_DAT`; the BT1 design creates confirmed appointments (`DA_XAC_NHAN`).
- **Fix:** service sets `DA_XAC_NHAN`; PATCH only accepts `DA_XAC_NHAN` (TD-09, TD-10).
- **Commit & confirmation:** `693f2b0`; `test_create_valid_appointment` asserts `DA_XAC_NHAN` and passes.

### BUG-003 · Critical — three tests needed a running PostgreSQL
- **Found by:** running `pytest -q` with PostgreSQL stopped (clean-folder rehearsal).
- **Symptom:** `3 failed, 50 passed` — `psycopg.OperationalError: connection refused` in `test_assign_valid_technician`, `test_reassign_with_reason`, `test_ticket_assignment_flow`.
- **Reproduce:** stop PostgreSQL (or clone on a machine without it) → `pytest -q`.
- **Root cause:** `TicketAssignmentService` imported `src.db.get_connection` to open its NFR5 transaction, so the service touched the real database even when its repositories were fakes (also a layer-boundary leak, C2).
- **Fix:** the transaction factory is injected (`src/repositories/transaction.py`); tests pass `fake_transaction` from `tests/fakes.py`.
- **Commit & confirmation:** `da85250`, `30fe3b0`; with PostgreSQL stopped and no `.env`: all tests pass.

### BUG-004 · Critical — M2 assignment screen was blank
- **Found by:** repository review and browser run in Session 12 (the API shape had changed in TD-13).
- **Symptom:** clicking "Phân công" opened M2 with only the title — no technician table and no empty-state message, so no ticket could be assigned from the UI.
- **Reproduce:** log in → M1 → "Phân công" on a ticket that has qualified technicians.
- **Root cause:** the API now returns `{ "ticket_id", "items": [...] }`, but `M2Assignment.jsx` stored the whole object and tested `techs.length` (undefined), so neither the table nor the empty branch rendered.
- **Fix:** rebuilt M2 on `data.items` with the shared `DataState` component (loading / empty / error).
- **Commit & confirmation:** `a38d891`; end-to-end browser run: M2 lists 4 technicians, assignment succeeds.

### BUG-005 · Major — wrong password reloaded the login page silently
- **Found by:** browser run of the invalid-data case in Session 12.
- **Symptom:** after a wrong password the page reloaded and no error was shown.
- **Reproduce:** login with `manager1` / any wrong password.
- **Root cause:** the API client treated every 401 as "session expired" (clear token + `window.location.reload()`), including the 401 `invalid_credentials` of the login call itself.
- **Fix:** 401 ends the session only for calls other than `/api/auth/login`; the login form shows "Sai tên đăng nhập hoặc mật khẩu."
- **Commit & confirmation:** `a38d891`; browser run shows the message.

### BUG-006 · Major — omitted reassignment reason returned 400 instead of 422
- **Found by:** curl with `{"technician_id": 2}` against API contract §4 (BT1 feedback: "thiếu lý do 422").
- **Symptom:** `400 bad_request — reason: Field required` instead of `422 reason_required`.
- **Reproduce:** `PATCH /api/tickets/{id}/assignment` on an assigned ticket without `reason`.
- **Root cause:** `reason` was a required field in the Pydantic schema, so the request was rejected as malformed before the QT-07 rule ran.
- **Fix:** `reason` optional in the schema; the service checks 5–255 characters after trim (TD-18).
- **Commit & confirmation:** `da85250`; `test_reassign_with_missing_reason_field_returns_422` and `test_tc03_…` pass.

### BUG-007 · Major — soft-delete migration was never executed
- **Found by:** reading `scripts/migrate.py` during the repository review.
- **Symptom:** `db/migrations/003_add_appointment_soft_delete.sql` existed but no script ran it; the schema only had `is_deleted` because it had also been copied into `docs/ddl_l4.sql`.
- **Reproduce:** `grep -n migrations scripts/migrate.py` → no match.
- **Root cause:** migrate.py executed the design document `docs/ddl_l4.sql` instead of the migrations folder.
- **Fix:** numbered migrations `001`/`002` applied in order with a `schema_migrations` table (TD-15).
- **Commit & confirmation:** `157f390`; fresh DB and an old DB both migrate; `pg_dump -s` identical to `docs/ddl_l4.sql`.

### BUG-008 · Minor — every file showed as modified on Windows
- **Found by:** `git status` on the Windows working copy.
- **Symptom:** 66 files "modified" with 9,000 insertions / 9,000 deletions; `git diff --ignore-cr-at-eol` empty.
- **Reproduce:** check out the repo with CRLF conversion and inspect it with a Git that does not convert.
- **Root cause:** no line-ending policy in the repository.
- **Fix:** `.gitattributes` with `* text=auto eol=lf` (TD-28).
- **Commit & confirmation:** `65e0e81`; `git status` clean after checkout.

### BUG-009 · Minor — technician skill list shape differed from the contract
- **Found by:** comparing responses with API contract 3.11.
- **Symptom:** `GET /api/technicians/{id}/skills` returned a bare array instead of `{ "technician_id", "items" }`.
- **Reproduce:** call the endpoint with any technician of the caller's center.
- **Root cause:** the route's response model was `List[TechnicianSkillRead]`.
- **Fix:** `TechnicianSkillList` response (TD-29).
- **Commit & confirmation:** `23f53b6`; `test_technician_skill_crud_flow` and `test_list_skills` updated and pass.
