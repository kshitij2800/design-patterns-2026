from uuid import UUID
from pydantic import BaseModel


class StrategyUpdateDto(BaseModel):
    strategy_key: str


class StrategySavedDto(BaseModel):
    location_id: UUID
    strategy_key: str


class ZoneRecommendationDto(BaseModel):
    zone_id: UUID
    zone_name: str
    action: str
    reason: str
    score: float | None = None


class RecommendationDto(BaseModel):
    location_id: UUID
    strategy_key: str
    action: str
    reason: str
    zones: list[ZoneRecommendationDto]