# Appendix — Declaration of AI Tool Usage (BT1)

| Tool | Used for | Applied in which part | How it was verified |
| :--- | :--- | :--- | :--- |
| Qwen AI | Phase planning; consistency reviews; condensing and restructuring the SRS (v0.1 → v0.3); generating the draw.io skeleton for the Use Case, Architecture, ERD and Wireframe diagrams; drafting the architecture rationale sentences, the DDL skeleton and the API contract, EN-VN Translation | `docs/srs_en.md`; `docs/usecase_l4.drawio` and `docs/usecase_spec_l4.md`; `docs/architecture_l4.drawio` and `docs/architecture_l4.md`; `docs/erd_l4.drawio`, `docs/erd_l4.dbd`, `docs/ddl_l4.sql`; `docs/wireframes_l4.drawio` and `docs/wireframe_mapping.md`; `docs/api_contract.md` | Every business rule, identifier and threshold was cross-checked against the course material and the case study (QT-xx codes, ticket status lifecycle, dataset columns in the provided data-generation code). All scope decisions — dropping appointment `location` and `note`, deferring `KIEM_TRA_TAI_CHO` from the v0.2 UI, dropping `customer_id` in favour of snapshot fields, locking the 7 core user stories — were made and locked by the student. Every diagram was opened, reviewed and adjusted manually in draw.io. The six consistency checks were re-run manually before PDF assembly. |
| Qwen AI | Drafted BT2 phase plan and documentation edits for appointment soft delete, technician_skill CRUD, tag normalization, and traceability updates | `docs/thay-doi-thiet-ke_en.md`, `docs/srs_en.md`, `docs/api_contract_en.md`, `docs/erd_l4_en.dbd`, `docs/ddl_l4.sql`, `README.md` | Student reviewed all changes against the BT2 assignment, L4 BT1 documents, and course rubric. Final scope decisions — appointment + technician_skill, soft-delete appointment, official tag v0.2 — were made by the student. |
| — none — | Original business-rule analysis; MoSCoW prioritisation and final user-story selection; final architecture option decisions; sample-data and seed decisions; peer-review coordination | SRS Sections 1–5 (scope and decisions); Architecture Section 2 (option choice); data plan | Performed entirely by the student, based on the course material and the provided sample dataset |

**"I confirm that I have read, understood, and take full responsibility for all of this content."**

- Full name: RASPHONE Samphanthamith
- Student ID (MSSV): 237480201IS09
- Date: 08/10/2026
