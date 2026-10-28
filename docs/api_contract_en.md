# `docs/api_contract_en.md` — API Contract (L4, Track SE, BT2 target tag v0.2)

Updated for BT2. Every business endpoint traces to a User Story in SRS §6.2.
Companion artifacts: `docs/srs_en.md` (v0.3), `docs/erd_l4_en.dbd`, `docs/ddl_l4.sql`,
`docs/wireframes_l4_en.drawio` (M1–M3).

## 1. Common conventions

- Base path: `/api` (local: `http://localhost:8000/api`).
- Format: JSON only; field names in `snake_case`, identical to ERD column names.
- Timestamps ISO 8601 (`received_at`, `due_date`); dates `YYYY-MM-DD` (`ngay_hen`);
  times `HH:MM` (`gio_bat_dau`, `gio_ket_thuc`).
- Pagination: query `page` (default 1), `page_size` (default 20, max 100);
  responses carry `page`, `page_size`, `total`.
- Authentication: Bearer token (infrastructure, out of scope). The caller's
  `center_id` is derived server-side from the token and NEVER accepted from the
  client (QT-14, NFR3).
- Phone numbers: full for Center Manager / Board of Directors; masked
  `090****567` for every other role (QT-15). Masking is applied in the Service
  layer before the response leaves.
- Error envelope: `{ "error": "<machine_code>", "message": "<human text>" }`,
  plus optional `details` or `conflicts`.
- Status codes: `200` read/update ok · `201` created · `400` malformed or missing
  field · `403` cross-center · `404` not found · `409` appointment overlap ·
  `422` business-rule violation (QT-xx / CON-xx).

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

No surplus endpoints: every row serves at least one User Story in the SRS matrix.
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
- 400 `bad_request` — invalid page/page_size.
- 403 `cross_center_access` — QT-14 / NFR3.

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
- 403 `cross_center_access` · 404 `ticket_not_found`.

### 3.3 POST /api/tickets/{ticket_id}/assignment  (first assignment)
Request: `{ "technician_id": 7, "reason": null }` (`reason` ignored here).
Ticket must be assignable (status not `DA_DONG` / `DA_HUY`, QT-06).
- 200: `{ "ticket_id": 123, "technician_id": 7, "status": "DA_PHAN_CONG", "log_id": 4501 }`
- 400 `bad_request` · 403 `cross_center_access` · 404 `ticket_not_found`
- 422 `technician_not_qualified` — QT-08 (same center + proficiency ≥ 3).
- 422 `ticket_not_assignable` — QT-06 lifecycle.

### 3.4 PATCH /api/tickets/{ticket_id}/assignment  (reassignment)
Request: `{ "technician_id": 9, "reason": "KTV nghi phép dài hạn" }` — `reason`
mandatory (QT-07).
- 200: same shape as 3.3 with a new `log_id`.
- 422 `reason_required` — "Reason is required when changing technician." (QT-07)
- 422 `technician_not_qualified` (QT-08) · 403 · 404 · 400.

### 3.5 POST /api/appointments
Request: `{ "ticket_id": 123, "loai": "NHAN_MAY", "ngay_hen": "2026-09-15",
            "gio_bat_dau": "08:00", "gio_ket_thuc": "10:00" }`
`technician_id` and `center_id` are derived server-side from the assigned ticket
(not client-supplied). Save performs the authoritative conflict check over
active appointments (`DA_DAT` / `DA_XAC_NHAN`, same technician, same `ngay_hen`,
overlapping interval).
- 201: `{ "appointment_id": 88, "ticket_id": 123, "technician_id": 7,
          "center_id": 2, "loai": "NHAN_MAY", "trang_thai": "DA_XAC_NHAN",
          "ngay_hen": "2026-09-15", "gio_bat_dau": "08:00", "gio_ket_thuc": "10:00" }`
- 400 `bad_request` (missing/malformed field) · 403 · 404 `ticket_not_found_or_unassigned`
- 409 `appointment_conflict` — FR7; body includes `conflicts: [ {appointment_id, ngay_hen, gio_bat_dau, gio_ket_thuc, trang_thai} ]`.
- 422 `appointment_type_deferred` — `KIEM_TRA_TAI_CHO` not creatable in v0.2.
- 422 `appointment_in_past` — "Appointment time must be in the future." (US5 AC2)
- 422 `invalid_time_range` — CON-01 (`gio_ket_thuc > gio_bat_dau`).

