"""HTTP probes for the security checklist (docs/checklist-bao-mat.md), items 2, 3 and 5.

Runs inside the api container (standard library only), called by scripts/security-checks.sh:
    docker compose exec -T api python scripts/security_probe.py 3
Each probe prints the request, the HTTP status and the body, so the terminal is the evidence.
"""
import json
import os
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000"


def call(method, path, body=None, token=None, raw=None):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    request = urllib.request.Request(BASE + path, data=data, method=method)
    if data is not None:
        request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, response.read().decode()
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode()


def show(label, method, path, keep=None, **kwargs):
    status, text = call(method, path, **kwargs)
    if keep and status < 400:   # print only the named fields of a success (no customer data on screen)
        text = json.dumps({key: json.loads(text)[key] for key in keep})
    print(f"  {label}\n    {method} {path} -> HTTP {status} {text[:300]}")
    return status, text


def login(username):
    status, text = call("POST", "/api/auth/login",
                        {"username": username, "password": os.environ.get("DEMO_PASSWORD", "manager123")})
    if status != 200:
        sys.exit(f"login {username} failed: HTTP {status} {text}")
    return json.loads(text)["access_token"]


def item2():
    token = login("manager2")
    show("SQL text in a filter value (expected 400, not a ticket list)", "GET",
         "/api/tickets/unassigned?priority=CAO%27%20OR%20%271%27%3D%271", token=token)
    show("SQL text in a path id (expected 400)", "GET", "/api/tickets/8036%20OR%201=1", token=token)


def item3():
    manager1 = login("manager1")
    show("manager1 (center 1) reads a ticket of center 2 (expected 403)", "GET", "/api/tickets/8036", token=manager1)
    show("manager1 (center 1) moves an appointment of center 2 (expected 403)", "PATCH", "/api/appointments/900004",
         body={"gio_bat_dau": "10:00", "gio_ket_thuc": "11:00"}, token=manager1)
    show("manager2 (center 2) reads the same ticket (expected 200)", "GET", "/api/tickets/8036",
         keep=["ticket_id", "ticket_code", "center_id"], token=login("manager2"))


def item5():
    token = login("manager2")
    show("Body that is not JSON (expected 400 envelope)", "POST", "/api/appointments", raw=b'{"ticket_id": 1', token=token)
    show("Unknown path (expected 404 envelope)", "GET", "/api/nope", token=token)
    show("Wrong method (expected 405 envelope)", "PUT", "/api/appointments", body={}, token=token)
    head, payload, signature = token.split(".")
    forged = ".".join([head, payload, ("B" if signature[0] == "A" else "A") + signature[1:]])
    show("Token signature changed by one character (expected 401)", "GET", "/api/tickets/unassigned", token=forged)


def item5_database_down():
    show("Database stopped (expected 503 database_unavailable, no host or SQL)", "GET",
         "/api/tickets/unassigned", keep=["total"], token=sys.argv[2])


def token_only():
    print(login("manager2"))


if __name__ == "__main__":
    probes = {"2": item2, "3": item3, "5": item5, "5db": item5_database_down, "token": token_only}
    probes[sys.argv[1]]()
