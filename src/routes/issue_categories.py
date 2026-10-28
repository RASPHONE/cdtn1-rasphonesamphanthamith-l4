from typing import List

from fastapi import APIRouter, Depends

from src.repositories.issue_category_repository import PostgresIssueCategoryRepository
from src.schemas.issue_category import IssueCategoryRead
from src.security import get_current_token_payload
from src.services.issue_category_service import IssueCategoryService

router = APIRouter(prefix="/api/issue-categories", tags=["issue_categories"])


def get_issue_category_service() -> IssueCategoryService:
    return IssueCategoryService(category_repository=PostgresIssueCategoryRepository())


@router.get("", response_model=List[IssueCategoryRead])
def list_issue_categories(
    _token: dict = Depends(get_current_token_payload),
    service: IssueCategoryService = Depends(get_issue_category_service),
):
    return service.list_active_categories()
