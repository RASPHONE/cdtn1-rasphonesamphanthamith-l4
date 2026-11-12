"""BUG-014 regression on the real database: app_user holds hashes only."""
import psycopg
import pytest

from tests.bt3.conftest import _run_script, login


def test_app_user_stores_only_pbkdf2_hashes(api, pg):
    rows = pg["query"]("SELECT username, password_hash FROM app_user ORDER BY user_id")
    assert [row["username"] for row in rows] == ["manager1", "manager2"]
    assert all(row["password_hash"].startswith("pbkdf2_sha256$600000$") for row in rows)
    assert all("manager123" not in row["password_hash"] for row in rows)
    assert login(api, "manager1")       # the documented demo password still works


def test_database_refuses_a_password_in_clear(pg):
    with pytest.raises(psycopg.errors.CheckViolation):
        pg["query"]("""INSERT INTO app_user (user_id, username, password_hash, role, center_id)
                       VALUES (99, 'clear', 'manager123', 'CENTER_MANAGER', 1)""")


def test_changing_demo_password_and_reseeding_changes_the_login(api, pg, monkeypatch):
    # Deployment Guide §9: the demo password is changed by setting DEMO_PASSWORD and restarting
    # (the API start-up runs seed.py). A second run with the same value changes nothing.
    monkeypatch.setenv("DEMO_PASSWORD", "Another-Demo-Pass-1")
    first = _run_script("seed.py", pg["db_name"])
    hashes = [row["password_hash"] for row in pg["query"]("SELECT password_hash FROM app_user ORDER BY user_id")]
    second = _run_script("seed.py", pg["db_name"])
    old = api.post("/api/auth/login", json={"username": "manager2", "password": "manager123"})
    new = api.post("/api/auth/login", json={"username": "manager2", "password": "Another-Demo-Pass-1"})
    assert "Demo password changed to the DEMO_PASSWORD value for: manager1, manager2" in first
    assert "Demo password changed" not in second
    assert hashes == [row["password_hash"] for row in pg["query"]("SELECT password_hash FROM app_user ORDER BY user_id")]
    assert (old.status_code, new.status_code) == (401, 200)
