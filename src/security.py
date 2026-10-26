from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

import jwt

from src.config import get_settings
from src.errors import AppError

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login",
    auto_error=False,  # Allows us to throw our custom AppError instead of HTTPException
)


def get_current_token_payload(token: str = Depends(oauth2_scheme)) -> dict:
    if not token:
        raise AppError("unauthorized", "Authentication required.")

    settings = get_settings()
    if not settings.jwt_secret:
        raise AppError("internal_error", "Server authentication is not configured.")

    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise AppError("unauthorized", "Token has expired.")
    except jwt.PyJWTError:
        raise AppError("unauthorized", "Invalid authentication token.")


def get_current_center_id(payload: dict = Depends(get_current_token_payload)) -> int:
    return payload["center_id"]


def get_current_user_id(payload: dict = Depends(get_current_token_payload)) -> int:
    return payload["user_id"]
