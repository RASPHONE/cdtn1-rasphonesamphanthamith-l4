"""BUG-014 regression: demo passwords are stored and checked only as PBKDF2 hashes."""
import pytest

from src.errors import AppError
from src.services.auth_service import AuthService
from src.services.password_hashing import hash_password, verify_password
from tests.fakes import FakeUserRepository


def test_hash_is_not_the_password_and_is_salted():
    first, second = hash_password("manager123", 1_000), hash_password("manager123", 1_000)
    assert first.startswith("pbkdf2_sha256$1000$")
    assert "manager123" not in first
    assert first != second                      # random salt per hash


def test_verify_accepts_only_the_right_password():
    stored = hash_password("manager123", 1_000)
    assert verify_password("manager123", stored)
    assert not verify_password("manager124", stored)
    assert not verify_password("manager123", "manager123")   # a value in clear never matches


def test_default_iteration_count_is_the_owasp_value():
    assert hash_password("x").split("$")[1] == "600000"


def test_login_checks_the_hash_and_gives_one_message_for_any_failure():
    service = AuthService(user_repository=FakeUserRepository())
    assert service.login("manager2", "manager123")["center_id"] == 2
    for username, password in (("manager2", "wrong"), ("nobody", "manager123")):
        with pytest.raises(AppError) as error:
            service.login(username, password)
        assert (error.value.code, error.value.message) == ("invalid_credentials", "Invalid username or password.")
