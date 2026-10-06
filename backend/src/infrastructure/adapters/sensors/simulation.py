from __future__ import annotations
import random
from collections.abc import Callable
from datetime import datetime, timezone

from domain.devices.entity import Device
from domain.sensors.errors import SensorReadError
from domain.sensors.ports import SensorPort
from domain.sensors.reading import Reading

# Documented value ranges for generated readings: device_type -> (low, high, unit)
SIMULATION_RANGES: dict[str, tuple[float, float, str]] = {
    "moisture_sensor": (0.2, 0.6, "vwc"),
    "light_sensor": (200.0, 2000.0, "lux"),
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SimulationSensorAdapter(SensorPort):
    """Generates a plausible value in code — no hardware needed."""

    def __init__(
        self,
        rng: random.Random | None = None,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._rng = rng or random.Random()
        self._clock = clock

    def read(self, device: Device) -> Reading:
        spec = SIMULATION_RANGES.get(device.device_type)
        if spec is None:
            raise SensorReadError(f"No simulation range for device type '{device.device_type}'")
        low, high, unit = spec
        value = round(self._rng.uniform(low, high), 4)
        return Reading(
            device_id=device.id,
            value=value,
            unit=unit,
            source="simulation",
            recorded_at=self._clock(),
        )