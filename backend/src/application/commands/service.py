from __future__ import annotations

from application.commands.dto import CommandLogDto, CommandRequestDto
from application.readings.errors import DeviceNotFoundError
from domain.actuators.context import ActuatorContext
from domain.actuators.errors import PolicyBlockedError
from domain.actuators.ports import ActuatorPort
from domain.commands.invoker import CommandInvoker, command_for
from infrastructure.persistence.actuator_state_repository import ActuatorStateRepository
from infrastructure.persistence.command_log_repository import CommandLogRepository
from infrastructure.persistence.device_repository import DeviceRepository
from domain.events.bus import EventBus
from domain.events.events import ActuatorStateChanged, CommandFailed 


class CommandRejectedError(Exception):
    """Not allowed in the current state. Carries the 'rejected' row for the 409 response."""

    def __init__(self, log_row: CommandLogDto) -> None:
        super().__init__(log_row.error_message)
        self.log_row = log_row


class CommandService:
    """One POST /api/commands: guard -> decorated port -> state update -> command_log."""

    def __init__(
        self,
        devices: DeviceRepository,
        states: ActuatorStateRepository,
        command_log: CommandLogRepository,
        port: ActuatorPort,              # the Phase 9 decorator stack
        bus: EventBus,                    # for publishing ActuatorStateChanged and CommandFailed
        invoker: CommandInvoker | None = None,
    ) -> None:
        self._devices = devices
        self._states = states
        self._log = command_log
        self._port = port
        self._bus = bus 
        self._invoker = invoker or CommandInvoker()

    def execute(self, req: CommandRequestDto) -> CommandLogDto:
        # 1. Missing device or not an actuator -> not found
        device = self._devices.get_device(req.device_id)
        if device is None or device.role != "actuator":
            raise DeviceNotFoundError(str(req.device_id))

        # 2. Unknown type -> UnknownCommandError, no command_log row
        command = command_for(req.command_type, req.device_id, req.payload)

        # 3. State guard: rejected row, no apply, no state write
        ctx = ActuatorContext(state=self._states.get_state(req.device_id) or "idle")
        if command.command_type not in ctx.allowed_commands():
            row = self._log_row(command, "rejected",
                                f"'{command.command_type}' is not allowed in state '{ctx.state}'")
            raise CommandRejectedError(row)


        # 4. Execute through the decorated port; a policy block is a 'failed' attempt
        try:
            self._invoker.run(command, self._port)
        except PolicyBlockedError as e:
            row = self._log_row(command, "failed", e.message)   # actuator_states untouched
            self._bus.publish(CommandFailed.for_device(device, command.command_type, e.message))
            return row

        # 5. Transition only when the target differs (light already running -> no transition)
        if command.target_state is not None and command.target_state != ctx.state:
            ctx.transition(command.target_state)
            self._states.save_state(req.device_id, ctx.state)
            self._bus.publish(ActuatorStateChanged.for_device(device, ctx.state))
        return self._log_row(command, "success")
    
    def list_history(self, limit: int = 50) -> list[CommandLogDto]:
        return self._log.list_recent(limit)

    def _log_row(self, command, status: str, error_message: str | None = None) -> CommandLogDto:
        return self._log.insert(
            command_type=command.command_type,
            device_id=command.device_id,
            payload=command.payload,
            status=status,
            error_message=error_message,
        )