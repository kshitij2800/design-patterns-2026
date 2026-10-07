from __future__ import annotations
from uuid import UUID

from application.automation.dto import (
    RecommendationDto,
    StrategySavedDto,
    ZoneRecommendationDto,
)
from application.automation.errors import LocationNotFoundError
from domain.automation.context import LocationAutomationContext
from domain.automation.strategy import Recommendation, get_strategy
from infrastructure.persistence.automation_repository import AutomationRepository

DEFAULT_STRATEGY_KEY = "conservative"   # used when a location has no saved strategy yet
NO_MOISTURE_REASON = (
    "no moisture reading for this zone (no moisture sensor assigned, or it has not reported yet)"
)


class AutomationService:
    def __init__(self, repo: AutomationRepository) -> None:
        self._repo = repo

    def set_strategy(self, location_id: UUID, strategy_key: str) -> StrategySavedDto:
        get_strategy(strategy_key)                    # unknown key -> UnknownStrategyError (400)
        if not self._repo.location_exists(location_id):
            raise LocationNotFoundError(str(location_id))
        self._repo.upsert_strategy(location_id, strategy_key)
        return StrategySavedDto(location_id=location_id, strategy_key=strategy_key)

    def evaluate(self, location_id: UUID) -> RecommendationDto:
        if not self._repo.location_exists(location_id):
            raise LocationNotFoundError(str(location_id))

        key = self._repo.get_strategy_key(location_id) or DEFAULT_STRATEGY_KEY
        strategy = get_strategy(key)                  # persisted key, validated before decide()

        zones: list[ZoneRecommendationDto] = []
        for snap in self._repo.list_zone_snapshots(location_id):
            if snap.moisture is None:
                rec = Recommendation("wait", NO_MOISTURE_REASON)
            else:
                context = LocationAutomationContext(
                    location_id=location_id,
                    zone_id=snap.zone_id,
                    moisture=snap.moisture,
                    low=snap.low,
                    high=snap.high,
                    light=snap.light,
                )
                rec = strategy.decide(context)
            zones.append(
                ZoneRecommendationDto(
                    zone_id=snap.zone_id,
                    zone_name=snap.zone_name,
                    action=rec.action,
                    reason=rec.reason,
                    score=rec.score,
                )
            )

        irrigate = [z for z in zones if z.action == "irrigate"]
        if not zones:
            action, reason = "wait", "no zones in this location"
        elif irrigate:
            action, reason = "irrigate", f"{len(irrigate)} of {len(zones)} zone(s) need irrigation"
        else:
            action, reason = "wait", f"all {len(zones)} zone(s) can wait"

        return RecommendationDto(
            location_id=location_id,
            strategy_key=key,
            action=action,
            reason=reason,
            zones=zones,
        )