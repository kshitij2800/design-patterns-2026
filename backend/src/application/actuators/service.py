from __future__ import annotations
from uuid import UUID

from application.actuators.dto import ExecutionDto
from domain.actuators.ports import ActuatorPort
from infrastructure.persistence.execution_log_repository import ExecutionLogRepository


class ActuatorCommandService:
    """Thin wrapper the API calls. All policy logic lives in the decorator chain, not here."""

    def __init__(self, decorated_port: ActuatorPort, log_repo: ExecutionLogRepository) -> None:
        self._port = decorated_port
        self._log_repo = log_repo

    def apply(self, device_id: UUID, command: str, payload: dict) -> None:
        self._port.apply(device_id, command, payload)

    def list_recent(self, limit: int = 20) -> list[ExecutionDto]:
        return self._log_repo.list_recent(limit)