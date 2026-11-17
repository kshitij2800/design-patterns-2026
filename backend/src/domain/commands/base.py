from __future__ import annotations
from abc import ABC, abstractmethod
from uuid import UUID

from domain.actuators.ports import ActuatorPort


class Command(ABC):
    """One actuator request as an object: what to do, to which device, with what payload.

    command_type  -- the string clients send ("start_pump", ...); also the registry key
    target_state  -- the state the actuator should be in after a completed apply
                     (None = this command never changes state)
    """

    command_type: str
    target_state: str | None = None

    def __init__(self, device_id: UUID, payload: dict | None = None) -> None:
        self.device_id = device_id
        self.payload = dict(payload or {})

    @abstractmethod
    def execute(self, port: ActuatorPort) -> None:
        ...