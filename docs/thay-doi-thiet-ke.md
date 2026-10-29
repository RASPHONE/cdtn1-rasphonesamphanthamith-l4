# Design Change Log

*This file is re-read during BT2 and BT3 grading (rubric criterion 3: Consistency &
Accumulation). When BT2 feedback arrives (Session 13+), append new entries at the end
of this file with the next TD-xx codes.*

**Format.** Changes triggered by lecturer feedback (TD-01 … TD-03) use the Session 8
template: **Feedback · Decision · Reason · Impact**. All other changes use the BT2
three-line format: **Change** (what) · **Reason** (why) · **Impact** (which components).

## After BT1 feedback (Session 8, date 15/10/2026)

### TD-01 Measurable threshold for NFR4 (phone masking)
- **Feedback:** NFR4's threshold "Mask format enforced" is not a numeric threshold. It should read e.g. "100% of phone numbers returned to other roles are displayed as `090****567`."
- **Decision:** FIX
- **Reason:** The course rule requires every NFR to have a measurable numeric threshold; a qualitative threshold cannot produce a PASS/FAIL test case in BT3. The figure 100% combined with the exact format (3 leading digits + 4 asterisks + 3 trailing digits) makes NFR4 verifiable by an automated regex assertion and matches QT-15.
- **Impact:** Threshold cell of the NFR4 row in `docs/srs.md` Section 4 updated (SRS bumped to v0.4); no change to any `.drawio` diagram, ERD, or wireframe; BT3 test case TC_NFR4 derived from it.

### TD-02 Location of the API Contract and directory tree
- **Feedback:** The API Contract section and the directory tree belong in the repo (`api-contract.md`); they do not need to be in the PDF.
- **Decision:** FIX
- **Reason:** The mandatory PDF structure is exactly the 5 components + AI appendix, 6–9 pages total; the API Contract is not one of the 5 components and does not appear in Checklist 18. The track-spec requirement ("track-specific spec submitted with BT1") is already satisfied by `docs/api-contract.md` in the repo, per the Session 4 workflow (fill the track template and commit it to the repo).
- **Impact:** API Contract page removed from the PDF (together with the table-of-contents resize this brought the document from 35 to 29 pages, see TD-03); `docs/api-contract.md` remains unchanged in the repo as the reference for BT2 implementation and BT3 tests; the directory tree appears only in README Section 4; no SRS content change.

### TD-03 Document length
- **Feedback:** Document is 35 pages, too long versus the 6–9 page guideline.
- **Decision:** PARTLY FIX. The BT1 PDF was reduced from 35 to 29 pages (API contract and directory tree moved to the repo, TD-02; table of contents resized). The full design record stays in `docs/` as the single source of truth. **The BT2 report follows the 6–9 page guideline**: it summarises and links to the repo documents instead of repeating them.
- **Reason:** The remaining BT1 pages were mandatory diagrams (use case, architecture, ERD, three wireframes) and the traceability matrix; shrinking them further would have made them unreadable.
- **Impact:** No content removed from repo documents; BT2 and BT3 trace against the same files.

### Note — reconciliation of change-log locations (internal decision, not lecturer feedback)
- **Feedback:** N/A — internal documentation decision.
- **Decision:** KEEP this file as the authoritative detailed log; README Section 8 only points to it.
- **Reason:** Session 8 mandates the evidence live in `docs/thay-doi-thiet-ke.md` with TD-xx codes; to avoid two parallel "single sources of truth", README Section 8 becomes a summary table with a link to this file.
- **Impact:** README gains a pointer to `docs/thay-doi-thiet-ke.md`; no other content changes.

## BT2 implementation changes

### TD-04 Choose full-CRUD entities for BT2
- **Change:** Implement full CRUD for `appointment` and `technician_skill`.
- **Reason:** BT2 rubric item [SE] S1 requires at least two entities with full CRUD.
- **Impact:** Adds appointment read/list/detail and soft-delete endpoints; adds technician skill CRUD endpoints, service/repository classes, tests, and traceability updates. `ticket` remains seeded sample data from L2 and is not expanded into full ticket CRUD.

### TD-05 Appointment soft delete
- **Change:** Add `appointment.is_deleted BOOLEAN NOT NULL DEFAULT FALSE`. The DELETE endpoint sets `is_deleted = TRUE` instead of physically removing the row. Default appointment lists and conflict checks exclude soft-deleted appointments.
- **Reason:** BT2 requires a Delete operation for appointment, but appointment history should remain traceable.
- **Impact:** ERD, DDL, migration, API contract, appointment repository/service, tests.

