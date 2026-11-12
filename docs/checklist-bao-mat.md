# `docs/checklist-bao-mat.md` — Security checklist (L4, track SE, BT3)

Seven items of BT3 TP5, each with its status (**ĐÃ LÀM** done · **CHƯA LÀM** not done ·
**KHÔNG ÁP DỤNG** not applicable) and one line of evidence. Every item was checked by
**running** the command, not from memory: `bash scripts/security-checks.sh` runs all seven
against the Docker system (`bash scripts/security-checks.sh 4` runs one) and prints each
command with its result; the terminal of each item is `docs/screenshots/sec-<n>.png`, taken on
12/11/2026 during the clean-machine test of commit `8f4cfdb` (the `v1.0` application code) in Docker.
Filling the checklist this way found three bugs, now fixed: BUG-014 (Critical),
BUG-015 and BUG-016 (Minor) in `docs/bug-log.md`.

| # | Item | OWASP Top 10:2025 | Status |
|---|---|---|---|
| 1 | No secret in the repository | A02 Security Misconfiguration | ĐÃ LÀM |
| 2 | Input checked in the application | A05 Injection | ĐÃ LÀM |
| 3 | Access limited to the owner | A01 Broken Access Control | ĐÃ LÀM |
| 4 | Passwords / sensitive data hashed or encrypted | A04 Cryptographic Failures · A07 Authentication Failures | ĐÃ LÀM |
| 5 | Error messages reveal nothing internal | A10 Mishandling of Exceptional Conditions · A02 | ĐÃ LÀM |
| 6 | Logs hold no secret or unneeded personal data | A09 Security Logging and Alerting Failures | ĐÃ LÀM |
| 7 | Dependencies pinned and checked for known vulnerabilities | A03 Software Supply Chain Failures | ĐÃ LÀM |

## 1. No secret in the repository — ĐÃ LÀM

**Evidence:** `git log --all --oneline -- .env frontend/.env` → empty (no `.env` was ever
committed); `git check-ignore -v .env frontend/.env` → `.gitignore:76`; a grep for a value
assigned to a password/secret/api_key/token name in `src/`, `scripts/`, `frontend/src/`,
`docker-compose.yml` and both Dockerfiles → empty · [sec-1](screenshots/sec-1.png).

- `JWT_SECRET` is empty in `.env.example`: the API then makes a random key per start. The
  sample key published in v0.2 (`.env.example` and a code default) is still in the Git
  history; it was never used outside local runs and the API now refuses to start with it
  (BUG-011, TC-11) — the equivalent of changing the key.
- Values that stay in the repository on purpose: `DB_PASSWORD=postgres` (local Docker
  database, not reachable from the network: port bound to 127.0.0.1), `DEMO_PASSWORD=manager123`
  (documented demo accounts, stored hashed, item 4) and the throw-away CI database password.
- The Docker image copies `.env.example`, never `.env` (`.dockerignore`).

## 2. Input checked in the application — ĐÃ LÀM

**Evidence:** the three course greps (SQL built by concatenation, raw HTML, system
commands) → empty; SQL text sent as a filter value → `400 bad_request` naming `priority`;
`tests/bt3/test_injection_db.py` PASS: the reason `Đổi KTV'); DROP TABLE ticket; --` is
stored as plain text and `ticket` still has 487 rows; TC-08 and TC-09 PASS · [sec-2](screenshots/sec-2.png).

