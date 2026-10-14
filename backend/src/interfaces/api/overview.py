from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from application.overview.dto import LocationOverviewDto
from application.overview.errors import LocationNotFoundError
from application.overview.facade import LocationOverviewFacade
from infrastructure.db import get_db

router = APIRouter(prefix="/api/locations", tags=["overview"])


def get_facade(db: Session = Depends(get_db)) -> LocationOverviewFacade:
    return LocationOverviewFacade.from_session(db)


@router.get("/{location_id}/overview", response_model=LocationOverviewDto)
def get_overview(location_id: UUID, facade: LocationOverviewFacade = Depends(get_facade)):
    """Dashboard snapshot for one location: assigned devices, zones, latest readings,
    saved strategy and a freshly computed recommendation."""
    try:
        return facade.get_overview(location_id)
    except LocationNotFoundError:
        raise HTTPException(status_code=404, detail="Location not found")