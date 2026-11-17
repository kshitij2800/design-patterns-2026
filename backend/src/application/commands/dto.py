from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class CommandRequestDto(BaseModel):
    command_type: str
    device_id: UUID
    payload: dict = Field(default_factory=dict)


class CommandLogDto(BaseModel):
    id: UUID
    command_type: str
    device_id: UUID
    payload: dict
    status: Literal["success", "failed", "rejected"]
    error_message: str | None
    created_at: datetime