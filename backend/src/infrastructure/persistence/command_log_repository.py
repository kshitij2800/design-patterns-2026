from __future__ import annotations
from uuid import UUID

from sqlalchemy.orm import Session

from application.commands.dto import CommandLogDto
from infrastructure.persistence.models import CommandLogRow


def _row_to_dto(row: CommandLogRow) -> CommandLogDto:
    return CommandLogDto(
        id=UUID(row.id),
        command_type=row.command_type,
        device_id=UUID(row.device_id),
        payload=row.payload,
        status=row.status,
        error_message=row.error_message,
        created_at=row.created_at,
    )


class CommandLogRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def insert(
        self,
        command_type: str,
        device_id: UUID,
        payload: dict,
        status: str,
        error_message: str | None = None,
    ) -> CommandLogDto:
        row = CommandLogRow(
            command_type=command_type,
            device_id=str(device_id),
            payload=payload,
            status=status,
            error_message=error_message,
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return _row_to_dto(row)

    def list_recent(self, limit: int = 50) -> list[CommandLogDto]:
        rows = (
            self._session.query(CommandLogRow)
            .order_by(CommandLogRow.created_at.desc())
            .limit(limit)
            .all()
        )
        return [_row_to_dto(r) for r in rows]