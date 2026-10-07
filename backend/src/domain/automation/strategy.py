from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass

from domain.automation.context import LocationAutomationContext


@dataclass(frozen=True)
class Recommendation:
    action: str                  # "irrigate" | "wait"
    reason: str
    score: float | None = None   # how far below the trigger level the moisture is


class UnknownStrategyError(ValueError):
    pass


class AutomationStrategy(ABC):
    key: str

    @abstractmethod
    def decide(self, context: LocationAutomationContext) -> Recommendation:
        ...


class ConservativeMoistureStrategy(AutomationStrategy):
    """Irrigates only when moisture drops below the zone's LOW threshold."""
    key = "conservative"

    def decide(self, context: LocationAutomationContext) -> Recommendation:
        m, low, high = context.moisture, context.low, context.high
        if m < low:
            return Recommendation(
                "irrigate",
                f"Moisture {m:.2f} is below the low threshold {low:.2f}",
                round(low - m, 4),
            )
        return Recommendation(
            "wait",
            f"Moisture {m:.2f} is not below the low threshold {low:.2f} (band {low:.2f}–{high:.2f})",
        )


class AggressiveMoistureStrategy(AutomationStrategy):
    """Acts sooner: irrigates once moisture falls below the MIDDLE of the band."""
    key = "aggressive"

    def decide(self, context: LocationAutomationContext) -> Recommendation:
        m = context.moisture
        trigger = (context.low + context.high) / 2
        if m < trigger:
            return Recommendation(
                "irrigate",
                f"Moisture {m:.2f} is below the mid-band trigger {trigger:.2f}",
                round(trigger - m, 4),
            )
        return Recommendation(
            "wait",
            f"Moisture {m:.2f} has not fallen below the mid-band trigger {trigger:.2f}",
        )


_STRATEGIES: dict[str, AutomationStrategy] = {
    s.key: s for s in (ConservativeMoistureStrategy(), AggressiveMoistureStrategy())
}


def known_strategy_keys() -> list[str]:
    return sorted(_STRATEGIES)


def get_strategy(key: str) -> AutomationStrategy:
    """The only lookup. Unknown keys fail here, before decide() is ever called."""
    try:
        return _STRATEGIES[key]
    except KeyError:
        raise UnknownStrategyError(
            f"Unknown strategy '{key}'. Known keys: {', '.join(known_strategy_keys())}"
        ) from None