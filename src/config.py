from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


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

    jwt_secret: str = "dev_only_change_me_in_env"
    access_token_expire_minutes: int = 60

    # Business clock for "appointment must be in the future" (US5 AC2).
    app_timezone: str = "Asia/Ho_Chi_Minh"

    # Comma-separated list of frontend origins allowed to call the API.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    log_level: str = "INFO"

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
