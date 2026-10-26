from datetime import datetime, timedelta

import jwt

from src.config import get_settings
from src.errors import AppError


# Minimal demo users for the BT2 prototype.
# In a real system, these would be in a `users` table with hashed passwords.
DEMO_USERS = {
    "manager1": {
        "user_id": 1,
        "username": "manager1",
        "password": "manager123",
        "role": "CENTER_MANAGER",
        "center_id": 1,
    },
    "manager2": {
        "user_id": 2,
        "username": "manager2",
        "password": "manager123",
        "role": "CENTER_MANAGER",
        "center_id": 2,
    },
}


class AuthService:
    def login(self, username: str, password: str) -> dict:
        user = DEMO_USERS.get(username)

        if not user or user["password"] != password:
            raise AppError(
                "invalid_credentials",
                "Invalid username or password.",
            )

        settings = get_settings()
        expire = datetime.utcnow() + timedelta(
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
