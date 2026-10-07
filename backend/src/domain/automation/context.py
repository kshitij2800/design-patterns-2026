from __future__ import annotations
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class LocationAutomationContext:
    """Everything a strategy may look at for ONE zone. Plain values, no ORM rows."""
    location_id: UUID
    zone_id: UUID
    moisture: float            # latest moisture reading among sensors in this zone
    low: float                 # zone threshold
    high: float                # zone threshold
    light: float | None = None


@dataclass(frozen=True)
class ZoneSnapshot:
    """What the repository hands the service for one zone (moisture may be missing)."""
    zone_id: UUID
    zone_name: str
    low: float
    high: float
    moisture: float | None
    light: float | None = None