from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class Device:
    id: UUID | None
    device_type: str
    role: str          
    device_family: str  
    display_name: str
    default_config: dict
    zone_id: UUID | None = None
    location_id: UUID | None = None