from __future__ import annotations
from domain.sensors.entity import Sensor
from domain.sensors.creators import get_creator
from infrastructure.persistence.device_repository import DeviceRepository


class SensorService:
    def __init__(self, repo: DeviceRepository) -> None:
        self._repo = repo

    def create_sensor(self, sensor_type: str, display_name: str | None = None) -> Sensor:
        creator = get_creator(sensor_type)
        prototype = creator.create_sensor(display_name=display_name)
        return self._repo.save_sensor(prototype)

    def list_sensors(self) -> list[Sensor]:
        return self._repo.list_sensors()