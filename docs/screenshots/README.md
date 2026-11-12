# Screenshots — evidence for `docs/test-report.md`

One terminal screenshot per Test Report case, named after the case: `TC-01.png` … `TC-12.png`.
Each shows the command (`DB_PORT=5433 pytest -s -v tests/bt3 -k tc01`), the API calls it made,
the `observed:` line and PASSED/FAILED. The three cases that failed before the fixes also have
`TC-08-run1.png`, `TC-09-run1.png` and `TC-11-run1.png` (commit `cf58fa7`).
`full-suite.png` is the whole suite with the README command: `pytest -q` → 98 passed.

**BT3 packaging (12/11/2026, clean-machine test of `main` = `8f4cfdb` in an empty folder, Docker):**

| File | Command | Shows |
|---|---|---|
| `clean-1.png` | `docker compose ps; curl -s http://localhost:8000/health` | db, api, web `Up … (healthy)`; `{"status":"ok","database":"up"}` |
| `clean-2.png` | `docker compose exec api pytest -q` | `116 passed` inside the running system (re-run in the same clean folder after `git pull` to `5e9a63d`, the `v1.0` application code with the FR1/FR8/FR9 and demo-password tests) |
| `clean-3.png` | `docker compose exec api python scripts/migrate.py` and `… seed.py` | second run: `0 applied, 3 already up to date`, every table `+0` |
| `run3.png` | `docker compose exec api pytest -v -p no:cacheprovider tests/bt3/test_bt3_cases.py` | Test Report run 3: TC-01 … TC-12 PASSED |
| `sec-1.png` … `sec-7.png` | `bash scripts/security-checks.sh <n>` | the 7 items of `docs/checklist-bao-mat.md` |

| `deploy-1.png` | browser, https://l4-237480201is09-web.onrender.com | the public demo on Render (Deployment Guide §9), logged in as `manager2`: screen M1 with the 27 tickets of center 2 |
| `deploy-2.png` | Render dashboard → `l4-237480201is09-api` → Environment | the API's variables set on the platform (values hidden), service *Blueprint managed*, live on commit `5e9a63d` |

The student's Docker needs `sudo`, so the commands appear with a `sudo` prefix.
