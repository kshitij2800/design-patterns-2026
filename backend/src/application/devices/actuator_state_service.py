from __future__ import annotations
from uuid import UUID

from application.readings.errors import DeviceNotFoundError
from domain.actuators.context import ActuatorContext
from domain.devices.entity import Device
from domain.events.bus import EventBus
from domain.events.events import ActuatorStateChanged
from infrastructure.persistence.actuator_state_repository import ActuatorStateRepository
from infrastructure.persistence.device_repository import DeviceRepository


class ActuatorStateService:
    """Loads an actuator's current state, validates+applies a transition, saves it,
    then publishes ActuatorStateChanged (Phase 11)."""

    def __init__(
        self, devices: DeviceRepository, states: ActuatorStateRepository, bus: EventBus
    ) -> None:
        self._devices = devices
        self._states = states
        self._bus = bus

    def _require_actuator(self, device_id: UUID) -> Device:
        device = self._devices.get_device(device_id)
        if device is None or device.role != "actuator":
            raise DeviceNotFoundError(str(device_id))
        return device

    def transition(self, device_id: UUID, target: str) -> str:
        device = self._require_actuator(device_id)
        current = self._states.get_state(device_id) or "idle"
        ctx = ActuatorContext(state=current)
        ctx.transition(target)              # raises IllegalTransitionError; nothing persisted on failure
        self._states.save_state(device_id, ctx.state)
        self._bus.publish(ActuatorStateChanged.for_device(device, ctx.state))
        return ctx.state