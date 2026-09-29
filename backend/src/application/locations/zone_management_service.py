from __future__ import annotations
from uuid import UUID

from sqlalchemy.orm import Session

from application.locations.dto import ZoneRequestDto
from application.locations.zone_assignment_service import ZoneNotFoundError
from domain.locations.errors import ConfigurationError
from domain.locations.validation import validate_zone_fields
from infrastructure.persistence.models import DeviceRow, LocationRow, ZoneRow


class LocationNotFoundError(Exception):
    pass


class ZoneManagementService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def _get_location(self, location_id: UUID) -> LocationRow:
        location = self._session.get(LocationRow, str(location_id))
        if location is None:
            raise LocationNotFoundError(str(location_id))
        return location

    def _get_zone(self, location_id: UUID, zone_id: UUID) -> ZoneRow:
        self._get_location(location_id)
        zone = self._session.get(ZoneRow, str(zone_id))
        if zone is None or zone.location_id != str(location_id):
            raise ZoneNotFoundError(str(zone_id))
        return zone

    def _check_unique_name(self, location_id: UUID, name: str, exclude_zone_id: str | None = None) -> None:
        zones = self._session.query(ZoneRow).filter(ZoneRow.location_id == str(location_id)).all()
        for z in zones:
            if z.id != exclude_zone_id and z.name.casefold() == name.casefold():
                raise ConfigurationError(f"Duplicate zone name: '{name}'")

    def add_zone(self, location_id: UUID, body: ZoneRequestDto) -> ZoneRow:
        self._get_location(location_id)
        name = validate_zone_fields(body.name, body.moisture_threshold_low, body.moisture_threshold_high)
        self._check_unique_name(location_id, name)
        row = ZoneRow(
            location_id=str(location_id),
            name=name,
            moisture_threshold_low=body.moisture_threshold_low,
            moisture_threshold_high=body.moisture_threshold_high,
            schedule=dict(body.schedule),
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return row

    def update_zone(self, location_id: UUID, zone_id: UUID, body: ZoneRequestDto) -> ZoneRow:
        zone = self._get_zone(location_id, zone_id)
        name = validate_zone_fields(body.name, body.moisture_threshold_low, body.moisture_threshold_high)
        self._check_unique_name(location_id, name, exclude_zone_id=zone.id)
        zone.name = name
        zone.moisture_threshold_low = body.moisture_threshold_low
        zone.moisture_threshold_high = body.moisture_threshold_high
        zone.schedule = dict(body.schedule)
        self._session.commit()
        self._session.refresh(zone)
        return zone

    def delete_zone(self, location_id: UUID, zone_id: UUID) -> None:
        zone = self._get_zone(location_id, zone_id)
        count = self._session.query(ZoneRow).filter(ZoneRow.location_id == str(location_id)).count()
        if count <= 1:
            raise ConfigurationError("Cannot delete the last zone of a location")
        try:
            self._session.query(DeviceRow).filter(DeviceRow.zone_id == zone.id).update(
                {DeviceRow.zone_id: None, DeviceRow.location_id: None},
                synchronize_session=False,
            )
            self._session.delete(zone)
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise