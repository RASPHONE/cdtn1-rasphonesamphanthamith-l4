# `docs/api-contract.md` — API Contract (L4, Track SE, BT2 target tag v0.2)

Updated for BT2. Every business endpoint traces to a User Story in SRS §6.2.
Companion artifacts: `docs/srs.md` (v0.6), `docs/erd_l4_en.dbd`, `docs/ddl_l4.sql`,
`docs/wireframes_l4_en.drawio` (M1–M3).

## 1. Common conventions

- Base path: `/api` (local: `http://localhost:8000/api`).
- Format: JSON only; field names in `snake_case`, identical to ERD column names.
- Timestamps ISO 8601 (`received_at`, `due_date`); dates `YYYY-MM-DD` (`ngay_hen`);
  times: requests accept `HH:MM`, responses return `HH:MM:SS` (`gio_bat_dau`, `gio_ket_thuc`).
- Pagination: query `page` (default 1), `page_size` (default 20, max 100);
  responses carry `page`, `page_size`, `total`.
- Authentication: Bearer JWT from the demo login (endpoint 16; a production identity
  provider is out of scope). The caller's `center_id` and `role` are derived
  server-side from the token and NEVER accepted from the client (QT-14, NFR3):
  list endpoints are filtered to the caller's center; requests addressing a record
  of another center return 403.
- Phone numbers: full for Center Manager / Board of Directors; masked
  `090****567` for every other role (QT-15). Masking is applied in the Service
  layer before the response leaves.
- Error envelope: `{ "error": "<machine_code>", "message": "<human text>" }`.
  The `error` code is the contract; `message` is explanatory English text and may be
  reworded. The UI shows its own Vietnamese text per code.
  Optional extras: `details` (list of `{field, message}`), `conflicts` (409) or
  `request_id` (500, matches the server log line). Stack traces, SQL and driver
  messages are never returned.
- Status codes: `200` read/update ok · `201` created · `400` malformed or missing
  field · `403` cross-center · `404` not found · `409` appointment overlap ·
  `422` business-rule violation (QT-xx / CON-xx) · `500 internal_error` ·
  `503 database_unavailable` (PostgreSQL unreachable).
- Implementation: `src/routes/` (HTTP), `src/services/` (rules, no HTTP),
  `src/repositories/` (SQL); the code → HTTP mapping is `HTTP_BY_CODE` in `src/errors.py`.

## 2. Endpoint list and traceability

| # | Method | Path | US | FR | UC |
|---|---|---|---|---|---|
| 1 | GET | `/api/tickets/unassigned` | US1, US8 | FR1, FR9 | UC1 |
| 2 | GET | `/api/tickets/{ticket_id}/qualified-technicians` | US2, US3 | FR2, FR8 | UC2 |
| 3 | POST | `/api/tickets/{ticket_id}/assignment` | US4 | FR3, FR4 | UC3 |
| 4 | PATCH | `/api/tickets/{ticket_id}/assignment` | US4 | FR5 | UC3 |
| 5 | POST | `/api/appointments` | US5, US6 | FR6, FR7 | UC4 |
| 6 | PATCH | `/api/appointments/{appointment_id}` | US5, US6 | FR6, FR7 | UC4 |
| 7 | GET | `/api/appointments/conflicts` | US6 | FR7 | UC4 |
| 8 | GET | `/api/appointments` | US5, US13 | FR6, FR7, FR11 | UC4 |
| 9 | GET | `/api/appointments/{appointment_id}` | US5, US13 | FR6, FR11 | UC4 |
| 10 | DELETE | `/api/appointments/{appointment_id}` | US13 | FR11 | UC4 |
| 11 | GET | `/api/technicians/{technician_id}/skills` | US12 | FR10 | UC2 |
| 12 | GET | `/api/technicians/{technician_id}/skills/{category_id}` | US12 | FR10 | UC2 |
| 13 | POST | `/api/technicians/{technician_id}/skills` | US12 | FR10 | UC2 |
| 14 | PATCH | `/api/technicians/{technician_id}/skills/{category_id}` | US12 | FR10 | UC2 |
| 15 | DELETE | `/api/technicians/{technician_id}/skills/{category_id}` | US12 | FR10 | UC2 |
| 16 | POST | `/api/auth/login` | US14 | FR12 | UC1–UC4 (precondition) |
| 17 | GET | `/api/tickets/{ticket_id}` | US2, US4, US5 | FR2, FR6 | UC3, UC4 (M2/M3 summary) |
| 18 | GET | `/api/issue-categories` | US8 | FR9 | UC1 (M1 filter, NFR7) |
| 19 | GET | `/health` | — (infrastructure) | — | — |

