from dataclasses import dataclass, field
from uuid import UUID


@dataclass(frozen=True)
class Zone:
    name: str
    moisture_threshold_low: float
    moisture_threshold_high: float
    schedule: dict = field(default_factory=dict)
    id: UUID | None = None


@dataclass(frozen=True)
class Location:
    name: str
    zones: tuple[Zone, ...]
    id: UUID | None = None


@dataclass(frozen=True)
class LocationConfig:
    location: Location