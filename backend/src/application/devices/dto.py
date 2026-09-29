from pydantic import BaseModel
from uuid import UUID


class DeviceDto(BaseModel):
    id: UUID
    device_type: str
    role: str
    device_family: str
    display_name: str
    default_config: dict
    zone_id: UUID | None = None
    location_id: UUID | None = None