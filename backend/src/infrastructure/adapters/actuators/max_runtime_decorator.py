from __future__ import annotations
from datetime import datetime, timedelta, timezone
from uuid import UUID

from domain.actuators.errors import PolicyBlockedError
from domain.actuators.ports import ActuatorPort
from infrastructure.persistence.actuator_state_repository import ActuatorStateRepository

MAX_RUN_TIME = timedelta(minutes=30)


class MaxRunTimeActuatorDecorator(ActuatorPort):
    """Rejects apply() when the persisted state is 'running' and has been for 30+ minutes.
    Does NOT call the inner component when it blocks."""

    def __init__(self, inner: ActuatorPort, states: ActuatorStateRepository) -> None:
        self._inner = inner
        self._states = states

    def apply(self, device_id: UUID, command: str, payload: dict) -> None:
        row = self._states.get_row(device_id)
        if row is not None and row.state == "running":
            elapsed = datetime.now(timezone.utc) - row.updated_at
            if elapsed >= MAX_RUN_TIME:
                raise PolicyBlockedError("maxRunTime", "Max run time exceeded")
        self._inner.apply(device_id, command, payload)