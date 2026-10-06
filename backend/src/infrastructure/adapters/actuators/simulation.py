from __future__ import annotations
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from domain.actuators.ports import ActuatorPort

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AppliedCommand:
    device_id: UUID
    command: str
    payload: dict
    applied_at: datetime


class SimulationActuatorAdapter(ActuatorPort):
    """Records intent in memory and logs it. No GPIO, no physical output.
    Phase 9 decorators will wrap this class."""

    def __init__(self) -> None:
        self.applied: list[AppliedCommand] = []

    def apply(self, device_id: UUID, command: str, payload: dict) -> None:
        entry = AppliedCommand(device_id, command, dict(payload), datetime.now(timezone.utc))
        self.applied.append(entry)
        logger.info("SIM actuator %s <- %s %s", device_id, command, payload)