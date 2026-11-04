from __future__ import annotations
from uuid import UUID
from sqlalchemy.orm import Session

from application.actuators.dto import ExecutionDto
from infrastructure.persistence.models import ActuatorExecutionLogRow


def _row_to_dto(row: ActuatorExecutionLogRow) -> ExecutionDto:
    return ExecutionDto(
        id=UUID(row.id),
        device_id=UUID(row.device_id),
        success=row.success,
        policy_applied=row.policy_applied,
        message=row.message,
        created_at=row.created_at,
    )


class ExecutionLogRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def insert(
        self, device_id: UUID, success: bool, policy_applied: list[str], message: str | None
    ) -> ExecutionDto:
        row = ActuatorExecutionLogRow(
            device_id=str(device_id), success=success, policy_applied=policy_applied, message=message
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return _row_to_dto(row)

    def list_recent(self, limit: int = 20) -> list[ExecutionDto]:
        rows = (
            self._session.query(ActuatorExecutionLogRow)
            .order_by(ActuatorExecutionLogRow.created_at.desc())
            .limit(limit)
            .all()
        )
        return [_row_to_dto(r) for r in rows]