### 3.6 PATCH /api/appointments/{appointment_id}
Request: optional subset `{ "loai", "ngay_hen", "gio_bat_dau", "gio_ket_thuc", "trang_thai" }`.
In v0.2 `trang_thai` may **only** be set to `DA_XAC_NHAN` (confirm); cancellation
statuses (`KHACH_HUY`, `KHACH_KHONG_DEN`) are deferred with US10.
Conflict check excludes the appointment being updated.
- 200 updated object · 409 `appointment_conflict` · 422 (same codes as 3.5)
  · 403 · 404 `appointment_not_found` · 400.

### 3.7 GET /api/appointments/conflicts
Query: `technician_id`, `ngay_hen`, `gio_bat_dau`, `gio_ket_thuc`,
optional `exclude_appointment_id`.
Purpose: lets M3 show the warning before save (UC4 step 5); the save-time check
in 3.5/3.6 remains authoritative.
- 200: `{ "conflicts": [ ... ] }` (empty array when none).
- 400 `bad_request` · 403 `cross_center_access` (technician outside caller center).

### 3.8 GET /api/appointments

Query: `page`, `page_size`, optional `technician_id`, optional `ticket_id`,
optional `ngay_hen`, optional `trang_thai`, optional `include_deleted`.

Default filter: `include_deleted=false`, so soft-deleted appointments are excluded.
Server-side center scoping applies from the caller token (QT-14).

- 200:
```json
{ "page": 1, "page_size": 20, "total": 12,
  "items": [ { "appointment_id": 88, "ticket_id": 123, "technician_id": 7,
               "center_id": 2, "loai": "NHAN_MAY", "trang_thai": "DA_XAC_NHAN",
               "ngay_hen": "2026-09-15", "gio_bat_dau": "08:00",
               "gio_ket_thuc": "10:00", "is_deleted": false } ] }
```
- 400 `bad_request` — invalid pagination/filter.
- 403 `cross_center_access` — QT-14.

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
  "items": [ { "category_id": 1, "category_name": "MAN_HINH", "proficiency": 4 } ] }
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

## 4. Validation table

| Endpoint | Field | Required | Type | Rule | Error (code) |
|---|---|---|---|---|---|
| 3.3 / 3.4 | `technician_id` | yes | int | exists; QT-08 vs ticket | "Technician not qualified for this category/center (QT-08)." (422) |
| 3.4 | `reason` | yes (reassign) | string 5–255 | non-empty | "Reason is required when changing technician." (422) |
| 3.5 / 3.6 | `loai` | yes | enum | `GIAO_MAY` / `NHAN_MAY` in v0.2 | "On-site check appointments are deferred (v0.2)." (422) |
| 3.5 / 3.6 | `ngay_hen` | yes | date | (`ngay_hen` + `gio_bat_dau`) > now | "Appointment time must be in the future." (422) |
| 3.5 / 3.6 | `gio_bat_dau`, `gio_ket_thuc` | yes | HH:MM | CON-01 end > start | "End time must be after start time." (422) |
| 3.1 | `category_id`, `priority` | no | int / enum | valid id / `CAO|TRUNG_BINH|THAP` | "Invalid filter value." (400) |
| 3.1 / 3.7 | `page`, `page_size` | no | int | ≥ 1 / 1–100 | "Invalid pagination parameters." (400) |
| 3.10 | `appointment_id` | yes | int | exists, not soft-deleted, not completed | "Completed appointment cannot be deleted." (422) |
| 3.13 | `category_id` | yes | int | active issue category | "Issue category not found or inactive." (404/422) |
| 3.13 / 3.14 | `proficiency` | yes | int | 1–5 | "Proficiency must be between 1 and 5." (422) |
| 3.13 | `(technician_id, category_id)` | — | composite | unique | "Skill already exists for this technician/category." (409) |
| 3.16 | `username`, `password` | yes | string | valid demo user | "Invalid credentials." (401) |

## 5. Notes

- Business rules appear as 422/409 codes and validation rows (QT-06, QT-07,
  QT-08, QT-14, QT-15, CON-01), so BT3 test cases trace FR → US → AC → TC
  including exception paths.
- Concurrency: conflict detection is a service-layer blocking check (SRS §5
  note 1); a simultaneous double-submit is theoretically possible and is
  accepted in v0.2 (one manager per center).

- **BT2 Scope Adjustments:** 
  - `technician_skill` CRUD (`POST/PATCH/DELETE /api/technicians/{id}/skills`) was added in BT2 to satisfy the requirement that at least two entities support full CRUD. In BT1, this was assumed to be imported master data. This is an API-only admin support feature; no new UI screen is introduced.
  - `POST /api/auth/login` was added as infrastructure to support QT-14 center scoping via JWT tokens.
