# Smart CRM – Mekong Mobile · Flow L4: Technician Assignment & Appointment Scheduling

Repository `cdtn1-rasphonesamphanthamith-l4` · Track **SE** · Specialized Graduation Topic I (CĐTN1) · BT2 tag **`v0.2`**

## 1. What it does

A decision-support tool for warranty-center managers at Mekong Mobile. It lists the
center's unassigned warranty tickets by SLA due date (problem V2), suggests only
technicians of the same center with proficiency ≥ 3 in the ticket's issue category and
shows each one's current workload (QT-08, problem V3), and records assignments and
reassignments with a mandatory reason (QT-07). It books device hand-over/receipt
appointments and blocks any time overlap for the same technician (FR7). Every manager
only sees data of their own center (QT-14).

Stack: FastAPI (Python) · PostgreSQL 16 · React + Vite. Requirements: `docs/srs.md`.

## 2. Environment

| Tool | Version |
|---|---|
| Python | 3.11 – 3.14 (tested on each; Docker image: 3.12.7) |
| PostgreSQL | 16 (a local install, or use Docker in section 4) |
| Node.js | 22.12+ (or 20.19+) — required by Vite 8 |
| Docker Desktop | optional, only for section 4 |

All configuration is in environment variables; every variable is listed with a sample
value in `.env.example` (backend) and `frontend/.env.example` (frontend). `.env` files are gitignored.

## 3. Install and run (native)

Run from the repository root, one command per step. Windows PowerShell: use `copy` instead of `cp`.

| # | Step | Command |
|---|---|---|
| 1 | Get the code | `git clone --branch v0.2 https://github.com/RASPHONE/cdtn1-rasphonesamphanthamith-l4.git` |
| 2 | Enter the folder | `cd cdtn1-rasphonesamphanthamith-l4` |
| 3 | Create `.env` | `cp .env.example .env` — then set `DB_USER` / `DB_PASSWORD` to your local PostgreSQL account |
| 4 | Create the empty database | `psql -U postgres -c "CREATE DATABASE mekong_l4"` |
| 5 | Create a virtual environment | `python -m venv .venv` |
| 6 | Activate it | Windows: `.venv\Scripts\activate` · macOS/Linux: `source .venv/bin/activate` |
| 7 | Install dependencies (pinned) | `pip install -r requirements.txt` |
| 8 | Build the schema | `python scripts/migrate.py` |
| 9 | Load sample data | `python scripts/seed.py` |
| 10 | Start the API | `uvicorn src.main:app --port 8000` |

Frontend, in a **second terminal** (the API must be running):

| # | Step | Command |
|---|---|---|
| 11 | Go to the frontend | `cd frontend` |
| 12 | Create its `.env` | `cp .env.example .env` |
| 13 | Install dependencies (lock file) | `npm ci` |
| 14 | Start the UI | `npm run dev` → open http://localhost:5173 |

### Demo accounts

| Username | Password | Center |
|---|---|---|
| `manager1` | `manager123` | 1 |
| `manager2` | `manager123` | 2 |

Demo-only accounts for QT-14 scoping (TD-07); they are not production authentication.
The session token is kept in the browser's `localStorage` — readable by an injected
script if the page had an XSS bug; accepted for the prototype (an HttpOnly cookie is the production choice).

## 4. Run with Docker (2 commands)

```bash
cp .env.example .env
docker compose up -d --build
```

`docker compose ps` should show `db`, `api` and `web` as **healthy**. The API container
builds the schema and loads the sample data automatically.
UI: http://localhost:5173 · API: http://localhost:8000/health · PostgreSQL on host port 5433.
Start over from an empty database: `docker compose down -v` then the second command again.

## 5. Tests

```bash
pytest -q
```

Expected: `81 passed`. Tests use in-memory fakes (`tests/fakes.py`) and need **no database and no `.env`**.
The three BT2 test types (happy path · boundary · invalid data) in one file:
`pytest -v tests/test_bt2_three_types.py`. Frontend checks: `npm run lint` and `npm run build` in `frontend/`.

## 6. Check that it works

