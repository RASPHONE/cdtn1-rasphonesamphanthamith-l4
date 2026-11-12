"""BUG-011 regression: the API must not run with a JWT secret that is public."""
import pytest
from pydantic import ValidationError

from src.config import PUBLISHED_JWT_SECRETS, Settings


@pytest.mark.parametrize("secret", sorted(PUBLISHED_JWT_SECRETS))
def test_published_secret_is_refused_at_startup(secret):
    with pytest.raises(ValidationError, match="published in the repository"):
        Settings(_env_file=None, jwt_secret=secret)


def test_short_secret_is_refused():
    with pytest.raises(ValidationError, match="at least 32 characters"):
        Settings(_env_file=None, jwt_secret="too-short")


def test_empty_secret_becomes_a_random_one_per_process():
    first = Settings(_env_file=None, jwt_secret="").jwt_secret
    second = Settings(_env_file=None, jwt_secret="").jwt_secret
    assert len(first) >= 32 and first != second


def test_token_without_expiry_or_center_is_refused(client):
    import jwt as pyjwt

    from src.config import get_settings

    secret = get_settings().jwt_secret
    base = {"sub": "manager1", "user_id": 1, "role": "CENTER_MANAGER", "center_id": 1}
    for drop in ("exp", "center_id"):
        claims = {**base, "exp": 4102444800}
        claims.pop(drop)
        token = pyjwt.encode(claims, secret, algorithm="HS256")
        response = client.get("/api/tickets/unassigned", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401, drop


def test_database_url_replaces_the_db_fields():
    # Render gives the database as one URL (render.yaml, Deployment Guide §9).
    settings = Settings(_env_file=None, db_host="ignored", db_password="ignored",
                        database_url="postgresql://l4_user:p%40ss%20word@dpg-abc-a/mekong_l4")
    assert (settings.db_host, settings.db_port, settings.db_user, settings.db_password, settings.db_name) == (
        "dpg-abc-a", 5432, "l4_user", "p@ss word", "mekong_l4")
    assert "password='p@ss word'" in settings.psycopg_conninfo


def test_database_url_must_be_postgresql():
    with pytest.raises(ValidationError, match="DATABASE_URL"):
        Settings(_env_file=None, database_url="mysql://user@host/db")
