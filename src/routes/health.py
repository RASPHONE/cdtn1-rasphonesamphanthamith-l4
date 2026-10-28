from fastapi import APIRouter

from src.db import ping

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    """Liveness of the API plus a quick database check.

    The API itself is 'ok' even when the database is down, so the frontend can
    still show a clear error instead of a connection failure.
    """
    return {"status": "ok", "database": "up" if ping() else "down"}
