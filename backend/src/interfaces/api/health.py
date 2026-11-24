from fastapi import APIRouter
from pydantic import BaseModel

from infrastructure.db import check_db

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    db: str


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    db_status = check_db()
    overall = "ok" if db_status == "ok" else "degraded"
    return HealthResponse(status=overall, db=db_status)

# Phase 11: main.py is kept unchanged, so the alerts router is mounted onto the
# health router (which has no prefix), giving the path /api/alerts.
from interfaces.api.alerts import router as alerts_router  # noqa: E402

router.include_router(alerts_router)