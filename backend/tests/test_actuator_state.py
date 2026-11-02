"""Domain-only state machine tests: no database, no HTTP."""
import pytest

from domain.actuators.context import ActuatorContext
from domain.actuators.state import IllegalTransitionError


def test_idle_to_running_allowed():
    ctx = ActuatorContext(state="idle")
    ctx.transition("running")
    assert ctx.state == "running"


def test_running_to_idle_allowed():
    ctx = ActuatorContext(state="running")
    ctx.transition("idle")
    assert ctx.state == "idle"


def test_any_state_to_error_allowed():
    for state in ["off", "idle", "running", "maintenance"]:
        ctx = ActuatorContext(state=state)
        ctx.transition("error")
        assert ctx.state == "error"


def test_error_to_idle_allowed():
    ctx = ActuatorContext(state="error")
    ctx.transition("idle")
    assert ctx.state == "idle"


def test_running_to_maintenance_rejected():
    ctx = ActuatorContext(state="running")
    with pytest.raises(IllegalTransitionError):
        ctx.transition("maintenance")
    assert ctx.state == "running"  # unchanged


def test_off_to_running_rejected():
    ctx = ActuatorContext(state="off")
    with pytest.raises(IllegalTransitionError):
        ctx.transition("running")
    assert ctx.state == "off"


def test_allowed_commands_match_state():
    assert ActuatorContext(state="idle").allowed_commands() == [
        "start_pump", "enter_maintenance", "power_off"
    ]
    assert ActuatorContext(state="running").allowed_commands() == ["stop_pump"]
    assert ActuatorContext(state="error").allowed_commands() == ["reset"]