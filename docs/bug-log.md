# `docs/bug-log.md` — Bug Log (L4)

Template (course, 7 lines): **ID & severity** · **Found by** · **Symptom** · **How to reproduce** ·
**Root cause** · **Fix** · **Commit & confirmation**.
Severity (BT3 definitions, asked in this order): **Critical** — the system cannot be used, data is
wrong, or data leaks / there is a security hole · **Major** — an important function is wrong or
unusable but there is a way around it · **Minor** — presentation or experience only, the business
result is still right. BUG-001 … BUG-010 were found in BT2 by reviews and runs; BUG-011 … BUG-013
by the BT3 Test Report cases (`docs/test-report.md`); BUG-014 … BUG-016 while filling the
security checklist by running it (`docs/checklist-bao-mat.md`).
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

### BUG-010 · Critical — `pip install -r requirements.txt` failed on Python 3.14
- **Found by:** clean-machine rehearsal on Linux before tagging `v0.2` (Session 12).
- **Symptom:** `ERROR: No matching distribution found for psycopg-binary==3.2.3`; pip only offered 3.2.10+.
- **Reproduce:** Python 3.14 → `pip install -r requirements.txt` (or `pip download --only-binary=:all: --python-version 3.14 …`).
- **Root cause:** the pinned `psycopg[binary]==3.2.3` and `pydantic==2.10.3` (→ `pydantic-core 2.27.1`) were released before Python 3.14 and publish no prebuilt wheels for it; pinned versions must have wheels for every Python version the README allows.
- **Fix:** `psycopg[binary]==3.2.13`, `pydantic==2.13.5` (both publish wheels for 3.11–3.14); FastAPI and the other pins unchanged. One Python 3.14 deprecation warning raised inside FastAPI/Starlette is filtered in `pytest.ini`. README states Python 3.11 – 3.14.
- **Commit & confirmation:** `6683cf6`; fresh virtual environments on Python 3.11, 3.12, 3.13 and 3.14 install with wheels only and pass all 81 tests; on 3.14 migrate, seed (second run +0), API and an assignment work against PostgreSQL 16.

## BT3 — found by the Test Report cases (Session 14)

