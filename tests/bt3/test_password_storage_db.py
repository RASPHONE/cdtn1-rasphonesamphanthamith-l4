"""BUG-014 regression on the real database: app_user holds hashes only."""
import psycopg
import pytest

from tests.bt3.conftest import login


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
