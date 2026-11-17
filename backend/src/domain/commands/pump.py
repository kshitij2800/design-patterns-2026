from __future__ import annotations

from domain.actuators.ports import ActuatorPort
from domain.commands.base import Command


class StartPumpCommand(Command):
    command_type = "start_pump"
    target_state = "running"

    def execute(self, port: ActuatorPort) -> None:
        port.apply(self.device_id, self.command_type, self.payload)


class StopPumpCommand(Command):
    command_type = "stop_pump"
    target_state = "idle"

    def execute(self, port: ActuatorPort) -> None:
        port.apply(self.device_id, self.command_type, self.payload)