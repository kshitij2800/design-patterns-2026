# Decorator Pattern — Actuator Execution Policies (Phase 9)

## Problem: policies shouldn't live inside the adapter

`SimulationActuatorAdapter` (Phase 5) does one thing: it records a command and logs
it. Phase 9 needs two more behaviours wrapped around every `apply()` call — write a
permanent record of the attempt, and reject it outright if the actuator has been
`running` for 30+ minutes. Neither belongs inside `SimulationActuatorAdapter` itself:
a real GPIO adapter or a future vendor actuator would need the exact same policies,
and baking them into one adapter class means copying that logic into every adapter
that comes later, or scattering `if` checks into the router.

## Solution: wrap the port, not the adapter

Each policy is its own class implementing `ActuatorPort`, wrapping another
`ActuatorPort`. A caller only ever holds the outermost wrapper and calls `apply()`
exactly as it would on the bare adapter — it has no way to know, or need to know,
how many layers are stacked underneath.

```text
LoggingActuatorDecorator ──▶ MaxRunTimeActuatorDecorator ──▶ SimulationActuatorAdapter
   (always writes a row)         (may block here)              (innermost — unaware
                                                                  it's wrapped)
```

`MaxRunTimeActuatorDecorator.apply()` checks the actuator's persisted state and
`updated_at`. If it's `running` and has been for 30+ minutes, it raises
`PolicyBlockedError("maxRunTime", "Max run time exceeded")` and never calls the inner
component. Otherwise it calls through.

`LoggingActuatorDecorator`, as the outermost layer, wraps that call in a try/except:

- clean success → insert a row (`success=true, policy_applied=["logging"], message=null`)
- `PolicyBlockedError` → insert a row (`success=false, policy_applied=[policy_name, "logging"], message=...`) and stop — the block *is* the outcome, nothing to re-raise
- any other exception → insert a failure row, then re-raise (a real adapter error shouldn't be swallowed)

Only policies that actually *did* something appear in `policy_applied`. Logging
always acts (it always writes the row), so it's always listed. Max-run-time only
appears when it actually blocked — a pass-through contributes nothing to say.

## Where in code

| Role | File |
|------|------|
| Port (unchanged since Phase 5) | `backend/src/domain/actuators/ports.py` — `ActuatorPort` |
| Blocked-policy signal | `backend/src/domain/actuators/errors.py` — `PolicyBlockedError` |
| Decorators | `backend/src/infrastructure/adapters/actuators/logging_decorator.py`, `max_runtime_decorator.py` |
| Innermost component | `backend/src/infrastructure/adapters/actuators/simulation.py` — `SimulationActuatorAdapter` |
| Persistence | `backend/src/infrastructure/persistence/models.py` — `ActuatorExecutionLogRow`; `execution_log_repository.py` |
| Composition root | `backend/src/interfaces/api/actuators.py` — `get_service` builds the chain |
| Frontend | `frontend/src/features/actuators/ExecutionLog.tsx` |

## Composition order, and why it's fixed

`LoggingActuatorDecorator(MaxRunTimeActuatorDecorator(SimulationActuatorAdapter(), states), log_repo)`

Logging has to be outermost. If max-run-time were outermost instead, a block would
raise straight out of `apply()` with nothing recording it — the whole point of this
phase is that a blocked attempt is *visible*, as a `success=false` row, not a silent
exception. Being outermost means logging observes every outcome below it, including
a block it didn't cause itself.

## Decorator vs inheritance

The alternative is a subclass per policy combination: `LoggingSimulationAdapter`,
`MaxRunTimeSimulationAdapter`, `LoggingMaxRunTimeSimulationAdapter`, and a fourth one
the moment a third policy (say, a cooldown) joins — the subclass count doubles with
every new policy, and each one re-implements the adapters it wraps. Decorators
compose at runtime instead: two small classes, stacked in whatever order the
composition root chooses, work for any adapter that implements `ActuatorPort` —
including adapters that don't exist yet.

## Extension: adding a third policy

1. Write a class implementing `ActuatorPort` that wraps an inner `ActuatorPort`,
   checks its own condition, and either calls through or raises `PolicyBlockedError`
   with its own policy name.
2. Insert it into the chain in `get_service` at the position its ordering requires.
3. Add a unit test proving it doesn't call the inner component when it blocks, and
   that a blocked attempt still produces a logged row via `LoggingActuatorDecorator`.

No change is needed in `ActuatorPort`, `SimulationActuatorAdapter`, the API route, or
the frontend — they all go through the decorated port without knowing what's inside it.