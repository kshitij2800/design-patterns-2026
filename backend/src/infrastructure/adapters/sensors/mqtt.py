from __future__ import annotations
from datetime import datetime, timezone

from domain.devices.entity import Device
from domain.sensors.errors import SensorReadError
from domain.sensors.reading import Reading


class MqttSensorAdapter:
    """Translates an inbound payload such as {"value": 0.41, "unit": "vwc"} into a Reading.

    No broker in this phase: Phase 12 delivers the payload (device HTTP or optional broker).
    """

    def translate(self, device: Device, payload: dict) -> Reading:
        value = payload.get("value")
        unit = payload.get("unit")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise SensorReadError("MQTT payload 'value' must be a number")
        if not isinstance(unit, str) or not unit:
            raise SensorReadError("MQTT payload 'unit' must be a non-empty string")
        return Reading(
            device_id=device.id,
            value=float(value),
            unit=unit,
            source="mqtt",
            recorded_at=datetime.now(timezone.utc),
        )