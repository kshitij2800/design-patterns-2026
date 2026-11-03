# State Pattern — Actuator Lifecycle (Phase 8) 

## Problem: an actuator's legal actions depend on what it's doing

An actuator (pump, grow light) moves through a lifecycle: it can be idle, actively
running, powered off, under maintenance, or in an error condition. Which commands
make sense depends entirely on which of these it's currently in — `stop_pump` is
meaningless on an idle pump, and `start_pump` is meaningless on a running one.

Without a state machine, this logic tends to leak into the router or the UI as
scattered `if device.state == "idle": ...` checks, repeated everywhere a transition
or an available-actions list is needed.

## Solution: one transition table, one place that knows the rules

`domain/actuators/state.py` defines every actuator state, the legal transitions
between them, and which commands are available in each state. `ActuatorContext`
wraps one actuator's current state and is the only thing allowed to change it —
`transition(target)` validates against the table and raises `IllegalTransitionError`
before anything is written; nothing is ever applied first and checked after.

```text
            power_on
   off ───────────────▶ idle ───────────────▶ running
    ▲                    │  ▲                    │
    │ power_off          │  │ exit_maintenance    │ stop_pump / error
    │                     ▼  │                     ▼
    └──────────────── maintenance              error
                                                   │
                                            reset  │
                                                   ▼
                                                 idle
```

(`* → error` is legal from every state; `error → idle` is the only way out.)

## Where in code

| Role | File |
|------|------|
| States + transition table + allowed commands | `backend/src/domain/actuators/state.py` |
| Guard (the only thing that mutates state) | `backend/src/domain/actuators/context.py` — `ActuatorContext` |
| Persistence | `backend/src/infrastructure/persistence/models.py` — `ActuatorStateRow`; `actuator_state_repository.py` |
| Application service (load → transition → save) | `backend/src/application/devices/actuator_state_service.py` — `ActuatorStateService` |
| API | `backend/src/interfaces/api/devices.py` — `POST /api/devices/{id}/transition`; `state`/`allowed_commands` on `GET /api/devices` |
| Frontend | `frontend/src/features/devices/ActuatorStateBadge.tsx` |

## Transition table

| From | Legal targets |
|------|----------------|
| `off` | `idle` |
| `idle` | `running`, `maintenance`, `off` |
| `running` | `idle` |
| `maintenance` | `idle` |
| `error` | `idle` |
| *(any state)* | `error` |

## State persists, never lives only in the FastAPI process

`actuator_states` is a real table keyed by `device_id`. `ActuatorStateService.transition`
loads the current state from the database, asks `ActuatorContext` to validate and
apply the move, and only then calls `save_state`. An illegal transition raises before
`save_state` is ever called, so the stored state is left untouched — confirmed by
restarting the backend and by `test_illegal_transition_rejected_and_not_persisted`.

## Error mapping

- Actuator not found (or the device exists but isn't an actuator) → **404**.
- Illegal transition → **409** (the domain's `IllegalTransitionError`, not a Pydantic
  validation error — the target name is syntactically valid, just not reachable
  from the current state).

## Why State (and not if/else in the router)

The alternative is a router or React component full of
`if device.state == "idle" and target == "running": ...`. That knowledge would be
duplicated anywhere a transition or an "allowed actions" list is needed — the API,
the UI, and later Phase 10's Command handlers. With State, `ActuatorContext` is the
single authority: Phase 10 will call `allowed_commands()` before executing a command,
and the router never encodes a transition rule itself.

## Extension: adding a new state or action

1. Add the state name to `ACTUATOR_STATES` in `state.py`.
2. Add its legal outgoing edges to `TRANSITIONS` and its commands to `ALLOWED_COMMANDS`.
3. Add a test exercising at least one legal and one illegal edge involving it.

No change is needed in the repository, the service, the API route, or the frontend —
they all read the table through `ActuatorContext`/`allowed_commands_for`.