No surplus business endpoints: rows 1–15, 17 and 18 each serve at least one User Story
in the SRS matrix. Rows 16 (`/api/auth/login`) and 19 (`/health`) are infrastructure:
login is the precondition of every use case (US14/FR12), and `/health` serves the
packaging and grading checks (README section 6, Docker health checks) — neither carries
business logic.
Endpoints 17–18 were added in BT2 (TD-19) to feed the wireframe summary blocks and the M1 category filter without hard-coded data. Endpoint 19 is an infrastructure health check.
Endpoint 16 is minimal demo authentication required by BT2. It is infrastructure supporting QT-14 center scoping for endpoints 1–15. It is not a production authentication provider.

## 3. Endpoint details

### 3.1 GET /api/tickets/unassigned
Query: `page`, `page_size`, optional `category_id`, optional `priority` (FR9).
Server-side filter is fixed: `status = MOI`, `technician_id IS NULL`,
`is_warranty = true`, `is_deleted = false`, `center_id = caller center`,
sorted `due_date` ASC (FR1).

- 200:
```json
{ "page": 1, "page_size": 20, "total": 57,
  "items": [ { "ticket_id": 123, "ticket_code": "BH-000123/2026",
               "customer_name": "Nguyen Van An", "customer_phone": "0901234567",
               "serial_no": "SN123456789012", "category_id": 1,
               "category_name": "MAN_HINH", "priority": "CAO",
               "received_at": "2026-09-08T08:00:00+07:00",
               "due_date": "2026-09-09T08:00:00+07:00" } ] }
```
- 400 `bad_request` — invalid page/page_size, `category_id` < 1, or `priority`
  outside `CAO|TRUNG_BINH|THAP` (`details` names the field).
- `customer_phone` is masked `090****567` unless the caller's role is
  `CENTER_MANAGER` or `BOARD_OF_DIRECTORS` (QT-15 / NFR4).

### 3.2 GET /api/tickets/{ticket_id}/qualified-technicians
- 200:
```json
{ "ticket_id": 123,
  "items": [ { "technician_id": 7, "technician_code": "KT007",
               "ho_ten": "Le Van Cuong", "level": "TRUNG_CAP",
               "proficiency": 4, "workload": 6 } ] }
```
`workload` is computed at query time (SRS terminology: assigned tickets in
`DA_PHAN_CONG` / `DANG_XU_LY` / `CHO_LINH_KIEN`); it is never stored.
- 403 `cross_center_access` · 404 `ticket_not_found`
- 422 `ticket_not_assignable` — not a warranty ticket, or ticket closed (`HOAN_TAT` / `DA_DONG` / `DA_HUY`).

### 3.3 POST /api/tickets/{ticket_id}/assignment  (first assignment)
Request: `{ "technician_id": 7, "reason": null }` (`reason` ignored here).
Ticket must be a warranty ticket in status `MOI` with no technician yet (QT-06, QT-07);
the UPDATE only matches such a row, so a concurrent assignment loses with 422.
- 200: `{ "ticket_id": 123, "technician_id": 7, "status": "DA_PHAN_CONG", "log_id": 4501 }`
- 400 `bad_request` · 403 `cross_center_access` · 404 `ticket_not_found`
- 422 `technician_not_qualified` — QT-08 (same center + proficiency ≥ 3).
- 422 `ticket_not_assignable` — not `MOI`, already assigned (also by a concurrent request), not warranty, or closed.