| Check | Command / action | Expected |
|---|---|---|
| API and database up | `curl http://localhost:8000/health` | `{"status":"ok","database":"up"}` |
| Re-run is safe (no duplicates) | `python scripts/migrate.py` then `python scripts/seed.py` again | `0 applied, 2 already up to date` · every table `+0` |
| Main flow | Log in as `manager2` → M1 → **Phân công** → choose a technician → **Xác nhận phân công** → **Đặt lịch hẹn → M3** → pick a future date/time → **Lưu & xác nhận** | Ticket leaves M1; appointment appears in M3 as "Đã xác nhận" |
| Double booking blocked | In M3, enter an overlapping time for the same technician | Yellow "Trùng lịch" banner, save disabled; the API returns 409 with the conflicting appointment |
| Filter with no result | M1: Nhóm sự cố "Nước vào" + Ưu tiên "Thấp" → **Áp dụng bộ lọc** | "Không có phiếu nào khớp bộ lọc hiện tại." + **Xoá bộ lọc** |
| Invalid data | `curl -X POST http://localhost:8000/api/appointments -H "Authorization: Bearer <token>" -H "Content-Type: application/json" -d "{}"` | `400 bad_request` naming each missing field |
| Backend stopped | Stop uvicorn, reload the UI | Error panel "Không kết nối được tới máy chủ…" with **Thử lại** |
| Database stopped | Stop PostgreSQL, reload a screen | `503 database_unavailable`, UI shows "Cơ sở dữ liệu tạm thời không khả dụng…" |

API reference and error codes: `docs/api-contract.md`.

## 7. Sample data (reproducible)

The committed sample `data/sample/` (≈ 2,100 rows: 6 categories, 38 technicians, 159 skills,
487 tickets, 1,330 status logs, 74 appointments) was built from the course dataset:

```bash
python tools/gen_dataset.py data/raw                                    # seed 20260901 (inside the script)
python tools/gen_sample.py --entity appointment --rows 1200 --seed 42 --link data/raw/tickets_history.csv --out data/raw/appointments.csv
python scripts/build_sample.py                                          # seed 42 → data/sample/*.csv
```

`data/raw/` (187,650 rows) is not committed. What the sample contains and why some rows
are generated (no `MOI` tickets in the dataset, customer snapshot fixture): `docs/srs.md` §1.5.

## 8. Project structure

```text
src/                     backend, three layers
  routes/                  layer 1: HTTP endpoints (+ schemas/ = request validation)
  services/                layer 2: business rules (QT-07, QT-08, QT-14, QT-15, FR7) — no HTTP, no SQL
  repositories/            layer 3: SQL (psycopg 3) + transaction.py (unit of work)
  main.py · errors.py · security.py · config.py · db.py
db/migrations/           001_init_schema.sql, 002_add_appointment_soft_delete.sql
scripts/                 migrate.py · seed.py · build_sample.py · docker-entrypoint.sh
data/sample/             committed sample CSVs
tools/                   course dataset generators (gen_dataset.py, gen_sample.py)
tests/                   pytest: fakes.py + service and API tests
frontend/src/            api/ (only fetch calls) · pages/ (M1, M2, M3, Login) · components/ · hooks/ · labels.js
docs/                    srs.md · api-contract.md · architecture-thuc-te.md (as built) · thay-doi-thiet-ke.md
                         ai-disclosure.md · bug-log.md · BT1 diagrams (.drawio) and exports/
Dockerfile · frontend/Dockerfile · docker-compose.yml
```

Naming convention: identifiers we choose are English (`snake_case` in Python, `camelCase`
in JavaScript). Data fields — columns, API fields, and the JavaScript objects sent to or
read from the API — keep the exact ERD column names from the SRS glossary (`ngay_hen`,
`gio_bat_dau`, `trang_thai`, `ho_ten`, …), which come from the course dataset and were kept
on purpose (BT1 feedback). The UI text is Vietnamese.

## 9. Current status

- [x] BT1 — analysis & design (PDF submitted; design files in `docs/`)
- [x] BT2 — core module, tests, M1–M3 screens, Docker (tag `v0.2`)
- [ ] BT3 — test plan/report and packaging (tag `v1.0`)

Design changes since BT1 (what · why · impact): `docs/thay-doi-thiet-ke.md` (TD-01 … TD-30) ·
bugs found and fixed: `docs/bug-log.md` · AI usage: `docs/ai-disclosure.md`.
