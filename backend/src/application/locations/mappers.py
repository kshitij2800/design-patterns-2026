from uuid import UUID

from application.locations.dto import LocationConfigReadDto, LocationSummaryDto, ZoneReadDto
from infrastructure.persistence.models import LocationRow, ZoneRow
from application.devices.dto import DeviceDto
from infrastructure.persistence.models import DeviceRow

def zone_row_to_dto(row: ZoneRow) -> ZoneReadDto:
    return ZoneReadDto(
        id=UUID(row.id),
        location_id=UUID(row.location_id),
        name=row.name,
        moisture_threshold_low=float(row.moisture_threshold_low),
        moisture_threshold_high=float(row.moisture_threshold_high),
        schedule=row.schedule,
    )


def config_to_dto(location_row: LocationRow, zone_rows: list[ZoneRow]) -> LocationConfigReadDto:
    return LocationConfigReadDto(
        location=LocationSummaryDto(id=UUID(location_row.id), name=location_row.name),
        zones=[zone_row_to_dto(z) for z in zone_rows],
    )

def device_row_to_dto(row: DeviceRow) -> DeviceDto:
    from uuid import UUID
    return DeviceDto(
        id=UUID(row.id),
        device_type=row.device_type,
        role=row.role,
        device_family=row.device_family,
        display_name=row.display_name or "",
        default_config=row.default_config,
        zone_id=UUID(row.zone_id) if row.zone_id else None,
        location_id=UUID(row.location_id) if row.location_id else None,
    )