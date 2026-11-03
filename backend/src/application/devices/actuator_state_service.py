from __future__ import annotations
from uuid import UUID

from application.readings.errors import DeviceNotFoundError
from domain.actuators.context import ActuatorContext
from infrastructure.persistence.actuator_state_repository import ActuatorStateRepository
from infrastructure.persistence.device_repository import DeviceRepository


class ActuatorStateService:
    """Loads an actuator's current state, validates+applies a transition, saves it."""

    def __init__(self, devices: DeviceRepository, states: ActuatorStateRepository) -> None:
        self._devices = devices
        self._states = states

    def _require_actuator(self, device_id: UUID) -> None:
        device = self._devices.get_device(device_id)
        if device is None or device.role != "actuator":
            raise DeviceNotFoundError(str(device_id))

    def transition(self, device_id: UUID, target: str) -> str:
        self._require_actuator(device_id)
        current = self._states.get_state(device_id) or "idle"
        ctx = ActuatorContext(state=current)
        ctx.transition(target)              # raises IllegalTransitionError; nothing persisted on failure
        self._states.save_state(device_id, ctx.state)
        return ctx.state