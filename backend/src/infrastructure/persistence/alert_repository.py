from __future__ import annotations
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from application.alerts.dto import AlertDto
from infrastructure.persistence.models import AlertRow


def _uuid(value: str | None) -> UUID | None:
    return UUID(value) if value else None


def _str(value: UUID | None) -> str | None:
    return str(value) if value else None


def _row_to_dto(row: AlertRow) -> AlertDto:
    return AlertDto(
        id=UUID(row.id),
        location_id=_uuid(row.location_id),
        zone_id=_uuid(row.zone_id),
        device_id=_uuid(row.device_id),
        severity=row.severity,
        message=row.message,
        event_type=row.event_type,
        status=row.status,
        created_at=row.created_at,
    )


class AlertRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def insert(
        self,
        *,
        event_type: str,
        severity: str,
        message: str,
        device_id: UUID | None,
        location_id: UUID | None,
        zone_id: UUID | None,
    ) -> AlertDto:
        row = AlertRow(
            event_type=event_type,
            severity=severity,
            message=message,
            status="active",
            device_id=_str(device_id),
            location_id=_str(location_id),
            zone_id=_str(zone_id),
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return _row_to_dto(row)

    def list_alerts(
        self,
        *,
        status: str = "active",
        location_id: UUID | None = None,
        zone_id: UUID | None = None,
        since: datetime | None = None,
        limit: int = 50,
    ) -> list[AlertDto]:
        query = self._session.query(AlertRow)
        if status != "all":
            query = query.filter(AlertRow.status == status)
        if location_id is not None:
            query = query.filter(AlertRow.location_id == str(location_id))
        if zone_id is not None:
            query = query.filter(AlertRow.zone_id == str(zone_id))
        if since is not None:
            query = query.filter(AlertRow.created_at >= since)
        rows = query.order_by(AlertRow.created_at.desc()).limit(limit).all()
        return [_row_to_dto(r) for r in rows]