# Deployment Guide — Mekong Mobile L4 (Technician Assignment & Appointment Scheduling), track SE, tag `v1.0`

Three containers: **db** (PostgreSQL 16), **api** (FastAPI, port 8000) and **web** (React UI
served by nginx, port 5173). The api container creates the schema and loads the sample data
by itself, so the system is ready after two commands. No Python, Node.js or PostgreSQL is
needed on the computer. (Running without Docker: README §3. Public demo on Render's free tier: §9.)

## 1. Requirements

| Item | Value |
|---|---|
| Operating system | Linux, macOS or Windows 10/11 (64-bit) |
| Docker | Docker Engine 24+ with the Compose v2 plugin, or Docker Desktop 4.25+. Check: `docker compose version` prints `v2.x` |
| Git | 2.30+ |
| Disk / memory | about 2 GB free disk (images and build cache), 2 GB RAM for Docker |
| Free ports | **8000** (API), **5173** (UI), **5433** on 127.0.0.1 (database, for tools only). Other ports: section 3 |
| Network | Internet access for the first build (Docker images, pip and npm packages) |

## 2. Setup steps

Run each command in a terminal, in this order (Windows: PowerShell).

1. `git clone --branch v1.0 https://github.com/RASPHONE/cdtn1-rasphonesamphanthamith-l4.git`
2. `cd cdtn1-rasphonesamphanthamith-l4`
3. `cp .env.example .env` — the sample values work as they are; nothing to edit for a local run
4. `docker compose up -d --build` — the first build takes about 2–4 minutes; the database
   schema and the sample data are loaded during this step

Open the UI at http://localhost:5173 and log in with a demo account (section 4).

Stop: `docker compose down` (data kept) · start again from an empty database:
`docker compose down -v`, then step 4.

## 3. Environment variables

All variables are in `.env` (created in step 3 from `.env.example`, which explains each one).
`.env` is never committed. **Required** = Docker Compose stops with an error if it is missing.

| Name | Meaning | Sample value | Required |
|---|---|---|---|
| `DB_PASSWORD` | Password of the PostgreSQL account, used by db and api | `postgres` | yes |
| `DB_NAME` | Database name | `mekong_l4` | no (default `mekong_l4`) |
| `DB_USER` | PostgreSQL account | `postgres` | no (default `postgres`) |
| `JWT_SECRET` | Key that signs login tokens. **Empty** = the API makes a random key at each start (users log in again after a restart). To keep logins across restarts, set 32+ random characters, e.g. `openssl rand -hex 32`. Values published in this repository are refused at start-up | *(empty)* | no |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Lifetime of a login token | `60` | no |
| `DEMO_PASSWORD` | Password of the demo accounts, applied at every start of the api container (change it, then `docker compose up -d` or a redeploy); only its PBKDF2 hash is stored | `manager123` | no |
| `APP_TIMEZONE` | Business time zone ("appointment must be in the future") | `Asia/Ho_Chi_Minh` | no |
| `LOG_LEVEL` | API log level | `INFO` | no |
| `API_PORT` | Host port of the API | `8000` | no |
| `WEB_PORT` | Host port of the UI (the allowed CORS origin follows it) | `5173` | no |
| `DOCKER_DB_PORT` | Host port of the database, bound to 127.0.0.1 only | `5433` | no |

`DB_HOST`, `DB_PORT`, `PORT`, `CORS_ORIGINS` and `DB_CONNECT_TIMEOUT` are read only when the
API runs without Docker (README §3); in Docker, `docker-compose.yml` sets them.
`DATABASE_URL` (one `postgresql://user:password@host:port/name` value that replaces the `DB_*`
variables) and `PORT` are set by the hosting platform in the public deployment (§9).

## 4. Sample data

Loaded **automatically** when the api container starts (`scripts/docker-entrypoint.sh`:
`migrate.py` → `seed.py` → API). The source is the committed sample `data/sample/*.csv`,
built from the course dataset. Both scripts are safe to run again: a second run adds 0 rows.

| Table | Rows | What it is |
|---|---|---|
| `issue_category` | 6 | issue categories (MAN_HINH, PIN, …) |
| `technician` | 38 | technicians of centers 1–6 |
| `technician_skill` | 159 | technician × category with proficiency 1–5 |
| `ticket` | 487 | warranty tickets; 27 open unassigned (`MOI`) in center 1 and 27 in center 2 |
| `ticket_status_log` | 1390 | status history (1330 from the sample + 60 creation rows of the `MOI` tickets) |
| `appointment` | 80 | 74 from the sample + 6 upcoming demo appointments dated from the day of the first start |
| `app_user` | 2 | demo accounts |

Demo accounts: **`manager1`** (center 1) and **`manager2`** (center 2), password **`manager123`**
(the `DEMO_PASSWORD` value). They are sample data for the prototype, not real credentials.

Check the counts:
`docker compose exec db psql -U postgres -d mekong_l4 -c "SELECT (SELECT count(*) FROM ticket) AS tickets, (SELECT count(*) FROM appointment) AS appointments, (SELECT count(*) FROM app_user) AS users"`
→ `487 | 80 | 2`

## 5. Verify it works

| # | Command / action | Expected result |
|---|---|---|
| 1 | `docker compose ps` | `db`, `api` and `web` all show `Up … (healthy)` (if `web` still shows `starting`, wait 20 seconds) |
| 2 | `curl -s http://localhost:8000/health` (Windows PowerShell: `curl.exe`) | `{"status":"ok","database":"up"}` |
| 3 | `docker compose exec api pytest -q` | `116 passed` — the full suite, including the 12 Test Report cases on fresh copies of the sample database |
| 4 | `docker compose exec api pytest -s -v tests/bt3 -k tc10` | one Test Report case with its `observed:` line and `PASSED` (any `tc01` … `tc12`) |
| 5 | `docker compose exec api python scripts/migrate.py` | `Migration completed: 0 applied, 3 already up to date.` |
| 6 | `docker compose exec api python scripts/seed.py` | every table `+0`; totals as in section 4 (no duplicates) |
| 7 | Open http://localhost:5173, log in as `manager2` / `manager123` | screen M1 lists 27 unassigned tickets of center 2, most urgent first |
| 8 | M1 → **Phân công** on a ticket → choose a technician → **Xác nhận phân công** | the ticket leaves M1; **Đặt lịch hẹn → M3** books an appointment shown as "Đã xác nhận" |
| 9 | `curl -s http://localhost:8000/api/tickets/unassigned` | `{"error":"unauthorized", …}` with HTTP 401 — data needs a login |

API reference with real examples: `docs/api-docs/README.md` (also `http://localhost:8000/docs`).

## 6. Troubleshooting

| Symptom | Fix |
|---|---|
| `permission denied … docker.sock` (Linux) | Your user is not in the `docker` group: put `sudo` before each `docker` command, or run `sudo usermod -aG docker $USER` and log in again |
| `Set DB_PASSWORD in .env` | Step 3 was skipped: run `cp .env.example .env` in the project folder |
| `port is already allocated` / `address already in use` | Another program uses 8000, 5173 or 5433: set `API_PORT`, `WEB_PORT` or `DOCKER_DB_PORT` in `.env`, then `docker compose up -d --build` |
| `api` stays `starting` or `unhealthy` | `docker compose logs api --tail 50`. `password authentication failed` means an old database volume made with another password: `docker compose down -v`, then step 4 |
| API log: `JWT_SECRET is a sample value published in the repository` and the API stops | The `.env` was copied from an old version: empty the `JWT_SECRET=` line (or set your own 32+ characters) |
| Logged out after `docker compose restart` | Expected with an empty `JWT_SECRET` (new key at each start); set one to keep logins |

## 7. Before a real deployment (HTTPS and secrets)

This package is for a local demo. For a real server: put `web` and `api` behind a reverse
proxy with a TLS certificate (nginx, Caddy or the hosting platform) and serve **HTTPS only**;
set `CORS_ORIGINS` to the HTTPS address of the UI; set a new `JWT_SECRET` (32+ random
characters), `DB_PASSWORD` and `DEMO_PASSWORD` in the platform's secret settings, never in
the repository; remove the database `ports:` entry so PostgreSQL is reachable only inside the
Docker network. The API sets no cookies (the token travels in the `Authorization` header) and
builds no absolute URLs, so it needs no code change behind the proxy.

## 8. Monitoring & alerts (proposal — not automated in this prototype)

What exists: every API log line carries a `request_id` (also returned in the `X-Request-ID`
header and in 500 bodies) with method, path, status and duration; `GET /health` checks the API
and the database; Docker restarts nothing by itself, it marks a failing service `unhealthy`.

**ALERT-01 — API errors.** *Measure:* number of 5xx responses in the API log, every 5 minutes
(`docker compose logs api --since 5m | grep -c "status=5"`). *Threshold:* more than 5 in two
consecutive windows. *Notify:* the on-duty operator, by chat message. *Action:* 1) find the
`request_id` of a failed call in the log and read the error line under it; 2) if it says
`database unavailable`, run `docker compose restart db`, then `curl -s http://localhost:8000/health`
must return `"database":"up"`; 3) still failing after 10 minutes → call the developer.

