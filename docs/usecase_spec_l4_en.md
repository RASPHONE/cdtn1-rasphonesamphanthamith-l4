## UC3 — Assign/reassign technician

- **Primary actor:** Center Manager
- **Goal:** Assign exactly one qualified technician to a warranty ticket, or change the assignment with a recorded reason.
- **Preconditions:** Manager is logged in and scoped to their own service center (QT-14); the ticket belongs to that center; ticket status is not `DA_DONG` or `DA_HUY`.
- **Postconditions:** `ticket.technician_id` is set; if the previous status was `MOI`, status becomes `DA_PHAN_CONG`; one `ticket_status_log` entry is written (with reason when reassigning).
- **Related:** US2, US3, US4 · FR2, FR3, FR4, FR5, FR8 · QT-07, QT-08 · Includes UC2
- **Priority:** MUST

**Main flow (happy path)**

1. The manager selects a warranty ticket from the unassigned list (UC1) or ticket detail.
2. The system displays the ticket summary: `ticket_code`, `issue_category`, `priority`, `due_date`, `customer_name`, `customer_phone` (full display for Center Manager, QT-15), `serial_no`.
3. The system invokes UC2 and lists qualified technicians: same `center_id`, `is_active = true`, `technician_skill.proficiency ≥ 3`, each with current workload count (FR8).
4. The manager selects exactly one technician.
5. If the ticket already has an assigned technician (reassignment), the system requires a non-empty reason.
6. The manager confirms the assignment.
7. The system validates eligibility (QT-08) and the one-technician rule (QT-07).
8. The system saves `technician_id`; changes status `MOI → DA_PHAN_CONG` when applicable; writes a `ticket_status_log` entry with `changed_by` and the reason (reassignment only).
9. The system displays confirmation with the assigned technician and updated ticket status.

**Exception flows (numbered by step)**

- **3a.** No qualified technician exists → system shows "No qualified technician available" and disables Confirm; manager may cancel without changes.
- **5a.** Reassignment reason is empty → system rejects and displays "Reason is required when changing technician."; selection is kept.
- **7a.** Selected technician fails QT-08 (wrong center or proficiency < 3, e.g. stale list) → system rejects with a validation error; no data is changed.
- **8a.** Connection drops or save fails → full rollback (NFR5): no partial ticket update, no orphan log entry; UI keeps entered data and allows retry.

---

## UC4 — Create/update appointment

- **Primary actor:** Center Manager
- **Goal:** Schedule or reschedule a device handover/receipt appointment for an assigned ticket without double-booking the technician.
- **Preconditions:** The ticket has an assigned technician (`technician_id` NOT NULL); manager is scoped to the ticket's center (QT-14).
- **Postconditions:** One `appointment` row exists/updated, linked to `ticket_id`, `technician_id`, `center_id`, with `trang_thai = DA_XAC_NHAN` after confirmation.
- **Related:** US5, US6 · FR6, FR7 · CON-01, CON-02, CON-03
- **Priority:** MUST

**Main flow (happy path)**

1. The manager opens the appointment form for an assigned ticket.
2. The system displays the ticket summary and the assigned technician.
3. The manager selects `loai` (`GIAO_MAY` or `NHAN_MAY` in v0.2) and enters `ngay_hen`, `gio_bat_dau`, `gio_ket_thuc`. (No location or note field in v0.2.)
4. The system validates: required fields present; (`ngay_hen` + `gio_bat_dau`) is in the future; `gio_ket_thuc > gio_bat_dau` (CON-01); `loai` allowed for creation in v0.2 (CON-02).
5. The system checks overlap against existing appointments of the same technician on the same `ngay_hen` with `trang_thai IN ('DA_DAT','DA_XAC_NHAN')`, excluding the appointment being updated.
6. If no overlap, the system saves the appointment linked to the ticket, technician, and center with `trang_thai = DA_XAC_NHAN` and displays confirmation.

**Exception flows (numbered by step)**

- **3a.** Manager (or API client) requests `KIEM_TRA_TAI_CHO` → system rejects creation in v0.2; the value remains in the enum only for historical data compatibility.
- **4a.** A required field (`ngay_hen`, `gio_bat_dau`, `gio_ket_thuc`, `loai`) is missing → system rejects, highlights missing fields, keeps entered data.
- **4b.** (`ngay_hen` + `gio_bat_dau`) is in the past → system rejects with "Appointment time must be in the future."
- **4c.** `gio_ket_thuc ≤ gio_bat_dau` → system rejects with "End time must be after start time."
- **5a.** Overlap with an active appointment of the same technician on the same `ngay_hen` → system warns with the conflicting appointment details and **blocks saving** until the manager changes the time or cancels (FR7, US6). No override in v0.2.
- **6a.** Save fails → full rollback (NFR5); entered data kept; retry allowed; no duplicate appointment row.

**Exception → AC → future test case mapping (for BT3)**

| Exception | SRS acceptance criterion | Future TC source |
|---|---|---|
| 3a | US5 AC1 (type restricted) | TC: reject on-site type in v0.2 |
| 4a | US5 AC3 | TC: missing required fields |
| 4b | US5 AC2 | TC: past appointment rejected |
| 4c | US5 AC4 | TC: end before start rejected |
| 5a | US6 AC1, AC3, AC4 | TC: conflict blocks save; inactive status does not conflict |
| UC3-3a | US2 AC2 | TC: no qualified technician |
| UC3-5a | US4 AC2 | TC: reason required |
| UC3-7a | US4 AC3, US2 AC3 | TC: ineligible technician rejected |
| UC3-8a / 6a | NFR5 | TC: rollback on failure |