### TD-06 Technician skill CRUD
- **Change:** Implement CRUD endpoints under `/api/technicians/{technician_id}/skills`. Delete removes the skill row because technician skill is configuration data supporting eligibility and is not protected by QT-13.
- **Reason:** A second full-CRUD entity is required. `technician_skill` directly supports QT-08, which requires proficiency ≥ 3 for qualified technicians.
- **Impact:** API contract, SRS traceability, technician skill repository/service, tests.

### TD-07 Minimal demo authentication
- **Change:** Implement minimal demo authentication for the prototype. The token carries `role` and `center_id`. This is not production authentication.
- **Reason:** BT2 extension requires basic login, and QT-14 requires center scoping.
- **Impact:** `POST /api/auth/login` (FR12/US14, TD-14), token dependencies in `src/security.py`, README demo credentials, and center-scoped access control in services.

### TD-08 Normalize tag/version references
- **Change:** BT2 submission tag uses `v0.2`. BT1 was submitted as a PDF and has no Git tag (correction, Session 12: an earlier version of this entry named a `v0.1` baseline tag that was never created). Product-version text inside SRS/API documents uses “BT2 prototype” where appropriate.
- **Reason:** Official BT2 tag is `v0.2`. Previous references to `v0.5` were mistaken or should refer to the BT1 baseline.
- **Impact:** README, SRS, API contract, and other docs only. No business logic changes.

## BT2 Implementation Alignments (Session 10-12)

### TD-09 Align appointment create status to `DA_XAC_NHAN`
- **Change:** Updated `AppointmentService.create_appointment` to set `trang_thai = DA_XAC_NHAN`.
- **Reason:** BT1 SRS (US5 AC1), API contract (§3.5), and Wireframe M3 all specified that confirmed appointments are created as `DA_XAC_NHAN`. The initial BT2 implementation incorrectly used `DA_DAT`.
- **Impact:** Code only. Aligns implementation with approved BT1 design.

### TD-10 Restrict PATCH appointment status
- **Change:** Restricted `AppointmentUpdate` schema Literal to only allow `DA_XAC_NHAN`.
- **Reason:** API contract §3.6 states that in v0.2, `trang_thai` may only be updated to `DA_XAC_NHAN`. Cancellation statuses are deferred to US10.
- **Impact:** Code and API contract clarification. Prevents managers from setting deferred statuses via API.

### TD-11 Enforce reassignment reason length
- **Change:** Added length validation (`len(reason) < 5 or len(reason) > 255`) in `TicketAssignmentService.reassign_technician`.
- **Reason:** API contract validation table specifies `reason` must be 5–255 characters. Initial implementation only checked for non-empty strings.
- **Impact:** Code only. Enforces QT-07 strictly as specified in the contract.

### TD-12 Implement NFR5 service-layer transaction boundary
- **Change:** Refactored `TicketRepository` and `TicketStatusLogRepository` to accept an optional shared `conn` parameter. `TicketAssignmentService` now opens a single `with get_connection() as conn:` block to coordinate both writes atomically (later refined by TD-17: the transaction factory is injected).
- **Reason:** Architecture rationale #4 claimed that ticket updates and status log inserts are wrapped in one database transaction (NFR5). However, repositories were opening independent connections, risking partial commits if the log insert failed.
- **Impact:** Code and test fakes. Fulfills the NFR5 reliability promise made in BT1.

### TD-13 Qualified-technician response shape and `log_id`
- **Change:** Wrapped the service response in `QualifiedTechnicianList` schema. Added `log_id` to `TicketAssignmentRead` schema, populated from the status log repository.
- **Reason:** API contract §3.2 specified the qualified technicians response should be wrapped in `{ "ticket_id": ..., "items": [...] }`. Contract §3.3/3.4 specified the assignment response should include the new `log_id`.
- **Impact:** Code, schemas, and API tests. The M2 page was not updated at the same time and rendered blank until BUG-004 was fixed (TD-25).

### TD-14 Traceability for demo auth and technician_skill CRUD
- **Change:** Added FR12 and US14 to SRS for minimal demo auth. Added reconciliation notes to API contract and Wireframe mapping explaining the `technician_skill` CRUD scope adjustment.
- **Reason:** API contract self-check requires every endpoint to trace to a User Story. `POST /api/auth/login` lacked traceability. Additionally, `technician_skill` CRUD was added in BT2, contradicting the BT1 "imported master data" assumption.
- **Impact:** SRS (bumped to v0.5), API contract, Wireframe mapping. Ensures 100% traceability matrix compliance.

## BT2 Finalisation (Session 12)

