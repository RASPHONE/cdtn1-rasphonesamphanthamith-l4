from fastapi import APIRouter, Depends, Response

from src.repositories.issue_category_repository import (
    PostgresIssueCategoryRepository,
)
from src.repositories.technician_repository import PostgresTechnicianRepository
from src.repositories.technician_skill_repository import (
    PostgresTechnicianSkillRepository,
)
from src.schemas.technician_skill import (
    TechnicianSkillCreate,
    TechnicianSkillList,
    TechnicianSkillRead,
    TechnicianSkillUpdate,
)
from src.security import get_current_center_id
from src.services.technician_skill_service import TechnicianSkillService

router = APIRouter(prefix="/api/technicians", tags=["technician_skills"])


def get_technician_skill_service() -> TechnicianSkillService:
    return TechnicianSkillService(
        technician_repository=PostgresTechnicianRepository(),
        category_repository=PostgresIssueCategoryRepository(),
        skill_repository=PostgresTechnicianSkillRepository(),
    )


@router.get(
    "/{technician_id}/skills",
    response_model=TechnicianSkillList,
)
def list_technician_skills(
    technician_id: int,
    center_id: int = Depends(get_current_center_id),
    service: TechnicianSkillService = Depends(get_technician_skill_service),
):
    return service.list_skills(
        center_id=center_id,
        technician_id=technician_id,
    )


@router.get(
    "/{technician_id}/skills/{category_id}",
    response_model=TechnicianSkillRead,
)
def get_technician_skill(
    technician_id: int,
    category_id: int,
    center_id: int = Depends(get_current_center_id),
    service: TechnicianSkillService = Depends(get_technician_skill_service),
):
    return service.get_skill(
        center_id=center_id,
        technician_id=technician_id,
        category_id=category_id,
    )


@router.post(
    "/{technician_id}/skills",
    response_model=TechnicianSkillRead,
    status_code=201,
)
def create_technician_skill(
    technician_id: int,
    payload: TechnicianSkillCreate,
    center_id: int = Depends(get_current_center_id),
    service: TechnicianSkillService = Depends(get_technician_skill_service),
):
    return service.create_skill(
        center_id=center_id,
        technician_id=technician_id,
        payload=payload,
    )


@router.patch(
    "/{technician_id}/skills/{category_id}",
    response_model=TechnicianSkillRead,
)
def update_technician_skill(
    technician_id: int,
    category_id: int,
    payload: TechnicianSkillUpdate,
    center_id: int = Depends(get_current_center_id),
    service: TechnicianSkillService = Depends(get_technician_skill_service),
):
    return service.update_skill(
        center_id=center_id,
        technician_id=technician_id,
        category_id=category_id,
        payload=payload,
    )


@router.delete(
    "/{technician_id}/skills/{category_id}",
    status_code=204,
)
def delete_technician_skill(
    technician_id: int,
    category_id: int,
    center_id: int = Depends(get_current_center_id),
    service: TechnicianSkillService = Depends(get_technician_skill_service),
):
    service.delete_skill(
        center_id=center_id,
        technician_id=technician_id,
        category_id=category_id,
    )
    return Response(status_code=204)