### 3.4 PATCH /api/tickets/{ticket_id}/assignment  (reassignment)
Request: `{ "technician_id": 9, "reason": "KTV nghi phép dài hạn" }` — `reason`
mandatory (QT-07).
- 200: same shape as 3.3 with a new `log_id`.
- 422 `reason_required` — "Reason is required when changing technician (5-255 characters)." (QT-07).
  Returned both when `reason` is omitted and when it is shorter than 5 / longer than 255
  characters after trimming. `details: [{"field": "reason", ...}]`.
- 422 `ticket_not_assignable` — ticket not currently assigned, closed, or changed by
  someone else since it was read (concurrent update guard).
- 422 `technician_not_qualified` (QT-08) · 403 · 404 · 400.

### 3.5 POST /api/appointments
Request: `{ "ticket_id": 123, "loai": "NHAN_MAY", "ngay_hen": "2026-09-15",
            "gio_bat_dau": "08:00", "gio_ket_thuc": "10:00" }`
`technician_id` and `center_id` are derived server-side from the assigned ticket
(not client-supplied). Save performs the authoritative conflict check over
active appointments (`DA_DAT` / `DA_XAC_NHAN`, same technician, same `ngay_hen`,
overlapping interval).
- 201: `{ "appointment_id": 88, "ticket_id": 123, "ticket_code": "BH-000123/2026",
          "technician_id": 7, "technician_ho_ten": "Le Van Cuong", "center_id": 2,
          "loai": "NHAN_MAY", "trang_thai": "DA_XAC_NHAN", "ngay_hen": "2026-09-15",
          "gio_bat_dau": "08:00:00", "gio_ket_thuc": "10:00:00", "is_deleted": false }`
- 400 `bad_request` (missing/malformed field) · 403 `cross_center_access` · 404 `ticket_not_found`
- 422 `ticket_not_assignable` — ticket has no technician, is not a warranty ticket, or is closed.
- 409 `appointment_conflict` — FR7; body includes `conflicts: [ {appointment_id, ticket_id, ngay_hen, gio_bat_dau, gio_ket_thuc, trang_thai} ]`.
  Intervals that only touch (09:00–10:00 then 10:00–11:00) do not conflict.
- 422 `appointment_type_deferred` — `KIEM_TRA_TAI_CHO` not creatable in v0.2.
- 422 `appointment_in_past` — "Appointment time must be in the future." (US5 AC2)
- 422 `invalid_time_range` — CON-01 (`gio_ket_thuc > gio_bat_dau`).

### 3.6 PATCH /api/appointments/{appointment_id}
Request: optional subset `{ "loai", "ngay_hen", "gio_bat_dau", "gio_ket_thuc", "trang_thai" }`.
In v0.2 `trang_thai` may **only** be set to `DA_XAC_NHAN` (confirm); cancellation
statuses (`KHACH_HUY`, `KHACH_KHONG_DEN`) are deferred with US10.
Conflict check excludes the appointment being updated.
- 200 updated object · 409 `appointment_conflict` (with `conflicts`) · 422 (same codes as 3.5)
  · 422 `appointment_completed_cannot_update` (`trang_thai = HOAN_TAT`)
  · 403 · 404 `appointment_not_found` (missing or soft-deleted) · 400.

### 3.7 GET /api/appointments/conflicts
Query: `technician_id`, `ngay_hen`, `gio_bat_dau`, `gio_ket_thuc`,
optional `exclude_appointment_id`.
Purpose: lets M3 show the warning before save (UC4 step 5); the save-time check
in 3.5/3.6 remains authoritative.
- 200: `{ "conflicts": [ {appointment_id, ticket_id, ngay_hen, gio_bat_dau, gio_ket_thuc, trang_thai} ] }` (empty array when none).
- 400 `bad_request` · 403 `cross_center_access` (technician outside caller center)
  · 404 `technician_not_found` · 422 `invalid_time_range`.

### 3.8 GET /api/appointments

Query: `page`, `page_size`, optional `technician_id`, optional `ticket_id`,
optional `ngay_hen`, optional `trang_thai`, optional `include_deleted`.

