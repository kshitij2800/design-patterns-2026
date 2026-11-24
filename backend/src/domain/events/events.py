"""Domain events: plain facts about something that already happened. No FastAPI/SQLAlchemy."""
from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar
from uuid import UUID

from domain.devices.entity import Device
from domain.sensors.reading import Reading


@dataclass(frozen=True)
class ReadingCreated:
    event_type: ClassVar[str] = "reading.created"
    device_id: UUID | None
    location_id: UUID | None
    zone_id: UUID | None
    value: float
    unit: str
    source: str
    recorded_at: datetime

    @classmethod
    def from_reading(cls, device: Device, reading: Reading) -> "ReadingCreated":
        # location_id / zone_id are copied from the device (both None when unassigned)
        return cls(
            device_id=device.id,
            location_id=device.location_id,
            zone_id=device.zone_id,
            value=reading.value,
            unit=reading.unit,
            source=reading.source,
            recorded_at=reading.recorded_at,
        )


@dataclass(frozen=True)
class ThresholdCrossed:
    event_type: ClassVar[str] = "threshold.crossed"
    device_id: UUID | None
    location_id: UUID | None
    zone_id: UUID | None
    moisture: float
    threshold_low: float


@dataclass(frozen=True)
class CommandFailed:
    event_type: ClassVar[str] = "command.failed"
    device_id: UUID | None
    location_id: UUID | None
    zone_id: UUID | None
    command_type: str
    message: str

    @classmethod
    def for_device(cls, device: Device, command_type: str, message: str) -> "CommandFailed":
        return cls(device.id, device.location_id, device.zone_id, command_type, message)


@dataclass(frozen=True)
class ActuatorStateChanged:
    event_type: ClassVar[str] = "state.changed"
    device_id: UUID | None
    location_id: UUID | None
    zone_id: UUID | None
    state: str

    @classmethod
    def for_device(cls, device: Device, state: str) -> "ActuatorStateChanged":
        return cls(device.id, device.location_id, device.zone_id, state)