### TD-15 Executable migrations in `db/migrations/`
- **Change:** `scripts/migrate.py` used to execute `docs/ddl_l4.sql` and never ran the soft-delete migration. Migrations are now `001_init_schema.sql` (BT1 DDL, made re-runnable) and `002_add_appointment_soft_delete.sql` (TD-05), applied in order and recorded in a `schema_migrations` table. `docs/ddl_l4.sql` stays as the consolidated design schema; both produce an identical schema (checked with `pg_dump -s`).
- **Reason:** BT2 S3/C5: migrations must build the database from empty and be safe to re-run, in a clear order.
- **Impact:** `db/migrations/`, `scripts/migrate.py`, README step 4.

### TD-16 Architecture as built differs from the BT1 directory plan
- **Change:** BT1 planned `presentation/controllers`, `presentation/views`, `domain/`, `TechnicianSuggestionService`, `AccessControl`, repository interfaces with `Mem*` implementations, and SQLAlchemy. As built: `src/routes/` are the controllers, `src/schemas/` (Pydantic) are the format validators, suggestion logic lives in `TicketAssignmentService`, access control is the token dependencies in `src/security.py` plus center checks in each service, in-memory fakes live in `tests/fakes.py`, data access uses psycopg 3 with plain SQL, and the views are a separate React app in `frontend/`.
- **Reason:** FastAPI's router/dependency model already provides the controller and validator layers; one service per use-case group kept the code small enough to explain line by line.
- **Impact:** `docs/architecture-thuc-te.md` + `architecture-thuc-te.drawio` (as-built diagram); `erd_l4_en.drawio` gains `appointment.is_deleted` (TD-05); the layer rules of BT1 are unchanged (routes → services → repositories, no HTTP in services, no rules in repositories).

### TD-17 Transaction boundary injected into the service; guarded assignment
- **Change:** Refines TD-12. `TicketAssignmentService` no longer imports the database module; a unit-of-work factory (`src/repositories/transaction.py`) is injected. The assignment UPDATE only matches a ticket that is still unassigned (reassignment: still held by the expected technician); otherwise `ticket_not_assignable` and no log row.
- **Reason:** C2 (no data-layer code in services) and C4 (three unit tests needed a live PostgreSQL). The guard closes a check-then-update race on QT-07.
- **Impact:** `ticket_assignment_service.py`, `ticket_repository.py`, `routes/tickets.py`, tests; SRS design note 9.

### TD-18 Missing reassignment reason returns 422
- **Change:** `reason` is optional in the request schema, so an omitted reason reaches the service and returns `422 reason_required` (it returned `400 bad_request` before).
- **Reason:** API contract §4 and BT1 feedback ("thiếu lý do 422"): a missing reason is a QT-07 business violation, not a malformed request.
- **Impact:** `schemas/ticket.py`, `ticket_assignment_service.py`, `test_api.py`, `test_bt2_three_types.py`.

### TD-19 Two supporting read endpoints
- **Change:** Added `GET /api/tickets/{ticket_id}` (read-only ticket summary) and `GET /api/issue-categories` (active categories).
- **Reason:** Wireframes M2/M3 show a ticket summary block, and the M1 category filter must come from the `issue_category` table (NFR7), not from a list hard-coded in the frontend.
- **Impact:** API contract §3.17–3.18 (trace US2/US4 and US8); new route/service/repository code; frontend M1–M3.

### TD-20 Conflict pre-check endpoint and conflict details implemented
- **Change:** Implemented `GET /api/appointments/conflicts` (contract 3.7) and the `conflicts` list in the `409 appointment_conflict` body (contract 3.5) — both were specified in BT1 but missing in code. The contract code `ticket_not_found_or_unassigned` is replaced by the two codes the service actually distinguishes: `404 ticket_not_found` and `422 ticket_not_assignable`.
- **Reason:** Rubric criterion 3 (code must match the BT1 design or document the difference); UC4 step 5 warns before saving.
- **Impact:** appointment repository/service/routes, API contract §3.5, M3 conflict banner.

### TD-21 QT-15 / NFR4 phone masking implemented
- **Change:** `src/services/phone_masking.py` masks `customer_phone` as `090****567` for every role except `CENTER_MANAGER` and `BOARD_OF_DIRECTORS`, in the ticket list and ticket detail responses.
- **Reason:** NFR4 (100% of phones returned to non-manager roles masked) was specified but not implemented. All demo accounts are managers, so the API output for them is unchanged; tests use a token with another role.
- **Impact:** service layer, `tests/test_phone_masking.py`, `test_api.py`.

### TD-22 Error envelope: 503 and request id
- **Change:** A database outage returns `503 database_unavailable` instead of a generic 500; unexpected errors return `500 internal_error` with a `request_id` that matches the server log; `/health` reports `{"status":"ok","database":"up|down"}`; filter values (`priority`, `trang_thai`) are validated (400).
- **Reason:** Grading step 5 (turn off a component → clear, controlled error) and C7.
- **Impact:** `src/main.py`, `src/db.py`, `src/errors.py`, API contract §1.

