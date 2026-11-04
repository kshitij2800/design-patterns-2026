from __future__ import annotations
from uuid import UUID

from domain.actuators.errors import PolicyBlockedError
from domain.actuators.ports import ActuatorPort
from infrastructure.persistence.execution_log_repository import ExecutionLogRepository


class LoggingActuatorDecorator(ActuatorPort):
    """Outermost decorator: every apply() call writes exactly one actuator_execution_log row."""

    def __init__(self, inner: ActuatorPort, log_repo: ExecutionLogRepository) -> None:
        self._inner = inner
        self._log_repo = log_repo

    def apply(self, device_id: UUID, command: str, payload: dict) -> None:
        try:
            self._inner.apply(device_id, command, payload)
        except PolicyBlockedError as e:
            self._log_repo.insert(
                device_id=device_id,
                success=False,
                policy_applied=[e.policy_name, "logging"],
                message=e.message,
            )
            return   # the block IS the outcome — nothing further to raise
        except Exception as e:
            self._log_repo.insert(
                device_id=device_id, success=False, policy_applied=["logging"], message=str(e)
            )
            raise
        else:
            self._log_repo.insert(
                device_id=device_id, success=True, policy_applied=["logging"], message=None
            )