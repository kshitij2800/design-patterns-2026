from __future__ import annotations
from abc import ABC, abstractmethod
from domain.devices.entity import Device
from domain.sensors.reading import Reading


class SensorPort(ABC):
    """What the application needs from any sensor, whatever the hardware or vendor."""

    @abstractmethod
    def read(self, device: Device) -> Reading:
        ...