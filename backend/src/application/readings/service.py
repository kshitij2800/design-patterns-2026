from __future__ import annotations
from collections.abc import Callable
from uuid import UUID

from application.readings.dto import ReadingDto
from application.readings.errors import DeviceNotFoundError
from domain.devices.entity import Device
from domain.sensors.ports import SensorPort
from domain.sensors.reading import Reading
from infrastructure.persistence.device_repository import DeviceRepository
from infrastructure.persistence.reading_repository import ReadingRepository
from domain.events.bus import EventBus
from domain.events.events import ReadingCreated 

# Given a device, return the port that can read it. The selector lives in
# infrastructure and is injected, so this service never imports adapter classes.
AdapterSelector = Callable[[Device], SensorPort]


def reading_to_dto(reading: Reading) -> ReadingDto:
    return ReadingDto(
        device_id=reading.device_id,
        value=reading.value,
        unit=reading.unit,
        source=reading.source,
        recorded_at=reading.recorded_at,
    )


class ReadingIngest:
    """The only writer of sensor_readings."""

    def __init__(
        self,
        devices: DeviceRepository,
        readings: ReadingRepository,
        select_adapter: AdapterSelector,
        bus: EventBus,
    ) -> None:
        self._devices = devices
        self._readings = readings
        self._select_adapter = select_adapter
        self._bus = bus

    def _load_device(self, device_id: UUID) -> Device:
        device = self._devices.get_device(device_id)
        if device is None:
            raise DeviceNotFoundError(str(device_id))
        return device

    def take_reading(self, device_id: UUID) -> ReadingDto:
        """One-shot read: load device -> select adapter -> read -> persist -> DTO."""
        device = self._load_device(device_id)
        reading = self._select_adapter(device).read(device)   # may raise SensorReadError
        return self.record(device_id, reading)

    def record(self, device_id: UUID, reading: Reading) -> ReadingDto:
        """Persist an already translated reading, then publish reading.created.

        Every ingest path ends here (POST /read via take_reading, the sampler, MQTT translate),
        so there is one publish rule. Tracking off: the row is stored, nothing is published.
        """
        device = self._load_device(device_id)
        stored = self._readings.insert(reading)
        if device.tracking_enabled:
            self._bus.publish(ReadingCreated.from_reading(device, stored))
        return reading_to_dto(stored)
    
    def list_readings(self, device_id: UUID, limit: int = 20) -> list[ReadingDto]:
        self._load_device(device_id)
        return [reading_to_dto(r) for r in self._readings.list_for_device(device_id, limit)]