### TD-23 Sample data from the course dataset
- **Change:** The hand-written seed (7 tickets, `PB-1-00001` codes) is replaced by `data/sample/` built from the course dataset (seed 20260901) and `gen_sample.py` (seed 42): 6 categories, 38 technicians, 159 skills, 487 tickets, 1,330 status logs, 74 appointments, plus 6 upcoming demo appointments. Ticket codes follow the ERD format `BH-000123/2026`.
- **Reason:** Course guidance (≥ 20–30 rows per main table, data traceable to the case study, seeds recorded); the dataset has no `MOI` tickets, so 60 are generated; generated appointments take technician and center from their ticket (gen_sample picks them at random) and overlaps are dropped.
- **Impact:** `tools/`, `scripts/build_sample.py`, `scripts/seed.py`, SRS §1.5 and design note 8, README section 7.

### TD-24 Appointment read model
- **Change:** Appointment responses add `ticket_code` and `technician_ho_ten`; the list is ordered newest date first.
- **Reason:** M3 must show the ticket and technician (wireframe), not raw ids; upcoming appointments should appear on page 1.
- **Impact:** appointment repository and schema, API contract §3.8.

### TD-25 Frontend rebuilt to match the wireframes
- **Change:** M1 gains filters, all wireframe columns, SLA time left, pagination and two distinct empty states; M2 gains the ticket summary, radio selection, reassignment reason and "Schedule appointment → M3"; M3 gains the ticket summary, live conflict pre-check, edit and soft-delete. UI text is Vietnamese only; code identifiers are English and API fields keep ERD column names. Tailwind is installed via npm (pinned) instead of a CDN script.
- **Reason:** BT2 S4 (three states, distinguish "no data" from "filter matched nothing") and wireframe consistency; M2 was broken by the TD-13 response change.
- **Impact:** `frontend/src/` (api, pages, components, hooks, labels), `docs/wireframe_mapping_en.md`.

### TD-26 Document file names follow the rubric
- **Change:** `srs_en.md` → `srs.md`, `thay-doi-thiet-ke_en.md` → `thay-doi-thiet-ke.md`, `ai-disclosure_en.md` → `ai-disclosure.md`, `api_contract_en.md` → `api-contract.md`; added `architecture-thuc-te.md` and `bug-log.md`.
- **Reason:** BT2 minimum repository structure names these files exactly; BT1 feedback named `api-contract.md`.
- **Impact:** `docs/` only; all references updated.

### TD-27 Docker packaging (prepared for BT3)
- **Change:** `Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml` (db · api · web with health checks); the api container runs migrate → seed → uvicorn.
- **Reason:** BT2 TP4 "high evaluation" level (system up in ≤ 2 commands) and direct preparation for BT3.
- **Impact:** repository root, README "Run with Docker".

### TD-28 Line endings normalised
- **Change:** `.gitattributes` forces LF for all text files.
- **Reason:** Windows checkouts showed every file as modified (CRLF only), and CRLF breaks shell scripts inside Linux containers.
- **Impact:** repository-wide, no content change.


### TD-29 Technician skill list shape follows the contract
- **Change:** `GET /api/technicians/{technician_id}/skills` returns `{ "technician_id", "items": [...] }` as written in API contract 3.11; it returned a bare array before.
- **Reason:** Rubric criterion 3 — the implementation must match the BT1/BT2 contract.
- **Impact:** `technician_skill_service.py`, `schemas/technician_skill.py`, `routes/technician_skills.py`, two tests.

### TD-30 Consistency pass on the documentation
- **Change:** Corrected statements that contradicted the code or each other: US1 AC3 / NFR3 (lists are filtered by the token's center; only direct record access returns 403), QT-04 working-day clause restored in the SRS, FR10 shown as API-only in the traceability matrix, API-contract validation table now lists error codes (the contract) instead of message wording, response time format `HH:MM:SS`, 3.2/3.3/3.6/3.8 error lists, use-case UC3 preconditions and reason length, BT1 architecture index names, BT1 file names in the AI disclosure, TD-02/TD-07/TD-08 wording, BUG-001 root cause (reproduced: collision on `ticket_status_log`, not `appointment`); TD-04 … TD-14 relabelled to the three-line format and TD-13's impact corrected (it had claimed the frontend was aligned, see BUG-004).
- **Reason:** Rubric criterion 3 — documents must match the implementation; found in a document-versus-code review in Session 12.
- **Impact:** `docs/` text and `.drawio` sources only; no code change.

