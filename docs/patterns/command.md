# Command Pattern — Actuator Commands (Phase 10)

## Intent

Turn each actuator request ("start the pump", "set the light to level 3") into an
**object** that knows what to do, to which device, with what payload. Every attempt is
then run the same way and recorded in one audit table, `command_log`.

## Before: a function call from the router

Phase 9 had a demo route that took a command string and called the decorated
`ActuatorPort.apply()` directly. That gives no state check, no audit of rejected
attempts, no record of which state a command should lead to, and the router would
fill up with `if command == "start_pump": ...` branches as commands grow.

## After: command objects + an invoker

```text
CommandPanel (React) ── POST /api/commands ──► commands router
                                                   │ (only collaborator)
                                                   ▼
                                             CommandService
   1. device exists and is an actuator?           (404)
   2. command_for(type) ── registry ──► StartPumpCommand / StopPumpCommand / SetLightLevelCommand   (unknown → 400, no row)
   3. type in ActuatorContext.allowed_commands()? ── no ──► command_log "rejected" (409), stop
   4. CommandInvoker.run(command, port) ──► Logging → MaxRunTime → SimulationActuatorAdapter
          PolicyBlockedError ──► command_log "failed" (200), state unchanged
   5. ActuatorContext.transition(target_state) only if it differs ──► actuator_states
      command_log "success" (200)
```

| Role | Class / file |
|------|--------------|
| Command (interface) | `domain/commands/base.py` — `Command.execute(port)`, `command_type`, `target_state` |
| Concrete commands | `domain/commands/pump.py` (`StartPumpCommand` → `running`, `StopPumpCommand` → `idle`), `domain/commands/light.py` (`SetLightLevelCommand` → `running`) |
| Registry + Invoker | `domain/commands/invoker.py` — `COMMAND_REGISTRY`, `command_for`, `CommandInvoker.run` |
| Receiver | `ActuatorPort` — the Phase 9 stack from `build_actuator_port` (`interfaces/api/actuators.py`) |
| Client | `application/commands/service.py` — `CommandService` |
| Audit | `command_log` table, `CommandLogRepository` |

The invoker never branches on `command_type`: the registry maps the string to a class,
and the invoker just calls `execute(port)`. A new command is one class plus one
registry entry (and the command name in `ALLOWED_COMMANDS` for the states it is
legal in).

## Object vs function

A command object carries data the call alone doesn't: its type (used for the state
guard and the audit row), its payload, and its `target_state`. The service can ask a
command *before* running it whether it is allowed, and *after* running it which state
to save — the same way for every command.

## Audit

Every attempt for a known command on a real actuator writes exactly one
`command_log` row:

| Outcome | HTTP | `status` | `actuator_states` | `actuator_execution_log` |
|---------|------|----------|-------------------|--------------------------|
| Not allowed in current state | 409 | `rejected` | unchanged | no row (port never called) |
| Max-run-time decorator blocks | 200 | `failed` (`Max run time exceeded`) | unchanged | row written by the decorator |
| Applied | 200 | `success` | transitioned only if `target_state` differs | row written by the decorator |

Unknown `command_type` is 400 with no row; a missing device or a non-actuator is 404.

## Changes to earlier phases

- `LoggingActuatorDecorator` now **re-raises** `PolicyBlockedError` after writing its
  row (Phase 9 swallowed it). Otherwise the command service could not tell a blocked
  apply from a successful one and would log `success`.
- The Phase 9 stack is built in one function, `build_actuator_port(db)` in
  `interfaces/api/actuators.py`, used by both routers. The demo
  `POST /api/actuators/{id}/apply` route is removed.
- `set_light_level` is added to `ALLOWED_COMMANDS` for `idle` and `running`.

## Command vs calling the port from the router

| | Router calls `ActuatorPort` | Command + invoker |
|---|---|---|
| State guard | each route must remember it | one place, every command |
| Rejected attempts | nothing recorded | `rejected` row |
| New command | new `if` branch in the router | new class + registry line |
| Decorators | easy to bypass with a raw adapter | always `build_actuator_port` |V