- Every value reaches PostgreSQL as a bound parameter (`%s`, psycopg 3). The f-strings in
  `src/repositories/` only join constant SQL fragments and column names from an allow-list;
  the one configurable value formatted into SQL (`APP_TIMEZONE` in `seed.py`) is now bound
  too (commit [71e092b](https://github.com/RASPHONE/cdtn1-rasphonesamphanthamith-l4/commit/71e092baa34c126ad5ba080b5ea8416a358ab017)).
- Request schemas (Pydantic) check types, enum values and required fields → 400; services
  check the business rules → 422 (reason 5–255 characters, proficiency 1–5, time ranges).
- Cross-site scripting: React escapes all text; no `innerHTML` / `dangerouslySetInnerHTML`.
  No system command or file path is ever built from user input.

## 3. Access limited to the owner — ĐÃ LÀM (S2)

**Evidence:** TC-10 PASS — `manager1` (center 1) changing appointment 900004 of center 2 →
`403 cross_center_access`, the row stays 09:00–10:00; probe: `manager1` reading ticket 8036
of center 2 → 403, `manager2` → 200 · [sec-3](screenshots/sec-3.png), [TC-10](screenshots/TC-10.png).

- The center always comes from the signed token, never from the request (QT-14). Each
  service compares it with the record's center before reading or writing; lists are filtered
  by it (TC-04: 27 tickets per center, no shared id).
- Tokens are verified with HS256 only and must carry `exp`, `sub`, `user_id`, `role` and
  `center_id` (commit [3275513](https://github.com/RASPHONE/cdtn1-rasphonesamphanthamith-l4/commit/32755138d155c1caa0d35c89b049c4ca4e4cc8ae)); a forged or altered token → 401 (TC-11).

## 4. Passwords hashed — ĐÃ LÀM (S3)

**Evidence:** `SELECT username, left(password_hash, 48) FROM app_user` →
`pbkdf2_sha256$600000$<salt>$<hash>` for both accounts (90 characters, never `manager123`);
`tests/test_password_storage.py` and `tests/bt3/test_password_storage_db.py` PASS ·
[sec-4](screenshots/sec-4.png).

- PBKDF2-HMAC-SHA256, 600,000 iterations, random 16-byte salt per account, constant-time
  comparison; an unknown username is checked against a dummy hash so both failures take the
  same time and return the same message. A database `CHECK` refuses a value that is not a hash.
- Found while filling this item: the demo passwords were plain text in the code →
  **BUG-014 (Critical)**, fixed in [2240727](https://github.com/RASPHONE/cdtn1-rasphonesamphanthamith-l4/commit/224072743ac5c29032b9cd0ef62ce5bdc12ff567).
- Not done: customer phone numbers are stored in clear (needed by the manager to call the
  customer); they are masked for every other role (QT-15, TC-05) and only visible inside the
  manager's own center. Encryption at rest is out of the prototype's scope.

## 5. Error messages reveal nothing internal — ĐÃ LÀM (S4)

**Evidence:** body that is not JSON → `400 bad_request` "Request body is not valid JSON.";
unknown path → `404 not_found`; wrong method → `405 method_not_allowed`; altered token →
`401` "Invalid authentication token."; database stopped → `503 database_unavailable`
"The database is temporarily unavailable…" (no host, port or SQL); unexpected exception →
`500 internal_error` with a `request_id` only · [sec-5](screenshots/sec-5.png).

- Every error uses `{error, message}`; stack traces stay in the server log under the same
  `request_id`.
- Found while filling this item: framework 404/405 answered FastAPI's `{"detail": …}` →
  **BUG-015** ([3804e6c](https://github.com/RASPHONE/cdtn1-rasphonesamphanthamith-l4/commit/3804e6c2e3ac456043a1dc4fb45792080ccfd779)); a 500 had no `X-Request-ID` header
  and no request log line → **BUG-016** ([354f526](https://github.com/RASPHONE/cdtn1-rasphonesamphanthamith-l4/commit/354f526a5a76bcef5005e2ed0f5bc25401565e0b)).
  The served OpenAPI said 422 for invalid input while the API answers 400 → corrected
  ([75973c8](https://github.com/RASPHONE/cdtn1-rasphonesamphanthamith-l4/commit/75973c81f4be759e21b3c13b93a2594ea5115f2d)).

## 6. Logs hold no secret or personal data — ĐÃ LÀM

**Evidence:** after all the checks above (logins, ticket lists with phone numbers, errors),
`docker compose logs api | grep -ciE 'password|token|bearer|\b0[0-9]{9}\b'` → `0` ·
[sec-6](screenshots/sec-6.png).

- The API writes one line per request: `request_id`, method, path, status, duration. It never
  logs bodies, headers or tokens; no endpoint takes personal data in the URL.
- A database outage logs the driver's message (host and port, never the password) for the
  operator only.

## 7. Dependencies pinned and checked — ĐÃ LÀM

**Evidence:** `requirements.txt` 10/10 packages pinned with `==`, `frontend/package-lock.json`
committed, Docker images pinned to exact tags; `pip-audit -r requirements.txt` → "No known
vulnerabilities found"; `npm audit` → "found 0 vulnerabilities" · [sec-7](screenshots/sec-7.png).

- The first `pip-audit` run (Session 15) reported 25 advisories in FastAPI/Starlette, PyJWT
  and pytest → upgraded in [b4c3e97](https://github.com/RASPHONE/cdtn1-rasphonesamphanthamith-l4/commit/b4c3e97c591e48cd3b7e90a4c6f7a275cac037f8).
  The first `npm audit` reported 4 moderate advisories, all from `minimatch` under ESLint
  (development only; `npm audit --omit=dev` was already 0) → the patched `minimatch` is
  pinned with an npm override in [f9ac299](https://github.com/RASPHONE/cdtn1-rasphonesamphanthamith-l4/commit/f9ac2996d71c72d4afc96f2225b912de11ad1595).
- Plan: run item 7 again before every release; advisories published later are not checked
  automatically (CI does not run the audits).

## Other track SE points (Session 15 self-study)

- **CORS:** allowed origins come from `CORS_ORIGINS` (Docker: built from `WEB_PORT`); no wildcard origin.
- **Secrets in URLs:** none — the token travels in the `Authorization` header only.
- **Token storage:** the UI keeps the token in `localStorage` (readable by a script if the
  page had an XSS bug); accepted for the prototype, an HttpOnly cookie is the production choice.
- **HTTPS:** not used on localhost; the steps for a real deployment are in
  `docs/deployment-guide.md` §7.
- **Database port:** published on 127.0.0.1 only (not on the network).
