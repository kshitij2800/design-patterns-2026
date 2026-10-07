from __future__ import annotations
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from application.automation.dto import RecommendationDto, StrategySavedDto, StrategyUpdateDto
from application.automation.errors import LocationNotFoundError
from application.automation.service import AutomationService
from domain.automation.strategy import UnknownStrategyError
from infrastructure.db import get_db
from infrastructure.persistence.automation_repository import AutomationRepository

router = APIRouter(prefix="/api/locations/{location_id}/automation", tags=["automation"])


def get_service(db: Session = Depends(get_db)) -> AutomationService:
    return AutomationService(AutomationRepository(db))


@router.put("", response_model=StrategySavedDto)
def save_strategy(
    location_id: UUID,
    body: StrategyUpdateDto,
    service: AutomationService = Depends(get_service),
):
    """Persist the active strategy key for this location (upsert)."""
    try:
        return service.set_strategy(location_id, body.strategy_key)
    except UnknownStrategyError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except LocationNotFoundError:
        raise HTTPException(status_code=404, detail="Location not found")


@router.post("/evaluate", response_model=RecommendationDto)
def evaluate(location_id: UUID, service: AutomationService = Depends(get_service)):
    """Evaluate every zone with the PERSISTED strategy, using latest readings + zone thresholds."""
    try:
        return service.evaluate(location_id)
    except UnknownStrategyError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except LocationNotFoundError:
        raise HTTPException(status_code=404, detail="Location not found")