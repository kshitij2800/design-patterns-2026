from __future__ import annotations
from uuid import UUID

from sqlalchemy.orm import Session

from infrastructure.persistence.models import DeviceRow, ZoneRow


class DeviceNotFoundError(Exception):
    pass


class ZoneNotFoundError(Exception):
    pass


class ZoneAssignmentService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def assign(self, device_id: UUID, zone_id: UUID | None) -> None:
        device = self._session.get(DeviceRow, str(device_id))
        if device is None:
            raise DeviceNotFoundError(str(device_id))

        if zone_id is None:
            device.zone_id = None
            device.location_id = None
        else:
            zone = self._session.get(ZoneRow, str(zone_id))
            if zone is None:
                raise ZoneNotFoundError(str(zone_id))
            device.zone_id = str(zone_id)
            device.location_id = zone.location_id

        self._session.commit()

    def list_devices_in_zone(self, location_id: UUID, zone_id: UUID) -> list[DeviceRow]:
        zone = self._session.get(ZoneRow, str(zone_id))
        if zone is None or zone.location_id != str(location_id):
            raise ZoneNotFoundError(str(zone_id))

        return (
            self._session.query(DeviceRow)
            .filter(DeviceRow.zone_id == str(zone_id))
            .all()
        )