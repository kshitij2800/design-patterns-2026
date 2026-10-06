from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class Reading:
    """Normalized sensor reading — the one shape every adapter must return."""
    device_id: UUID
    value: float
    unit: str          
    source: str          
    recorded_at: datetime  