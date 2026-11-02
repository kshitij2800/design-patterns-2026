from __future__ import annotations
from dataclasses import dataclass

from domain.actuators.state import allowed_commands_for, validate_transition


@dataclass
class ActuatorContext:
    """Holds one actuator's current state and guards transitions."""
    state: str

    def transition(self, target: str) -> None:
        validate_transition(self.state, target)
        self.state = target

    def allowed_commands(self) -> list[str]:
        return allowed_commands_for(self.state)