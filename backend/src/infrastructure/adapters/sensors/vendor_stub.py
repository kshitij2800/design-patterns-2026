from __future__ import annotations
import random
from datetime import datetime, timezone

from domain.devices.entity import Device
from domain.sensors.errors import SensorReadError
from domain.sensors.ports import SensorPort
from domain.sensors.reading import Reading


class FakeAcmeClient:
    """Pretend vendor SDK. Its payload shape is deliberately NOT our Reading shape:

        {"channel": "SOIL", "reading_x100": 4100, "uom": "PCT_VWC", "epoch_ms": 1759...}

    - values are integers scaled by 100
    - moisture comes as a percentage (41.00 %), not a 0–1 fraction
    - time is epoch milliseconds, not a datetime
    """

    _CHANNELS = {"moisture_sensor": ("SOIL", "PCT_VWC", 20.0, 60.0),
                 "light_sensor": ("LIGHT", "LUX", 200.0, 2000.0)}

    def fetch(self, device_type: str) -> dict:
        channel, uom, low, high = self._CHANNELS[device_type]
        return {
            "channel": channel,
            "reading_x100": int(random.uniform(low, high) * 100),
            "uom": uom,
            "epoch_ms": int(datetime.now(timezone.utc).timestamp() * 1000),
        }


class VendorStubSensorAdapter(SensorPort):
    """Adapter: translates the vendor's raw payload into our normalized Reading."""

    def __init__(self, client: FakeAcmeClient | None = None) -> None:
        self._client = client or FakeAcmeClient()

    def read(self, device: Device) -> Reading:
        if device.device_type not in FakeAcmeClient._CHANNELS:
            raise SensorReadError(f"Vendor stub does not support '{device.device_type}'")
        raw = self._client.fetch(device.device_type)
        return self.translate(device, raw)

    def translate(self, device: Device, raw: dict) -> Reading:
        try:
            scaled = raw["reading_x100"] / 100
            uom = raw["uom"]
            recorded_at = datetime.fromtimestamp(raw["epoch_ms"] / 1000, tz=timezone.utc)
        except (KeyError, TypeError) as e:
            raise SensorReadError(f"Malformed vendor payload: {e}") from e

        if uom == "PCT_VWC":
            value, unit = round(scaled / 100, 4), "vwc"     # 41.00 % -> 0.41
        elif uom == "LUX":
            value, unit = scaled, "lux"
        else:
            raise SensorReadError(f"Unknown vendor unit '{uom}'")

        return Reading(
            device_id=device.id,
            value=value,
            unit=unit,
            source="vendor",
            recorded_at=recorded_at,
        )