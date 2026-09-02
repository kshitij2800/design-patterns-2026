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