from pydantic import BaseModel
from uuid import UUID


class DeviceDto(BaseModel):
    id: UUID
    device_type: str
    role: str
    device_family: str
    display_name: str
    default_config: dict
    state: str | None = None
    allowed_commands: list[str] = []
    zone_id: UUID | None = None
    location_id: UUID | None = None

class StateTransitionRequestDto(BaseModel):
    target: str

class ActuatorStateDto(BaseModel):
    device_id: UUID
    state: str
    allowed_commands: list[str]