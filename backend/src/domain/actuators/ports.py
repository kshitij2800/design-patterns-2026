from __future__ import annotations
from abc import ABC, abstractmethod
from uuid import UUID


class ActuatorPort(ABC):
    """What the application needs from any actuator (pump, light...)."""

    @abstractmethod
    def apply(self, device_id: UUID, command: str, payload: dict) -> None:
        ...