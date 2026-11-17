from __future__ import annotations

from domain.actuators.ports import ActuatorPort
from domain.commands.base import Command


class SetLightLevelCommand(Command):
    """Turns a light on at a level. From idle it moves to running;
    on an already running light it only changes the level (no transition)."""

    command_type = "set_light_level"
    target_state = "running"

    def execute(self, port: ActuatorPort) -> None:
        port.apply(self.device_id, self.command_type, self.payload)