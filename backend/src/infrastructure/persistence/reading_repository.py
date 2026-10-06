from __future__ import annotations
from uuid import UUID

from sqlalchemy.orm import Session

from domain.sensors.reading import Reading
from infrastructure.persistence.models import ReadingRow


def _row_to_reading(row: ReadingRow) -> Reading:
    return Reading(
        device_id=UUID(row.device_id),
        value=float(row.value),          # NUMERIC comes back as Decimal
        unit=row.unit,
        source=row.source,
        recorded_at=row.recorded_at,
    )


class ReadingRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def insert(self, reading: Reading) -> Reading:
        row = ReadingRow(
            device_id=str(reading.device_id),
            value=reading.value,
            unit=reading.unit,
            source=reading.source,
            recorded_at=reading.recorded_at,
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return _row_to_reading(row)

    def list_for_device(self, device_id: UUID, limit: int = 20) -> list[Reading]:
        rows = (
            self._session.query(ReadingRow)
            .filter(ReadingRow.device_id == str(device_id))
            .order_by(ReadingRow.recorded_at.desc())
            .limit(limit)
            .all()
        )
        return [_row_to_reading(r) for r in rows]

    def latest_for_device(self, device_id: UUID) -> Reading | None:
        rows = self.list_for_device(device_id, limit=1)
        return rows[0] if rows else None