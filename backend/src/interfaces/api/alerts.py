from __future__ import annotations
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from application.alerts.dto import ALERT_STATUS_FILTERS, AlertDto
from infrastructure.db import get_db
from infrastructure.persistence.alert_repository import AlertRepository

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


def get_alerts(db: Session = Depends(get_db)) -> AlertRepository:
    return AlertRepository(db)


@router.get(
    "",
    response_model=list[AlertDto],
    responses={400: {"description": "status is not active, resolved or all"}},
)
def list_alerts(
    status: str = Query("active", description="active (default), resolved or all"),
    location_id: UUID | None = None,
    zone_id: UUID | None = None,
    since: datetime | None = Query(None, description="Only alerts with created_at at or after this time"),
    limit: int = Query(50, ge=1, le=200),
    alerts: AlertRepository = Depends(get_alerts),
):
    """Persisted alerts, newest created_at first. Written only by AlertPersistenceSubscriber."""
    if status not in ALERT_STATUS_FILTERS:
        raise HTTPException(status_code=400, detail="status must be one of: active, resolved, all")
    return alerts.list_alerts(
        status=status, location_id=location_id, zone_id=zone_id, since=since, limit=limit
    )