### BUG-011 · Critical — anyone could sign a login token with the secret published in the repository
- **ID & severity:** BUG-011 · CRITICAL — question 1 of the decision tree, *security hole / data leaks* — other centers' customer data readable and changeable.
- **Found by:** TC-11 (security, OWASP A07/A02).
- **Symptom:** with the API started as README and Docker say (`cp .env.example .env`), a token that an outsider signs with the `JWT_SECRET` value printed in `.env.example` is accepted: `GET /api/tickets/unassigned` → **200** with center 1's tickets, customer names and phone numbers, for any center the outsider writes into the token. TC-11 first run: `v0.2_.env.example=200`.
- **Reproduce:** check out `v0.2` → `cp .env.example .env` → start the API → `python -c "import jwt,time; print(jwt.encode({'sub':'x','user_id':1,'role':'CENTER_MANAGER','center_id':1,'exp':int(time.time())+3600}, 'change_me_to_a_long_random_string_32_chars_min', algorithm='HS256'))"` → call any endpoint with that token: 200 every time.
- **Root cause:** the key that signs tokens must be private, but the public repository shipped a working value in `.env.example` (and another as the default in `src/config.py`), and the documented set-up copies that file unchanged. Nothing checked the key, so every installation following the README signed tokens with a key every reader of the repository knows, and QT-14 (center from the token) could be bypassed.
- **Fix:** `src/config.py` refuses the two published values and any key shorter than 32 characters at start-up, and an empty `JWT_SECRET` now means a random key per API process (warning in the log; users log in again after a restart). `.env.example` leaves `JWT_SECRET` empty, `docker-compose.yml` no longer requires it, the tests use their own key, README notes how to clear an old `.env`. The set-up stays at two commands.
- **Commit & confirmation:** [`1692bf4`](https://github.com/RASPHONE/cdtn1-rasphonesamphanthamith-l4/commit/1692bf4dc5309cab5ba1cb7b8100a7d06eeb4eff) · TC-11 re-run: both published secrets → 401 (screenshots `TC-11-run1.png` → `TC-11.png`), a real login still → 200; new regression tests in `tests/test_config.py` (published or short key refused, empty key → random).

### BUG-012 · Major — "reassigning" a ticket to its current technician was accepted and logged as a change
- **ID & severity:** BUG-012 · MAJOR — question 2, *an important function is wrong* — the assignment history (QT-07 audit trail) records false changes; there is a way around it (M2 does not offer the current technician), and the ticket itself stays correct, so not Critical.
- **Found by:** TC-09 (invalid data).
- **Symptom:** `PATCH /api/tickets/194/assignment` with `{"technician_id": 30, "reason": "Khách yêu cầu giữ nguyên KTV"}` for a ticket already held by technician 30 → **200**, and `ticket_status_log` gained a row (2 → 3) recording a reassignment that did not happen.
- **Reproduce:** any ticket in `DA_PHAN_CONG`; PATCH its assignment with its own `technician_id` and a valid reason; count `ticket_status_log` rows for the ticket before and after.
- **Root cause:** `TicketAssignmentService.reassign_technician` checked the reason (QT-07) and the new technician's eligibility (QT-08) but never compared the requested technician with the one already assigned. The only guard was the disabled radio button on screen M2, i.e. the rule lived in the presentation layer only.
- **Fix:** the service raises `same_technician` (422, "The ticket is already assigned to this technician.") before any write; API contract §3.4 and the validation table list the new code; unit regression test `test_reassign_to_the_current_technician_is_rejected_without_log`.
- **Commit & confirmation:** [`6e10882`](https://github.com/RASPHONE/cdtn1-rasphonesamphanthamith-l4/commit/6e10882e13dcb05524eaae133ae8c1744c65cf55) · TC-09 re-run: 422 `same_technician`, log rows unchanged (screenshots `TC-09-run1.png` → `TC-09.png`).

### BUG-013 · Minor — a body that is not JSON was rejected with a meaningless field name
- **ID & severity:** BUG-013 · MINOR — neither question 1 nor 2 — the request is still refused with the right status and nothing is saved; only the explanation is wrong.
- **Found by:** TC-08 (invalid data, message checked).
- **Symptom:** `POST /api/appointments` with a truncated JSON body → 400 `bad_request` as expected, but the message read "Request data is missing or malformed: 37." and `details[0].field` was `"37"`.
- **Reproduce:** send `{"ticket_id": 103, "loai": "NHAN_MAY"` (no closing brace) to any POST/PATCH endpoint.
- **Root cause:** the validation handler in `src/main.py` names fields from Pydantic's error location. For a JSON decode error that location is `("body", <character offset>)`, so the offset of the syntax error was reported as if it were a field.
- **Fix:** errors of type `json_invalid` get their own response: "Request body is not valid JSON.", `details: [{"field": "body", …}]`; API contract §1 documents it.
- **Commit & confirmation:** [`fe1fd2f`](https://github.com/RASPHONE/cdtn1-rasphonesamphanthamith-l4/commit/fe1fd2fc11bc5fae2259e9230cf01fabf2f6c3c2) · TC-08 re-run: 400, message "Request body is not valid JSON.", field `body` (screenshots `TC-08-run1.png` → `TC-08.png`).

## BT3 — found by the security checklist (Session 15)

### BUG-014 · Critical — demo passwords were kept in plain text in the source code
- **ID & severity:** BUG-014 · CRITICAL — question 1 of the decision tree, *security hole* — credentials stored and compared in clear (OWASP A04/A07, BT3 S3); changing a password meant writing the new one into the public repository.
- **Found by:** security checklist item 4 ("passwords hashed"): the check `SELECT password_hash FROM <users table>` could not be run because there was no users table.
- **Symptom:** `src/services/auth_service.py` held `DEMO_USERS = {"manager1": {"password": "manager123", …}, …}` and `login()` compared `user["password"] != password`; nothing anywhere stored a hash.
- **Reproduce:** check out `b58fb4a` → `grep -n '"password"' src/services/auth_service.py` → two plain-text passwords; `psql … -c "\dt"` → no user table.
- **Root cause:** the BT2 demo login (TD-07) kept its two accounts as a constant to stay small ("in a real system, these would be in a `users` table with hashed passwords"), and BT2 did not check password storage; S3 in BT3 requires hashes in the database.
- **Fix:** migration `003_add_app_user.sql` creates `app_user` with a `CHECK` that only accepts `pbkdf2_sha256$…` values; `seed.py` creates the two accounts from `DEMO_PASSWORD` hashed with PBKDF2-SHA256 (600,000 iterations, random salt); `AuthService` reads the account through `PostgresUserRepository` and compares in constant time, checking a dummy hash for unknown usernames. Tests: `test_password_storage.py` (4), `bt3/test_password_storage_db.py` (2).
- **Commit & confirmation:** [`2240727`](https://github.com/RASPHONE/cdtn1-rasphonesamphanthamith-l4/commit/224072743ac5c29032b9cd0ef62ce5bdc12ff567) · `SELECT username, left(password_hash, 48) FROM app_user` → `pbkdf2_sha256$600000$…` for both accounts; login with `manager123` still 200, wrong password 401; a plain-text insert is refused by the database (screenshot `sec-4.png`).

### BUG-015 · Minor — unknown paths and wrong methods answered outside the error format
- **ID & severity:** BUG-015 · MINOR — neither question 1 nor 2 — the status code was right and nothing leaked; only the body did not follow the API contract.
- **Found by:** security checklist item 5 ("error messages reveal nothing internal"), calling a path that does not exist.
- **Symptom:** `GET /api/nope` → 404 `{"detail": "Not Found"}` and `PUT /api/appointments` → 405 `{"detail": "Method Not Allowed"}`, while every other error is `{"error", "message"}` (API contract §1); the UI's error handling reads `error`.
- **Reproduce:** `curl -s http://localhost:8000/api/nope` on `b58fb4a`.
- **Root cause:** `src/main.py` mapped `AppError`, validation errors, database errors and unexpected exceptions to the envelope, but not the HTTP errors raised by the framework's router itself (Starlette `HTTPException`).
- **Fix:** a handler for Starlette's `HTTPException` answers `404 not_found` "No such endpoint." and `405 method_not_allowed` (keeping the `Allow` header); API contract §1 lists both. Regression test `test_unknown_path_and_wrong_method_use_the_error_envelope`.
- **Commit & confirmation:** [`3804e6c`](https://github.com/RASPHONE/cdtn1-rasphonesamphanthamith-l4/commit/3804e6c2e3ac456043a1dc4fb45792080ccfd779) · `GET /api/nope` → 404 `{"error":"not_found","message":"No such endpoint."}` (screenshot `sec-5.png`).

### BUG-016 · Minor — a 500 response could not be matched to its log line by header
- **ID & severity:** BUG-016 · MINOR — neither question 1 nor 2 — the client still got a safe 500 with a `request_id` in the body; only the operator's tracing was incomplete.
- **Found by:** security checklist item 5, writing the test for an unexpected error (`test_unexpected_error_returns_500_without_internal_details`).
- **Symptom:** an unexpected exception answered 500 `{"error": "internal_error", …, "request_id": …}` but without the `X-Request-ID` header that every other response carries, and the request log had no `status=500` line for it.
- **Reproduce:** make a service raise `RuntimeError` (as the test does) and read the response headers and the log: header missing, only the stack trace line.
- **Root cause:** the handler for `Exception` runs in Starlette's outermost error middleware, outside the `request_log` middleware that sets the header and writes the request line; the exception left `call_next` and skipped both.
- **Fix:** `request_log` catches the exception itself, logs the stack trace with the request id and returns the same 500 envelope, so the header and the request line are written; the `Exception` handler stays as a last resort.
- **Commit & confirmation:** [`354f526`](https://github.com/RASPHONE/cdtn1-rasphonesamphanthamith-l4/commit/354f526a5a76bcef5005e2ed0f5bc25401565e0b) · the new test fails on the previous commit and passes now; log shows `request_id=… unhandled error` and `request_id=… status=500` with the same id.
