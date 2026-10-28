import pytest

from src.errors import AppError
from src.schemas.technician_skill import (
    TechnicianSkillCreate,
    TechnicianSkillUpdate,
)
from src.services.technician_skill_service import TechnicianSkillService
from tests.fakes import (
    FakeIssueCategoryRepository,
    FakeTechnicianRepository,
    FakeTechnicianSkillRepository,
)


def make_technician(technician_id=1, center_id=1, is_active=True):
    return {
        "technician_id": technician_id,
        "center_id": center_id,
        "is_active": is_active,
    }


def make_category(category_id=1, category_name="MAN_HINH", is_active=True):
    return {
        "category_id": category_id,
        "category_name": category_name,
        "is_active": is_active,
    }


def make_skill(technician_id=1, category_id=1, proficiency=4):
    return {
        "technician_id": technician_id,
        "category_id": category_id,
        "category_name": "MAN_HINH",
        "proficiency": proficiency,
    }


def make_service(skills=None):
    technicians = [
        make_technician(technician_id=1, center_id=1),
        make_technician(technician_id=2, center_id=2),
    ]

    categories = [
        make_category(category_id=1, category_name="MAN_HINH", is_active=True),
        make_category(category_id=7, category_name="CU", is_active=False),
    ]

    technician_repo = FakeTechnicianRepository(technicians)
    category_repo = FakeIssueCategoryRepository(categories)
    skill_repo = FakeTechnicianSkillRepository(skills)

    service = TechnicianSkillService(
        technician_repository=technician_repo,
        category_repository=category_repo,
        skill_repository=skill_repo,
    )

    return service, skill_repo


def test_create_valid_skill():
    service, _ = make_service()
    payload = TechnicianSkillCreate(category_id=1, proficiency=4)

    result = service.create_skill(
        center_id=1,
        technician_id=1,
        payload=payload,
    )

    assert result["technician_id"] == 1
    assert result["category_id"] == 1
    assert result["proficiency"] == 4


def test_create_duplicate_skill_fails():
    service, _ = make_service([make_skill()])
    payload = TechnicianSkillCreate(category_id=1, proficiency=3)

    with pytest.raises(AppError) as exc:
        service.create_skill(
            center_id=1,
            technician_id=1,
            payload=payload,
        )

    assert exc.value.code == "skill_already_exists"


def test_create_skill_with_proficiency_zero_fails():
    service, _ = make_service()
    payload = TechnicianSkillCreate(category_id=1, proficiency=0)

    with pytest.raises(AppError) as exc:
        service.create_skill(
            center_id=1,
            technician_id=1,
            payload=payload,
        )

    assert exc.value.code == "proficiency_out_of_range"


def test_create_skill_with_proficiency_six_fails():
    service, _ = make_service()
    payload = TechnicianSkillCreate(category_id=1, proficiency=6)

    with pytest.raises(AppError) as exc:
        service.create_skill(
            center_id=1,
            technician_id=1,
            payload=payload,
        )

    assert exc.value.code == "proficiency_out_of_range"


def test_create_skill_with_inactive_category_fails():
    service, _ = make_service()
    payload = TechnicianSkillCreate(category_id=7, proficiency=3)

    with pytest.raises(AppError) as exc:
        service.create_skill(
            center_id=1,
            technician_id=1,
            payload=payload,
        )

    assert exc.value.code == "category_inactive"


def test_create_skill_with_missing_category_fails():
    service, _ = make_service()
    payload = TechnicianSkillCreate(category_id=999, proficiency=3)

    with pytest.raises(AppError) as exc:
        service.create_skill(
            center_id=1,
            technician_id=1,
            payload=payload,
        )

    assert exc.value.code == "category_not_found"


def test_create_skill_cross_center_fails():
    service, _ = make_service()
    payload = TechnicianSkillCreate(category_id=1, proficiency=3)

    with pytest.raises(AppError) as exc:
        service.create_skill(
            center_id=1,
            technician_id=2,
            payload=payload,
        )

    assert exc.value.code == "cross_center_access"


def test_update_skill_proficiency():
    service, _ = make_service([make_skill(proficiency=3)])
    payload = TechnicianSkillUpdate(proficiency=5)

    result = service.update_skill(
        center_id=1,
        technician_id=1,
        category_id=1,
        payload=payload,
    )

    assert result["proficiency"] == 5


def test_update_missing_skill_fails():
    service, _ = make_service()
    payload = TechnicianSkillUpdate(proficiency=5)

    with pytest.raises(AppError) as exc:
        service.update_skill(
            center_id=1,
            technician_id=1,
            category_id=1,
            payload=payload,
        )

    assert exc.value.code == "skill_not_found"


def test_update_skill_with_invalid_proficiency_fails():
    service, _ = make_service([make_skill(proficiency=3)])
    payload = TechnicianSkillUpdate(proficiency=9)

    with pytest.raises(AppError) as exc:
        service.update_skill(
            center_id=1,
            technician_id=1,
            category_id=1,
            payload=payload,
        )

    assert exc.value.code == "proficiency_out_of_range"


def test_delete_skill():
    service, skill_repo = make_service([make_skill()])

    service.delete_skill(
        center_id=1,
        technician_id=1,
        category_id=1,
    )

    assert skill_repo.get_skill(1, 1) is None


def test_delete_missing_skill_fails():
    service, _ = make_service()

    with pytest.raises(AppError) as exc:
        service.delete_skill(
            center_id=1,
            technician_id=1,
            category_id=1,
        )

    assert exc.value.code == "skill_not_found"


def test_list_skills():
    service, _ = make_service([make_skill()])

    result = service.list_skills(
        center_id=1,
        technician_id=1,
    )

    assert len(result) == 1
    assert result[0]["technician_id"] == 1
