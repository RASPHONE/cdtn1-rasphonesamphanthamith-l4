import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

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

    try:
        # Only HS256 is accepted, and a token without an expiry or without the claims the
        # API reads is refused with 401 (it would otherwise fail later with a 500).
        return jwt.decode(
            token, settings.jwt_secret, algorithms=["HS256"],
            options={"require": ["exp", "sub", "user_id", "role", "center_id"]},
        )
    except jwt.ExpiredSignatureError:
        raise AppError("unauthorized", "Token has expired.")
    except jwt.PyJWTError:
        raise AppError("unauthorized", "Invalid authentication token.")


def get_current_center_id(payload: dict = Depends(get_current_token_payload)) -> int:
    return payload["center_id"]


def get_current_user_id(payload: dict = Depends(get_current_token_payload)) -> int:
    return payload["user_id"]


def get_current_role(payload: dict = Depends(get_current_token_payload)) -> str:
    return payload.get("role", "")
