#!/usr/bin/env bash
# Runs the 7 checks of docs/checklist-bao-mat.md against the system started with
#   docker compose up -d --build
# and prints each command with its result (the terminal is the evidence; one screenshot per item).
#
#   bash scripts/security-checks.sh        # all items
#   bash scripts/security-checks.sh 4      # one item (1 ... 7)
#
# Needs only git and Docker on the computer. Item 5 stops the database for a few seconds and
# starts it again. Item 7 downloads pip-audit and npm advisories (network needed).
set -u
cd "$(dirname "$0")/.."

run() { printf '\n$ %s\n' "$*"; eval "$@"; }
title() { printf '\n==================== %s ====================\n' "$*"; }
api() { docker compose exec -T api "$@"; }

item1() {
  title "1. No secret in the repository (OWASP A02)"
  run 'git log --all --oneline -- .env frontend/.env'
  echo "  expected: nothing (no .env was ever committed)"
  run 'git check-ignore -v .env frontend/.env'
  run "git ls-files | grep -E '(^|/)\.env$|\.pem$|\.key$' || true"
  run "grep -rniE \"(password|secret|api_key|token)[[:space:]]*[:=][[:space:]]*['\\\"][^'\\\"]{4,}['\\\"]\" src/ scripts/ frontend/src/ docker-compose.yml Dockerfile frontend/Dockerfile || true"
  echo "  expected: nothing (no secret value written in code or config)"
}

item2() {
  title "2. Input checked in the application, no injection (OWASP A05)"
  run "grep -rnE '(SELECT|INSERT|UPDATE|DELETE).*(\+ *[a-zA-Z_]|\\\$\{)' src/ || true"
  run "grep -rnE 'innerHTML|dangerouslySetInnerHTML|v-html' src/ frontend/src/ || true"
  run "grep -rnE 'exec\(|execSync|spawn\(|os\.system|shell=True' src/ frontend/src/ || true"
  echo "  expected: nothing for the three course greps"
  run 'api python scripts/security_probe.py 2'
  run 'api pytest -q -p no:cacheprovider tests/bt3/test_injection_db.py tests/bt3/test_bt3_cases.py -k "injection or tc08 or tc09"'
}

item3() {
  title "3. Access limited to the owner's center (OWASP A01, S2)"
  run 'api python scripts/security_probe.py 3'
  run 'api pytest -s -v -p no:cacheprovider tests/bt3 -k tc10'
}

item4() {
  title "4. Passwords stored as hashes (OWASP A04/A07, S3)"
  run "docker compose exec -T db sh -c 'psql -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" -c \"SELECT user_id, username, left(password_hash, 48) AS password_hash_start, length(password_hash) AS length FROM app_user ORDER BY user_id\"'"
  echo "  expected: pbkdf2_sha256\$600000\$<salt>\$<hash>, never the password itself"
  run 'api pytest -q -p no:cacheprovider tests/test_password_storage.py tests/bt3/test_password_storage_db.py'
}

item5() {
  title "5. Error messages reveal nothing internal (OWASP A10/A02, S4)"
  run 'api python scripts/security_probe.py 5'
  token=$(api python scripts/security_probe.py token)
  run 'docker compose stop db'
  run "api python scripts/security_probe.py 5db \"\$token\""
  run 'docker compose start db'
  until docker compose exec -T db pg_isready -q 2>/dev/null; do sleep 1; done
  run "api python -c \"import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health').read().decode())\""
  run 'api pytest -q -p no:cacheprovider tests/test_api.py -k "500 or 503 or envelope"'
}

item6() {
  title "6. Logs hold no secret or personal data (OWASP A09)"
  run 'docker compose logs api | wc -l'
  run "docker compose logs api | grep -ciE 'password|token|bearer|\\b0[0-9]{9}\\b' || true"
  echo "  expected: 0 (no password, token or phone number in the API log)"
  run "docker compose logs api | grep -m 3 'request_id='"
}

item7() {
  title "7. Dependencies pinned and audited (OWASP A03)"
  run "grep -cvE '^[[:space:]]*(#|\$)' requirements.txt; grep -cE '^[^#[:space:]][^=]*==[0-9]' requirements.txt"
  echo "  expected: the same number twice (every Python dependency pinned with ==); frontend: package-lock.json"
  run 'docker run --rm -v "$PWD:/src:ro" -w /src python:3.12.7-slim-bookworm sh -c "pip install -q --disable-pip-version-check --root-user-action=ignore pip-audit==2.7.3 && pip-audit -r requirements.txt"'
  run 'docker run --rm -v "$PWD/frontend:/app:ro" -w /app node:22.14.0-alpine npm audit'
}

if [ $# -eq 0 ]; then set -- 1 2 3 4 5 6 7; fi
for n in "$@"; do "item$n"; done
