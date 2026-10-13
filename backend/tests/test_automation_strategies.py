from uuid import uuid4

import pytest

from domain.automation.context import LocationAutomationContext
from domain.automation.strategy import (
    AggressiveMoistureStrategy,
    ConservativeMoistureStrategy,
    UnknownStrategyError,
    get_strategy,
)


def ctx(moisture: float, low: float = 0.25, high: float = 0.45) -> LocationAutomationContext:
    return LocationAutomationContext(
        location_id=uuid4(), zone_id=uuid4(), moisture=moisture, low=low, high=high
    )


def test_conservative_waits_when_within_band():
    rec = ConservativeMoistureStrategy().decide(ctx(0.40))
    assert rec.action == "wait"


def test_conservative_irrigates_below_low():
    rec = ConservativeMoistureStrategy().decide(ctx(0.20))
    assert rec.action == "irrigate"
    assert rec.score == pytest.approx(0.05)


def test_aggressive_differs_on_same_context():
    context = ctx(0.30)   # inside the band, but below the 0.35 midpoint
    assert ConservativeMoistureStrategy().decide(context).action == "wait"
    assert AggressiveMoistureStrategy().decide(context).action == "irrigate"


def test_unknown_strategy_key_rejected():
    with pytest.raises(UnknownStrategyError):
        get_strategy("yolo")