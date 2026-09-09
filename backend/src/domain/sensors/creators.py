from __future__ import annotations
from abc import ABC, abstractmethod
from domain.sensors.entity import Sensor


class SensorCreator(ABC):
    @abstractmethod
    def create_sensor(self, display_name: str | None = None) -> Sensor:
        ...


class MoistureSensorCreator(SensorCreator):
    def create_sensor(self, display_name: str | None = None) -> Sensor:
        return Sensor(
            device_type="moisture_sensor",
            display_name=display_name or "Moisture Sensor",
            default_config={
                "unit": "vwc",
                "sampling_interval_seconds": 300,
                "moisture_threshold_percent": 40,
            },
        )


class LightSensorCreator(SensorCreator):
    def create_sensor(self, display_name: str | None = None) -> Sensor:
        return Sensor(
            device_type="light_sensor",
            display_name=display_name or "Light Sensor",
            default_config={
                "unit": "lux",
                "sampling_interval_seconds": 60,
                "low_light_threshold_lux": 500,
            },
        )


_REGISTRY: dict[str, SensorCreator] = {
    "moisture": MoistureSensorCreator(),
    "light": LightSensorCreator(),
}


def get_creator(sensor_type: str) -> SensorCreator:
    creator = _REGISTRY.get(sensor_type)
    if creator is None:
        raise ValueError(f"Unknown sensor type: '{sensor_type}'. Valid types: {list(_REGISTRY)}")
    return creator