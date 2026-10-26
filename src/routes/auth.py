from fastapi import APIRouter, Depends

from src.schemas.auth import LoginRequest, LoginResponse
from src.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])


def get_auth_service() -> AuthService:
    return AuthService()


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    service: AuthService = Depends(get_auth_service),
):
    return service.login(
        username=payload.username,
        password=payload.password,
    )
