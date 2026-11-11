import logging
import secrets
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Values that were published in this public repository (tag v0.2): a token signed with
# one of them could be forged by anyone, so the API refuses to start with them.
PUBLISHED_JWT_SECRETS = frozenset({
    "change_me_to_a_long_random_string_32_chars_min",   # .env.example in v0.2
    "dev_only_change_me_in_env",                        # default in this file in v0.2
})
MIN_JWT_SECRET_LENGTH = 32


class Settings(BaseSettings):
    """All runtime configuration comes from environment variables / .env.

    Every variable is listed with a sample value in `.env.example`.
    Empty values in .env fall back to the defaults below.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_ignore_empty=True,
    )

    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "mekong_l4"
    db_user: str = "postgres"
    db_password: str = ""
    db_connect_timeout: int = 3

    port: int = 8000

    # Empty (the .env.example value) = a random secret per API process: demo logins
    # stop working when the API restarts. Set 32+ random characters to keep them.
    jwt_secret: str = Field(default="", validate_default=True)
    access_token_expire_minutes: int = 60
    # Password given to the demo accounts by scripts/seed.py (stored hashed only).
    demo_password: str = "manager123"

    # Business clock for "appointment must be in the future" (US5 AC2).
    app_timezone: str = "Asia/Ho_Chi_Minh"

    # Comma-separated list of frontend origins allowed to call the API.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    log_level: str = "INFO"

    @field_validator("jwt_secret")
    @classmethod
    def _jwt_secret_must_be_private(cls, value: str) -> str:
        if not value:
            logging.getLogger("l4.config").warning(
                "JWT_SECRET is not set: using a random secret for this process "
                "(logins end when the API restarts)."
            )
            return secrets.token_urlsafe(48)
        if value in PUBLISHED_JWT_SECRETS:
            raise ValueError(
                "JWT_SECRET is a sample value published in the repository. "
                "Leave it empty in .env or set your own random string."
            )
        if len(value) < MIN_JWT_SECRET_LENGTH:
            raise ValueError(f"JWT_SECRET must be at least {MIN_JWT_SECRET_LENGTH} characters.")
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def psycopg_conninfo(self) -> str:
        return (
            f"host={self.db_host} "
            f"port={self.db_port} "
            f"dbname={self.db_name} "
            f"user={self.db_user} "
            f"password={self.db_password}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
