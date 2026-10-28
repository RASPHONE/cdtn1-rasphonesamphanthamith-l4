from pydantic import BaseModel


class IssueCategoryRead(BaseModel):
    category_id: int
    category_name: str
    default_priority: str
