from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ZoneRequestDto(BaseModel):
    name: str
    moisture_threshold_low: float = Field(ge=0.0, le=1.0)
    moisture_threshold_high: float = Field(ge=0.0, le=1.0)
    schedule: dict = Field(default_factory=dict)

class ZoneAssignmentRequestDto(BaseModel):
    zone_id: UUID | None

class LocationConfigRequestDto(BaseModel):
    location_name: str
    zones: list[ZoneRequestDto]


class ZoneReadDto(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    location_id: UUID
    name: str
    moisture_threshold_low: float
    moisture_threshold_high: float
    schedule: dict


class LocationSummaryDto(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str


class LocationConfigReadDto(BaseModel):
    location: LocationSummaryDto
    zones: list[ZoneReadDto]