Default filter: `include_deleted=false`, so soft-deleted appointments are excluded.
Order: `ngay_hen` DESC, `gio_bat_dau` DESC (upcoming and recent first).
Each item also carries `ticket_code` and `technician_ho_ten` for display (TD-24).
Server-side center scoping applies from the caller token (QT-14).

- 200:
```json
{ "page": 1, "page_size": 20, "total": 12,
  "items": [ { "appointment_id": 88, "ticket_id": 123, "ticket_code": "BH-000123/2026",
               "technician_id": 7, "technician_ho_ten": "Le Van Cuong",
               "center_id": 2, "loai": "NHAN_MAY", "trang_thai": "DA_XAC_NHAN",
               "ngay_hen": "2026-09-15", "gio_bat_dau": "08:00:00",
               "gio_ket_thuc": "10:00:00", "is_deleted": false } ] }
```
- 400 `bad_request` — invalid pagination/filter (`trang_thai` must be one of CON-03).
- Only the caller's center is listed (QT-14); there is no center parameter, so no 403 here.

### 3.9 GET /api/appointments/{appointment_id}

- 200: appointment object.
- 403 `cross_center_access`.
- 404 `appointment_not_found` — does not exist or is soft-deleted when `include_deleted=false`.

### 3.10 DELETE /api/appointments/{appointment_id}

Soft delete. Sets `appointment.is_deleted = true`. Does not physically remove the row.

- 200:
```json
{ "appointment_id": 88, "is_deleted": true }
```
- 403 `cross_center_access`.
- 404 `appointment_not_found` — already deleted or does not exist.
- 422 `appointment_completed_cannot_delete` — `trang_thai = HOAN_TAT`. completed appointments cannot be soft-deleted.

### 3.11 GET /api/technicians/{technician_id}/skills

Returns the skill list of one technician. Center scoping applies.

- 200:
```json
{ "technician_id": 7,
  "items": [ { "technician_id": 7, "category_id": 1, "category_name": "MAN_HINH", "proficiency": 4 } ] }
```
- 403 `cross_center_access`.
- 404 `technician_not_found`.

### 3.12 GET /api/technicians/{technician_id}/skills/{category_id}

- 200:
```json
{ "technician_id": 7, "category_id": 1, "category_name": "MAN_HINH", "proficiency": 4 }
```
- 403 `cross_center_access`.
- 404 `technician_not_found` or `skill_not_found`.

### 3.13 POST /api/technicians/{technician_id}/skills

Request:

```json
{ "category_id": 1, "proficiency": 4 }
```

- 201: created skill object.
- 400 `bad_request` — missing/malformed field.
- 403 `cross_center_access`.
- 404 `technician_not_found` or `category_not_found`.
- 409 `skill_already_exists` — duplicate `(technician_id, category_id)`.
- 422 `proficiency_out_of_range` — not between 1 and 5.
- 422 `category_inactive` — issue category is not active.

### 3.14 PATCH /api/technicians/{technician_id}/skills/{category_id}

Request:

```json
{ "proficiency": 5 }
```

- 200: updated skill object.
- 403 `cross_center_access`.
- 404 `technician_not_found` or `skill_not_found`.
- 422 `proficiency_out_of_range`.

### 3.15 DELETE /api/technicians/{technician_id}/skills/{category_id}

Removes the skill row.

- 204: deleted.
- 403 `cross_center_access`.
- 404 `technician_not_found` or `skill_not_found`.

### 3.16 POST /api/auth/login

Minimal demo authentication for BT2. Not production authentication.

Request:

```json
{ "username": "manager1", "password": "..." }
```

- 200:
```json
{ "access_token": "...", "token_type": "bearer",
  "role": "CENTER_MANAGER", "center_id": 1 }
```
- 401 `invalid_credentials`.

### 3.17 GET /api/tickets/{ticket_id}

Read-only ticket summary for M2 and M3 (TD-19). Center scoping and QT-15 masking apply.

