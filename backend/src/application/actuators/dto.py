from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class ExecutionDto(BaseModel):
    id: UUID
    device_id: UUID
    success: bool
    policy_applied: list[str]
    message: str | None
    created_at: datetime


class ApplyCommandDto(BaseModel):
    command: str
    payload: dict = {}