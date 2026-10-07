from __future__ import annotations
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from domain.automation.context import ZoneSnapshot
from infrastructure.persistence.models import (
    AutomationRuleRow,
    DeviceRow,
    LocationRow,
    ReadingRow,
    ZoneRow,
)


class AutomationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def location_exists(self, location_id: UUID) -> bool:
        return self._session.get(LocationRow, str(location_id)) is not None

    def get_strategy_key(self, location_id: UUID) -> str | None:
        row = (
            self._session.query(AutomationRuleRow)
            .filter(AutomationRuleRow.location_id == str(location_id))
            .one_or_none()
        )
        return row.strategy_key if row else None

    def upsert_strategy(self, location_id: UUID, strategy_key: str) -> None:
        stmt = insert(AutomationRuleRow).values(
            location_id=str(location_id),
            strategy_key=strategy_key,
            updated_at=func.now(),
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["location_id"],
            set_={"strategy_key": strategy_key, "updated_at": func.now()},
        )
        self._session.execute(stmt)
        self._session.commit()

    def list_zone_snapshots(self, location_id: UUID) -> list[ZoneSnapshot]:
        """One snapshot per zone: thresholds from `zones`, latest readings from
        sensors whose devices.zone_id is that zone. Never uses unassigned devices."""
        zones = (
            self._session.query(ZoneRow)
            .filter(ZoneRow.location_id == str(location_id))
            .order_by(ZoneRow.name)
            .all()
        )
        return [
            ZoneSnapshot(
                zone_id=UUID(z.id),
                zone_name=z.name,
                low=float(z.moisture_threshold_low),
                high=float(z.moisture_threshold_high),
                moisture=self._latest_value(z.id, "moisture_sensor"),
                light=self._latest_value(z.id, "light_sensor"),
            )
            for z in zones
        ]

    def _latest_value(self, zone_id: str, device_type: str) -> float | None:
        row = (
            self._session.query(ReadingRow.value)
            .join(DeviceRow, DeviceRow.id == ReadingRow.device_id)
            .filter(
                DeviceRow.zone_id == zone_id,
                DeviceRow.role == "sensor",
                DeviceRow.device_type == device_type,
            )
            .order_by(ReadingRow.recorded_at.desc())
            .limit(1)
            .first()
        )
        return float(row[0]) if row else None