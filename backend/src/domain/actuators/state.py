"""Actuator state machine: transition table + allowed commands per state.

States: off, idle, running, error, maintenance.
"""

ACTUATOR_STATES = {"off", "idle", "running", "error", "maintenance"}

# Legal transitions. "error" is reachable from any state (handled in context.py).
TRANSITIONS: dict[str, set[str]] = {
    "off": {"idle"},
    "idle": {"running", "maintenance", "off"},
    "running": {"idle"},
    "maintenance": {"idle"},
    "error": {"idle"},
}

# Commands available in each state. Reused by Phase 10 Command.
ALLOWED_COMMANDS: dict[str, list[str]] = {
    "off": ["power_on"],
    "idle": ["start_pump", "enter_maintenance", "power_off"],
    "running": ["stop_pump"],
    "maintenance": ["exit_maintenance"],
    "error": ["reset"],
}


class IllegalTransitionError(ValueError):
    pass


def validate_transition(current: str, target: str) -> None:
    if target not in ACTUATOR_STATES:
        raise IllegalTransitionError(f"Unknown state '{target}'")
    if target == "error":
        return  # any state -> error is always legal
    if target not in TRANSITIONS.get(current, set()):
        raise IllegalTransitionError(f"Cannot transition from '{current}' to '{target}'")


def allowed_commands_for(state: str) -> list[str]:
    return ALLOWED_COMMANDS.get(state, [])