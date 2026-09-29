from __future__ import annotations
from uuid import UUID

from sqlalchemy.orm import Session, selectinload

from domain.locations.entity import LocationConfig
from infrastructure.persistence.models import LocationRow, ZoneRow


class LocationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save_config(self, config: LocationConfig) -> tuple[LocationRow, list[ZoneRow]]:
        location = config.location
        location_row = LocationRow(name=location.name)
        location_row.zones = [
            ZoneRow(
                name=z.name,
                moisture_threshold_low=z.moisture_threshold_low,
                moisture_threshold_high=z.moisture_threshold_high,
                schedule=z.schedule,
            )
            for z in location.zones
        ]

        try:
            self._session.add(location_row)
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise

        self._session.refresh(location_row)
        for zone_row in location_row.zones:
            self._session.refresh(zone_row)
        return location_row, list(location_row.zones)

    def get_config(self, location_id: UUID) -> tuple[LocationRow, list[ZoneRow]] | None:
        row = (
            self._session.query(LocationRow)
            .options(selectinload(LocationRow.zones))
            .filter(LocationRow.id == str(location_id))
            .first()
        )
        if row is None:
            return None
        return row, list(row.zones)

    def list_locations(self) -> list[LocationRow]:
        return (
            self._session.query(LocationRow)
            .order_by(LocationRow.created_at.desc())
            .all()
        )

    def delete_location(self, location_id: UUID) -> bool:
        row = self._session.get(LocationRow, str(location_id))
        if row is None:
            return False
        self._session.delete(row)
        self._session.commit()
        return True