- 200: the fields of 3.1 plus `status`, `technician_id`, `technician_ho_ten`, `closed_at`.
- 403 `cross_center_access` · 404 `ticket_not_found` (missing or soft-deleted).

### 3.18 GET /api/issue-categories

Active issue categories for the M1 filter (FR9). Read from `issue_category`, so a
category added by one INSERT appears with zero code changes (NFR7).

- 200: `[ { "category_id": 1, "category_name": "MAN_HINH", "default_priority": "CAO" } ]`
- 401 `unauthorized`.

### 3.19 GET /health

Infrastructure check, no authentication.

- 200: `{ "status": "ok", "database": "up" }` — `database` is `"down"` when PostgreSQL
  cannot be reached (the API itself still answers).

## 4. Validation table

Format errors are rejected by the request schemas with `400 bad_request` and a
`details` entry naming the field; business rules are checked in the service layer.

| Endpoint | Field | Required | Type | Rule | Error code (HTTP) |
|---|---|---|---|---|---|
| 3.3 / 3.4 | `technician_id` | yes | int | exists, active, same center, proficiency ≥ 3 (QT-08) | `technician_not_found` (404) · `technician_not_qualified` (422) |
| 3.4 | `reason` | yes (reassign) | string 5–255 after trim | omitted, blank, < 5 or > 255 | `reason_required` (422) |
| 3.5 / 3.6 | `loai` | yes | enum | `GIAO_MAY` / `NHAN_MAY` in v0.2 | `bad_request` (400) unknown value · `appointment_type_deferred` (422) `KIEM_TRA_TAI_CHO` |
| 3.5 / 3.6 | `ngay_hen` + `gio_bat_dau` | yes | date + time | strictly after now (APP_TIMEZONE) | `appointment_in_past` (422) |
| 3.5 / 3.6 / 3.7 | `gio_bat_dau`, `gio_ket_thuc` | yes | time | CON-01 end > start | `invalid_time_range` (422) |
| 3.1 | `category_id`, `priority` | no | int ≥ 1 / enum `CAO\|TRUNG_BINH\|THAP` | valid value | `bad_request` (400) |
| 3.1 / 3.8 | `page`, `page_size` | no | int | ≥ 1 / 1–100 | `bad_request` (400) |
| 3.8 | `trang_thai` | no | enum | CON-03 values | `bad_request` (400) |
| 3.7 | `technician_id` | yes | int | exists, in caller's center | `technician_not_found` (404) · `cross_center_access` (403) |
| 3.10 | `appointment_id` | yes | int | exists, not soft-deleted, not completed | `appointment_not_found` (404) · `appointment_completed_cannot_delete` (422) |
| 3.13 | `category_id` | yes | int | exists and active | `category_not_found` (404) · `category_inactive` (422) |
| 3.13 / 3.14 | `proficiency` | yes | int | 1–5 (CON-04) | `proficiency_out_of_range` (422) |
| 3.13 | `(technician_id, category_id)` | — | composite | unique | `skill_already_exists` (409) |
| 3.16 | `username`, `password` | yes | string | valid demo user | `invalid_credentials` (401) |

## 5. Notes

- Business rules appear as 422/409 codes and validation rows (QT-06, QT-07,
  QT-08, QT-14, QT-15, CON-01), so BT3 test cases trace FR → US → AC → TC
  including exception paths.
- Concurrency: appointment conflict detection is a service-layer check (SRS §5
  note 1); two simultaneous appointment submits for the same slot are
  theoretically possible and accepted in v0.2 (one manager per center).
  Assignment is protected: the guarded UPDATE lets only one concurrent request
  win (SRS §5 note 9).

- **BT2 Scope Adjustments:** 
  - `technician_skill` CRUD (`POST/PATCH/DELETE /api/technicians/{id}/skills`) was added in BT2 to satisfy the requirement that at least two entities support full CRUD. In BT1, this was assumed to be imported master data. This is an API-only admin support feature; no new UI screen is introduced.
  - `POST /api/auth/login` was added as infrastructure to support QT-14 center scoping via JWT tokens.
