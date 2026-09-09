from __future__ import annotations
from dataclasses import dataclass, field
from uuid import UUID


@dataclass
class Sensor:
    device_type: str
    display_name: str
    default_config: dict = field(default_factory=dict)
    id: UUID | None = None