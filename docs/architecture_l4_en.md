# `docs/architecture_l4_en.md` — Architecture decisions (L4, v0.2)

Pattern: **Layered (4 layers)** as the frame, **MVC** inside the Presentation layer,
**Repository** for data access. Diagram: `docs/architecture_l4_en.drawio`.

## 1. Layer responsibilities (L4 instantiation)

| Layer | L4 components | Responsibility | Must NOT |
|---|---|---|---|
| 1 Presentation | M1/M2/M3 views; TicketController, AssignmentController, AppointmentController | Render lists/forms, empty-field hints, show empty-state, validation and conflict messages | Contain QT rules or SQL |
| 2 Service | TicketAssignmentService, TechnicianSuggestionService, AppointmentService, AccessControl | QT-06/07/08 enforcement, reassignment reason, conflict detection (FR7), center scoping (QT-14), phone masking (QT-15), transaction boundary (NFR5) | Know the storage technology; call upward |
| 3 Repository | TicketRepository, TechnicianRepository, AppointmentRepository, TicketStatusLogRepository (Pg + in-memory impls) | Translate service calls to SQL behind interfaces | Contain business rules |
| 4 Data store | PostgreSQL 16: ticket, technician, technician_skill, issue_category, appointment, ticket_status_log | Schema-level integrity (PK, FK, CHECK CON-01..05, UNIQUE), indexes for NFR1/NFR2/FR7 | — |

## 2. Architecture rationale (template: Because NFRx requires <threshold>, I choose <decision>; the trade-off is <cost>)

1. **Because NFR1** requires the unassigned warranty ticket list to render in **under 2 seconds for up to 500 open tickets per center**, I choose **server-side filtering, sorting and pagination executed in the repository query**, backed by the composite index `idx_ticket_unassigned ON ticket(center_id, status, technician_id, due_date)`, instead of loading all tickets and filtering in the presentation layer; **the trade-off is** extra write cost on every ticket update and one additional index to maintain.

2. **Because NFR2** requires the qualified-technician panel to return in **under 1 second for up to 40 active technicians and 6 issue categories**, I choose **a single indexed join query** (`technician ⋈ technician_skill` filtered by `center_id`, `category_id`, `proficiency ≥ 3`, `is_active = true`) executed by TechnicianSuggestionService, **without any caching layer**; **the trade-off is** that the query must be reworked if eligibility rules grow (e.g. workload-based ranking), and `idx_skill_lookup` adds maintenance cost.

3. **Because NFR3** requires that **any cross-center request returns HTTP 403**, I choose to **enforce center scoping inside the Service layer** (every service method receives the caller's center context via AccessControl) rather than merely hiding other centers' data in the UI; **the trade-off is** that every service method must accept and validate caller context, adding a small repeating authorization step.

4. **Because NFR5** requires that a failed save leaves **no partial assignment or appointment and rolls back within 3 seconds**, I choose to **wrap the ticket update, the `ticket_status_log` insert and the appointment write in one database transaction** coordinated by the service layer; **the trade-off is** slightly longer row locks and more complex service code compared with saving each record separately.

5. **Because NFR7** requires that adding a new issue category needs **only one INSERT into `issue_category` with zero code changes**, I choose to **drive all eligibility logic from the `issue_category` and `technician_skill` tables** and forbid hard-coded category enums in code; **the trade-off is** that category master data must be administered by direct INSERT until a (deferred, SHOULD) admin screen exists.

6. **Because FR7 combined with NFR6** requires the manager to see an **understandable conflict warning and finish rescheduling within 3 minutes**, I compared two options — (A) a service-layer overlap query over active appointments (`trang_thai IN ('DA_DAT','DA_XAC_NHAN')`) using `idx_appointment_overlap`, versus (B) a PostgreSQL exclusion constraint — and I choose **option A**; **the trade-off is** that option A is not concurrency-proof at the database level (two simultaneous submits could theoretically overlap), which I accept because v0.2 has a single manager per center, whereas option B would be absolute but cannot emit a friendly, status-aware warning.

## 3. Directory tree (architecture evidence)

```text
warranty-l4/
├── src/
│   ├── presentation/
│   │   ├── controllers/   TicketController, AssignmentController, AppointmentController
│   │   └── views/         M1 list, M2 assignment, M3 appointment
│   ├── services/          TicketAssignmentService, TechnicianSuggestionService,
│   │                      AppointmentService, AccessControl
│   ├── domain/            Ticket, Appointment, eligibility rules as pure functions
│   └── repositories/      interfaces + Pg* implementations + Mem* for tests
├── db/schema.sql          layer 4 (DDL skeleton)
└── docs/                  srs_en.md, usecase_l4.drawio, architecture_l4.drawio,
                           erd_l4.drawio, api_contract.md, ai-disclosure.md
```
