from datetime import datetime, timedelta, timezone

import jwt

from src.config import get_settings
from src.errors import AppError
from src.services.password_hashing import verify_against_dummy, verify_password


class AuthService:
    """Demo login (FR12). Accounts live in table app_user with hashed passwords only."""

    def __init__(self, user_repository):
        self.user_repo = user_repository

    def login(self, username: str, password: str) -> dict:
        user = self.user_repo.get_active_by_username(username)

        if user is None:
            verify_against_dummy(password)
            valid = False
        else:
            valid = verify_password(password, user["password_hash"])

        if not valid:
            raise AppError(
                "invalid_credentials",
                "Invalid username or password.",
            )

        settings = get_settings()
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.access_token_expire_minutes
        )

        payload = {
            "sub": user["username"],
            "user_id": user["user_id"],
            "role": user["role"],
            "center_id": user["center_id"],
            "exp": expire,
        }

        token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")

        return {
            "access_token": token,
            "token_type": "bearer",
            "role": user["role"],
            "center_id": user["center_id"],
        }
