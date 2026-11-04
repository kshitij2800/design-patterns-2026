from __future__ import annotations
from uuid import UUID
from datetime import datetime, timezone 
from sqlalchemy.orm import Session

from infrastructure.persistence.models import ActuatorStateRow


class ActuatorStateRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_state(self, device_id: UUID) -> str | None:
        row = self._session.get(ActuatorStateRow, str(device_id))
        return row.state if row else None

    def get_states(self, device_ids: list[UUID]) -> dict[UUID, str]:
        if not device_ids:
            return {}
        rows = (
            self._session.query(ActuatorStateRow)
            .filter(ActuatorStateRow.device_id.in_([str(i) for i in device_ids]))
            .all()
        )
        return {UUID(r.device_id): r.state for r in rows}

    def save_state(self, device_id: UUID, state: str) -> None:
        row = self._session.get(ActuatorStateRow, str(device_id))
        if row is None:
            row = ActuatorStateRow(device_id=str(device_id), state=state)
            self._session.add(row)
        else:
            row.state = state
            row.updated_at = datetime.now(timezone.utc)
        self._session.commit()