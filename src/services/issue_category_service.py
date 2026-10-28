from typing import Any, Dict, List


class IssueCategoryService:
    """Reference data for the M1 filter (FR9). Categories come from the
    issue_category table, never from a hard-coded list (NFR7)."""

    def __init__(self, category_repository):
        self.category_repo = category_repository

    def list_active_categories(self) -> List[Dict[str, Any]]:
        return self.category_repo.list_active()
