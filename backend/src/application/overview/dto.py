from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from application.locations.dto import LocationSummaryDto


class DeviceCountsDto(BaseModel):
    """Assigned devices only (this location_id and a non-null zone_id)."""
    sensor: int
    actuator: int


class OverviewDeviceDto(BaseModel):
    id: UUID
    device_type: str
    role: str
    display_name: str


class OverviewReadingDto(BaseModel):
    """Newest sensor_readings row for one device. The last two fields come from the device."""
    device_id: UUID
    value: float
    unit: str
    recorded_at: datetime
    tracking_enabled: bool
    sampling_interval_seconds: int


class OverviewZoneDto(BaseModel):
    id: UUID
    name: str
    moisture_threshold_low: float
    moisture_threshold_high: float
    devices: list[OverviewDeviceDto]
    latest_readings: list[OverviewReadingDto]


class OverviewRecommendationDto(BaseModel):
    action: str
    reason: str


class LocationOverviewDto(BaseModel):
    location: LocationSummaryDto
    device_counts: DeviceCountsDto
    zones: list[OverviewZoneDto]
    strategy_key: str | None
    last_recommendation: OverviewRecommendationDto | None