from typing import List

from pydantic import BaseModel


class TechnicianSkillCreate(BaseModel):
    category_id: int
    proficiency: int


class TechnicianSkillUpdate(BaseModel):
    proficiency: int


class TechnicianSkillRead(BaseModel):
    technician_id: int
    category_id: int
    category_name: str
    proficiency: int


class TechnicianSkillList(BaseModel):
    technician_id: int
    items: List[TechnicianSkillRead]
