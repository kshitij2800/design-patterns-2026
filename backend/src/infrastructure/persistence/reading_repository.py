from __future__ import annotations
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased

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

        # ---- Phase 7 ----

    def latest_for_devices(self, device_ids: list[UUID]) -> dict[UUID, Reading]:
        """One query: the newest row per device (any source).

        ROW_NUMBER() numbers each device's rows newest-first (rn = 1 is the newest);
        the outer query keeps only rn = 1. Uses the (device_id, recorded_at DESC) index.
        """
        if not device_ids:
            return {}
        ranked = (
            select(
                ReadingRow,
                func.row_number()
                .over(partition_by=ReadingRow.device_id, order_by=ReadingRow.recorded_at.desc())
                .label("rn"),
            )
            .where(ReadingRow.device_id.in_([str(i) for i in device_ids]))
            .subquery()
        )
        newest = aliased(ReadingRow, ranked)
        rows = self._session.execute(select(newest).where(ranked.c.rn == 1)).scalars().all()
        return {UUID(r.device_id): _row_to_reading(r) for r in rows}