**ALERT-02 — Tickets about to miss their SLA (business).** *Measure:* open warranty tickets with
no technician whose `due_date` is within 4 hours, per center, every hour
(`SELECT center_id, count(*) FROM ticket WHERE status = 'MOI' AND technician_id IS NULL AND is_warranty AND NOT is_deleted AND due_date < now() + interval '4 hours' GROUP BY center_id`).
*Threshold:* more than 5 in one center. *Notify:* that center's manager, by e-mail.
*Action:* open M1 (sorted by due date) and assign the listed tickets to qualified technicians
with the lowest workload shown in M2.

## 9. Public demo on Render (free tier)

**Live:** UI https://l4-237480201is09-web.onrender.com · API https://l4-237480201is09-api.onrender.com/health
(interactive reference: `/docs`). Demo accounts `manager1` (center 1) and `manager2` (center 2);
their password is the `DEMO_PASSWORD` set on Render, given in the BT3 report, not in this repository.
Deployed on 12/11/2026 from commit `5e9a63d`; evidence: `docs/screenshots/deploy-1.png` (the live UI)
and `deploy-2.png` (the API's variables on Render, values hidden).

`render.yaml` (a Render Blueprint) describes the three parts, all on Render's free plan in Singapore:

| Part | Render service | Configuration on the platform |
|---|---|---|
| Database | PostgreSQL 16, private network only (no public access) | created empty; the API's start-up builds the schema and loads the sample data (section 4) |
| API | Docker web service built from `./Dockerfile`, health check `/health` | `DATABASE_URL` taken from the database; `JWT_SECRET` generated by Render; `DEMO_PASSWORD` typed in the dashboard; `CORS_ORIGINS` = the UI address; `PORT` set by Render |
| UI | Static site built from `frontend/` with `npm ci && npm run build` | `VITE_API_BASE_URL` = the API address; served over HTTPS with security headers |

Steps (once):

1. Push the repository to GitHub (public).
2. Open https://dashboard.render.com, sign in with GitHub, choose **New → Blueprint** and select
   `cdtn1-rasphonesamphanthamith-l4`, branch `main`.
3. Render lists the database and the two services from `render.yaml` and asks for `DEMO_PASSWORD`:
   type the password the demo accounts should have, then **Deploy Blueprint**.
4. Wait until all three are **Available** / **Deployed** (the first API build takes about 5 minutes).
5. Check: `curl -s https://l4-237480201is09-api.onrender.com/health` → `{"status":"ok","database":"up"}`;
   open the UI, log in as `manager2` → screen M1 lists 27 tickets.

**Changing the demo password later:** service `l4-237480201is09-api` → **Environment** → edit
`DEMO_PASSWORD` → **Save, rebuild, and deploy**. The API's start-up (`seed.py`) sees that the stored
hashes no longer match and replaces them; its log shows `Demo password changed to the DEMO_PASSWORD
value for: manager1, manager2`. The same works locally: edit `.env`, then `docker compose up -d`.

If Render added a suffix to a name because the address was taken, set the API's `CORS_ORIGINS` to
the real UI address and the UI's `VITE_API_BASE_URL` to the real API address (service →
**Environment**), then **Manual Deploy → Clear build cache & deploy** the UI.

Every push to `main` redeploys the API and the UI. Free-plan limits: the API sleeps after
15 minutes without traffic and the next request takes about a minute (the UI shows its loading
state meanwhile); the free database expires 30 days after creation, then is deleted after 14 more
days — create it again from the Blueprint or point `DATABASE_URL` at another PostgreSQL; 750 instance
hours per month. Optional: `.github/workflows/keep-awake.yml` calls `/health` every 10 minutes once
the repository variable `RENDER_API_URL` is set, so the API does not sleep while it is being graded.
