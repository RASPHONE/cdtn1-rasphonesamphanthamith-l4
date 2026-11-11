from fastapi import APIRouter, Depends

from src.schemas.auth import LoginRequest, LoginResponse
from src.repositories.user_repository import PostgresUserRepository
from src.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])


def get_auth_service() -> AuthService:
    return AuthService(user_repository=PostgresUserRepository())


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    service: AuthService = Depends(get_auth_service),
):
    return service.login(
        username=payload.username,
        password=payload.password,
    )
