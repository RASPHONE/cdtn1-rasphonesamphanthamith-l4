from typing import Any, Dict

from src.errors import AppError
from src.schemas.technician_skill import (
    TechnicianSkillCreate,
    TechnicianSkillUpdate,
)


class TechnicianSkillService:
    def __init__(
        self,
        technician_repository,
        category_repository,
        skill_repository,
    ):
        self.technician_repo = technician_repository
        self.category_repo = category_repository
        self.skill_repo = skill_repository

    def list_skills(
        self,
        *,
        center_id: int,
        technician_id: int,
    ) -> Dict[str, Any]:
        self._get_owned_technician(
            center_id=center_id,
            technician_id=technician_id,
        )

        return {
            "technician_id": technician_id,
            "items": self.skill_repo.list_by_technician(technician_id),
        }

    def get_skill(
        self,
        *,
        center_id: int,
        technician_id: int,
        category_id: int,
    ) -> Dict[str, Any]:
        self._get_owned_technician(
            center_id=center_id,
            technician_id=technician_id,
        )

        skill = self.skill_repo.get_skill(technician_id, category_id)

        if not skill:
            raise AppError(
                "skill_not_found",
                "Technician skill not found.",
            )

        return skill

    def create_skill(
        self,
        *,
        center_id: int,
        technician_id: int,
        payload: TechnicianSkillCreate,
    ) -> Dict[str, Any]:
        self._get_owned_technician(
            center_id=center_id,
            technician_id=technician_id,
        )

        self._validate_proficiency(payload.proficiency)

        category = self.category_repo.get_by_id(payload.category_id)

        if not category:
            raise AppError(
                "category_not_found",
                "Issue category not found.",
            )

        if not category["is_active"]:
            raise AppError(
                "category_inactive",
                "Cannot add a skill for an inactive issue category.",
            )

        existing = self.skill_repo.get_skill(technician_id, payload.category_id)

        if existing:
            raise AppError(
                "skill_already_exists",
                "This technician already has a skill for this category.",
            )

        self.skill_repo.create(
            technician_id=technician_id,
            category_id=payload.category_id,
            proficiency=payload.proficiency,
        )

        created = self.skill_repo.get_skill(technician_id, payload.category_id)

        if not created:
            raise AppError(
                "skill_not_found",
                "Failed to retrieve the created skill.",
            )

        return created

    def update_skill(
        self,
        *,
        center_id: int,
        technician_id: int,
        category_id: int,
        payload: TechnicianSkillUpdate,
    ) -> Dict[str, Any]:
        self._get_owned_technician(
            center_id=center_id,
            technician_id=technician_id,
        )

        self._validate_proficiency(payload.proficiency)

        existing = self.skill_repo.get_skill(technician_id, category_id)

        if not existing:
            raise AppError(
                "skill_not_found",
                "Technician skill not found.",
            )

        self.skill_repo.update_proficiency(
            technician_id=technician_id,
            category_id=category_id,
            proficiency=payload.proficiency,
        )

        updated = self.skill_repo.get_skill(technician_id, category_id)

        if not updated:
            raise AppError(
                "skill_not_found",
                "Failed to retrieve the updated skill.",
            )

        return updated

    def delete_skill(
        self,
        *,
        center_id: int,
        technician_id: int,
        category_id: int,
    ) -> None:
        self._get_owned_technician(
            center_id=center_id,
            technician_id=technician_id,
        )

        existing = self.skill_repo.get_skill(technician_id, category_id)

        if not existing:
            raise AppError(
                "skill_not_found",
                "Technician skill not found.",
            )

        deleted = self.skill_repo.delete_skill(technician_id, category_id)

        if not deleted:
            raise AppError(
                "skill_not_found",
                "Technician skill not found.",
            )

    def _get_owned_technician(
        self,
        *,
        center_id: int,
        technician_id: int,
    ) -> Dict[str, Any]:
        technician = self.technician_repo.get_by_id(technician_id)

        if not technician:
            raise AppError(
                "technician_not_found",
                "Technician not found.",
            )

        if technician["center_id"] != center_id:
            raise AppError(
                "cross_center_access",
                "You cannot access another center's technician.",
            )

        return technician

    def _validate_proficiency(self, proficiency: int) -> None:
        if proficiency < 1 or proficiency > 5:
            raise AppError(
                "proficiency_out_of_range",
                "Proficiency must be between 1 and 5.",
            )
