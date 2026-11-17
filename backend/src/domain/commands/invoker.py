from __future__ import annotations
from uuid import UUID

from domain.actuators.ports import ActuatorPort
from domain.commands.base import Command
from domain.commands.light import SetLightLevelCommand
from domain.commands.pump import StartPumpCommand, StopPumpCommand


class UnknownCommandError(ValueError):
    pass


# Registry: command_type string -> command class. A new command = one class + one line here.
COMMAND_REGISTRY: dict[str, type[Command]] = {
    cls.command_type: cls
    for cls in (StartPumpCommand, StopPumpCommand, SetLightLevelCommand)
}


def command_for(command_type: str, device_id: UUID, payload: dict | None = None) -> Command:
    cls = COMMAND_REGISTRY.get(command_type)
    if cls is None:
        raise UnknownCommandError(f"Unknown command_type '{command_type}'")
    return cls(device_id, payload)


class CommandInvoker:
    """Runs any Command against a port. It never looks at command_type."""

    def run(self, command: Command, port: ActuatorPort) -> None:
        command.execute(port)