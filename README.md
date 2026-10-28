# Smart CRM – Mekong Mobile · Flow L4: Technician Assignment & Appointment Scheduling
Repository: `cdtn1-rasphonesamphanthamith-l4` · Track SE · Specialized Graduation Topic I
Design documents: `docs/` (BT1).

## 1. Goal
A decision-support system for warranty center managers at Mekong Mobile:
- Replaces assignment by memory (problem V3): the system suggests technicians
  from the same service center with proficiency >= 3 in the ticket's issue
  category, showing each technician's current workload.
- Reduces silently overdue tickets (problem V2): the unassigned-ticket list is
  sorted by SLA due date (`due_date`).
- Prevents double-booking: creating or updating an appointment is blocked when
  it overlaps an active appointment of the same technician.
Scope stops at the center manager's screens in v0.2: no customer portal
(WON'T), no technician self-service UI (deferred to v1.1).
Details: `docs/srs_en.md`.

## 2. Environment
- Python 3.11+ · FastAPI · SQLAlchemy
- PostgreSQL 16 (native install or Docker)
- Environment variables: see `.env.example`
  (DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, PORT)
- Docker Desktop: only needed for BT3 packaging, not for BT1/BT2 development

## 3. Run instructions (<= 4 steps)
> **Status:** at the BT1 milestone this repository contains design documents
> only (`docs/`). The four steps below become runnable from tag `v0.2` (BT2);
1. `cp .env.example .env` and fill in the values
2. `pip install -r requirements.txt`
3. `python scripts/migrate.py`  # creates schema from `db/schema.sql`, loads `data/sample/`
4. `uvicorn src.main:app --reload` → open `http://localhost:8000/health`

## Run Frontend (React + Vite)

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:5173`.
Demo accounts:
- `manager1` / `manager123` (Center 1)
- `manager2` / `manager123` (Center 2)

## 4. Directory structure
```text
docs/      BT1 design documents + original .drawio sources:
           srs_en.md · usecase_l4_en.drawio · usecase_spec_l4_en.md ·
           architecture_l4_en.drawio · architecture_l4_en.md · erd_l4_en.drawio ·
           erd_l4_en.dbd · ddl_l4.sql · wireframes_l4_en.drawio ·
           wireframe_mapping_en.md · api_contract_en.md · ai-disclosure_en.md
src/       Source code in four layers (BT2):
           presentation/ (controllers, views) · services/ · repositories/ ·
           domain/ · main.py = FastAPI entry point (/health)
db/        schema.sql — storage-layer DDL (6 tables, CHECK constraints, indexes)
scripts/   migrate.py — schema creation + sample-data loading (BT2)
data/      sample/ a few hundred example rows; raw/ is NOT committed (.gitignore)
tools/     gen_sample.py — simulated data generation (--seed mandatory)
tests/     pytest unit tests (BT2)
```

## 5. Tests
```bash
pytest -v
```
Prints the number of PASSed tests. Status: no tests at the BT1 milestone;

## 6. Current status
- [x] Repository initialized, Conventional Commits (Session 2)
- [x] BT1 — analysis & design (end of Session 6): five components + AI
      appendix in `docs/`, PDF submitted via LMS (baseline tag `v0.1`)
- [ ] Scaffold of core modules: empty files matching the four-layer
      architecture (before Session 7)
- [ ] BT2 — assignment & appointment modules runnable locally
      (Sessions 8–12, tag `v0.2`)
- [ ] BT3 — tests & Docker packaging (Sessions 13–16, tag `v1.0`)

## 7. Sample data & seeds (Reproducibility)
- Base case-study dataset: seed `20260901` (16 files, 187,650 rows).
- L4 appointments (not present in the base set): seed `42`:
  ```bash
  python tools/gen_sample.py --entity appointment --rows 1200 --seed 42 \
    --link tickets_history.csv --out appointments.csv
  ```
- The L4 working subset is ~40,200 records (warranty tickets + related status
  logs + appointments + master data). This is a filtered subset, not the full
  187,650-row dataset.
- Large CSVs are NOT committed: `.gitignore` keeps `data/raw/` and `*.csv`
  except `!data/sample/*.csv`.
- Loading notes (BT2): empty `technician_id` → NULL; `is_warranty` strings →
  boolean; `customer_name` / `customer_phone` are snapshot fields produced by
  a fixture script (customers_raw cannot be joined to `customer_id`; see
  `docs/srs_en.md` §5 note 2).

## 8. Design change log

| Date | Change vs BT1 | Reason | Reference |
|---|---|---|---|
| 2026-10-15 | NFR4 threshold made measurable (100% mask format `090****567`); API Contract and directory tree kept repo-only, Report retained at 29 pages (reduced from 35 via TD-02 API-contract removal + TOC resize); 6–9 page guideline not met — deviation accepted with documented reasons | BT1 feedback TD-01, TD-02, TD-03 | `docs/thay-doi-thiet-ke_en.md` |
| 2026-10-15 | Normalized tags and added BT2 design changes: appointment soft-delete, technician_skill CRUD, minimal demo auth decision | BT2 | `docs/thay-doi-thiet-ke_en.md` |
| 2026-10-21 | Implemented BT2 core module for L4: appointment CRUD with soft delete, `technician_skill` CRUD, unassigned-ticket list, qualified-technician suggestion, assignment/reassignment, minimal demo authentication for QT-14 center scoping, seeded sample data, automated tests, and M1–M3 frontend screens. | BT2 Components 1–3: core module, tests, and presentation layer | `docs/thay-doi-thiet-ke_en.md`; `src/`; `tests/`; `frontend/`; `scripts/` |
| 2026-10-26 | BT2 implementation and alignment: added/updated US14/FR12 demo-authentication traceability; documented `technician_skill` API-only CRUD scope; aligned appointment `DA_XAC_NHAN` create/confirm behavior; documented completed-appointment soft-delete rejection; enforced reassignment reason length 5–255; implemented NFR5 atomic assignment transaction; aligned qualified-technician response to `{ "ticket_id", "items": [...] }`; added assignment response `log_id`. | BT2 rubric consistency, traceability, and API-contract alignment | `docs/thay-doi-thiet-ke_en.md` TD-09 to TD-14; `docs/srs_en.md`; `docs/api_contract_en.md` |

Internal SRS change log (v0.1 → v0.5, including pre-submission iterations):
see `docs/srs_en.md` → Document control.
