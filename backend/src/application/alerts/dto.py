from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

# Allowed values for GET /api/alerts?status=  (anything else -> 400)
ALERT_STATUS_FILTERS = ("active", "resolved", "all")


class AlertDto(BaseModel):
    id: UUID
    location_id: UUID | None
    zone_id: UUID | None
    device_id: UUID | None
    severity: Literal["info", "warning", "critical"]
    message: str
    event_type: str
    status: Literal["active", "resolved"]
    created_at: datetime
    # acknowledged_at is stored but deliberately not part of this response