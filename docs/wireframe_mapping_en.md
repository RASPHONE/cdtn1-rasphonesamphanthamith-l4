# `docs/wireframe_mapping_en.md` — Wireframe traceability (L4, v0.2)

Source: `docs/wireframes_l4_en.drawio` (3 pages: M1, M2, M3). Grayscale low-fi; PNG exports for the PDF.

## 1. Field ↔ ERD column (both directions)

| Screen | UI element | ERD column |
|---|---|---|
| M1 | filter dropdowns | `issue_category.category_name`, `ticket.priority` |
| M1 | table columns | `ticket.ticket_code`, `customer_name`, `customer_phone`, `serial_no`, `category_id`→name, `priority`, `received_at`, `due_date` |
| M1 | row action [Assign] | opens M2 (UC3) |
| M2 | summary block | `ticket.*` (read-only) |
| M2 | technician table | `technician.ho_ten`, `technician_skill.proficiency` |
| M2 | workload column | computed (NOT stored): count of `ticket` with status DA_PHAN_CONG / DANG_XU_LY / CHO_LINH_KIEN |
| M2 | reason input | `ticket_status_log.note` (write path) |
| M3 | type dropdown | `appointment.loai` (v0.2: GIAO_MAY, NHAN_MAY only) |
| M3 | date/time inputs | `appointment.ngay_hen`, `gio_bat_dau`, `gio_ket_thuc` |
| M3 | read-only summary | `ticket.ticket_code`, `technician.ho_ten`, `appointment.center_id` (system-derived) |
| M3 | confirm button | sets `appointment.trang_thai = DA_XAC_NHAN` |

NOT NULL coverage: appointment's `ticket_id / technician_id / center_id / trang_thai` are system-generated; `loai / ngay_hen / gio_bat_dau / gio_ket_thuc` are M3 inputs; `ticket_status_log` NOT NULL columns are system-written on M2 confirm. Master data (`issue_category`, `technician`, `technician_skill`) is imported from the case-study dataset — no admin screen in v0.2 (NFR7 insert-only).

## 2. Button/action ↔ Use Case

| Action | UC |
|---|---|
| M1 [Apply filters] | UC1 (FR9) |
| M1 [Assign] | UC3 entry |
| M2 [Confirm assignment] | UC3 step 6 |
| M2 [Schedule appointment] | UC4 entry |
| M3 [Save & confirm] | UC4 step 6 |

## 3. Exception ↔ UI location (consistency check 6)

| Exception | UI location |
|---|---|
| UC3-3a no qualified technician | M2 strip 1 (+ Confirm disabled) |
| UC3-5a reason required | M2 strip 2 |
| UC3-7a ineligible technician | M2 validation/rollback area |
| UC3-8a save failed rollback | M2 validation/rollback area |
| UC4-4a missing fields | M3 field validation area |
| UC4-4b past time | M3 field validation area |
| UC4-4c end ≤ start | M3 field validation area |
| UC4-5a conflict | M3 conflict warning banner (blocks save) |
| UC4-6a save failed rollback | M3 rollback area |
| US1 AC2 empty state (AC-driven) | M1 empty-state strip |
| US1 AC3 / QT-14 403 (API-level) | M1 generic message area; canonical definition in API contract |

## 4. Absent by design

No `location`, no appointment `note/ghi_chu`, no `KIEM_TRA_TAI_CHO` option in v0.2; no technician or customer screens. Each absence traces to a locked scope decision in SRS v0.2 §1.3 / §5 notes.

## 5. BT2 Scope Reconciliation: technician_skill
In BT1, `technician_skill` was documented as imported master data with no admin screen in v0.2 (NFR7 insert-only). For BT2, API-level CRUD endpoints were added to satisfy the BT2 requirement that at least two entities support full CRUD operations. This serves as a backend support API for the qualification matrix (QT-08). **No new customer-facing or manager-facing screen is introduced**, so the "no admin screen in v0.2" wireframe constraint remains true.
