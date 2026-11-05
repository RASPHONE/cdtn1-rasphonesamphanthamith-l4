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
