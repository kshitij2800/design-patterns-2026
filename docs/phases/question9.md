# Phase 9 — Decorator questions

## A. Pattern

1. State the intent of Decorator in plain language. Why is stacking wrappers a flexible alternative to a combinatorial explosion of subclasses (`LoggingRetryMaxRuntimeActuator`, …)?

> [!NOTE]
> ***Your Answer***
>
> A decorator wraps an object that implements the same interface, and adds behavior before/after delegating the call to the object it wraps. The alternative — a subclass for every combination of policies — explodes combinatorially: 2 policies already need up to 3 extra classes (`Logging`, `MaxRuntime`, `LoggingMaxRuntime`), and every new policy roughly doubles the set. Decorators compose at runtime instead: N policies need only N small classes, stacked in whatever combination a composition root chooses, including combinations nobody wrote a dedicated subclass for.

2. Name the participants (**component**, **concrete component**, **decorator**, **concrete decorators**). What interface does every decorator present to the caller, and why must that match the wrapped component?

> [!NOTE]
> ***Your Answer***
>
> - Component (interface): `ActuatorPort`
> - Concrete component: `SimulationActuatorAdapter`
> - Decorator: any class implementing `ActuatorPort` that holds a reference to another `ActuatorPort`
> - Concrete decorators: `LoggingActuatorDecorator`, `MaxRunTimeActuatorDecorator`
>
> Every decorator presents `apply(device_id, command, payload) -> None` — exactly `ActuatorPort`'s signature — because the caller holds a reference typed as `ActuatorPort` and calls it without knowing how many layers are stacked inside. If a decorator's signature drifted even slightly, it would no longer be substitutable for the thing it wraps, and the caller would have to know which layer it's really talking to — which defeats the point of the pattern.

3. **Order matters.** Using logging and retry (or logging and max-run-time) as an example, explain how wrapping A around B can change what you observe compared with wrapping B around A.

> [!NOTE]
> ***Your Answer***
>
> In this app, `LoggingActuatorDecorator` wraps `MaxRunTimeActuatorDecorator` wraps `SimulationActuatorAdapter`. Logging is outermost, so it sees every outcome below it — including a block raised by max-run-time that never reached the real adapter. If the order were reversed (max-run-time outermost, logging innermost), a blocked attempt would raise straight out of `apply()` before logging's `try/except` ever ran, so nothing would be recorded. Same components, different order, different observable behavior.
 

## B. This phase of the application

4. What is `ActuatorPort` here, and which **at least two** decorators did you stack around the real adapter (for example logging and max run-time)? Where is the chain wired (composition root / factory), and why not inside the HTTP router?

> [!NOTE]
> ***Your Answer***
>
> `ActuatorPort.apply(device_id, command, payload)` is the one method every layer implements. The two decorators are `LoggingActuatorDecorator` (outermost) and `MaxRunTimeActuatorDecorator` (middle), wrapping `SimulationActuatorAdapter` (innermost). The chain is built in `get_service()` inside `interfaces/api/actuators.py` — the composition root. It isn't in the router because the router's job is translating HTTP into a method call and a response; deciding which policies apply and in what order is an architectural decision that belongs in one place, not duplicated in every endpoint that might call `apply()`.
 

5. Max run-time can **short-circuit**: the inner adapter is never called. Why must a blocked attempt still produce a row in `actuator_execution_log` with `success=false` and the policy named in `policy_applied`?

> [!NOTE]
> ***Your Answer***
>
> Without a recorded row, there would be no way to tell, after the fact, that a command was attempted and rejected versus never attempted at all. The execution log exists to show exactly that distinction: `success=false` with `policy_applied` naming which policy stopped it (`["maxRunTime", "logging"]`) and a human-readable `message`. This only works because `LoggingActuatorDecorator` is outermost and catches `PolicyBlockedError` before it would otherwise propagate out of `apply()`.

6. How does max run-time know the actuator has been running too long (for example `actuator_states.updated_at` from Phase 8)? Why is that data from **State**, not something the decorator should invent as a second lifecycle?

> [!NOTE]
> ***Your Answer***
>
> `MaxRunTimeActuatorDecorator` reads the actuator's current `state` and `updated_at` through `ActuatorStateRepository`, which owns `actuator_states` from Phase 8. It shouldn't track its own notion of "how long has this been running," because that would create two competing sources of truth for actuator lifecycle — the one `ActuatorContext` guards, and a second one only the decorator knows about. Reusing `updated_at` means the decorator trusts the same timestamp every transition already updates, instead of tracking something in parallel that could drift out of sync with it.

7. `GET /api/actuators/executions` feeds the dashboard execution log. Why persist attempts in the database instead of only printing to stdout? What should the UI show after a blocked attempt and a refresh?

> [!NOTE]
> ***Your Answer***
>
> Logger/print output disappears into container logs, isn't queryable, and isn't visible to anyone using the dashboard. Persisting to `actuator_execution_log` gives a durable history — who/what was attempted, when, and whether it succeeded — that survives restarts and doesn't require reading logs. After a blocked attempt and a refresh, the UI should show a row with a "blocked" badge, policies `maxRunTime, logging`, and the message "Max run time exceeded."

## C. Compare, contrast, and scenarios

8. Contrast Decorator with **Adapter**. Both wrap. One **keeps** the interface and **adds** behaviour; the other **changes** the interface and **translates**. Which is which in this greenhouse (Phase 9 vs Phase 5)?

> [!NOTE]
> ***Your Answer***
>
> Adapter (Phase 5) changes the interface: `VendorStubSensorAdapter` takes a foreign shape (`{"reading_x100": 4100, "uom": "PCT_VWC", ...}`) and translates it into `Reading` — the caller never sees the vendor's shape at all. Decorator (Phase 9) keeps the interface identical — every layer is still `ActuatorPort.apply(...)` — and only adds behavior around the call. Adapter answers "how do I make this incompatible thing fit"; Decorator answers "how do I add behavior without changing what already fits."

9. Contrast Decorator with **inheritance** of combined policies. How does composition let you add or remove a policy without a new subclass for every combination?

> [!NOTE]
> ***Your Answer***
>
> A subclass bakes its policy combination in at compile time — `LoggingSimulationAdapter` is permanently logging-plus-simulation, forever. Adding or removing a policy means writing or deleting a class and redeploying. With decorators, the composition root just changes which objects it wraps around which, at runtime — no subclass for the new combination needs to exist anywhere in the codebase.
 

10. A classmate’s decorator changes the method signature “a little” (extra required argument, different return type). Another ignores wrap order and cannot explain whether logging runs once per logical call or per inner attempt. Explain why each is a trap.

> [!NOTE]
> ***Your Answer***
>
> Changing the signature breaks substitutability: the decorator is no longer interchangeable with the plain `ActuatorPort` the caller expects, so code that works against the real adapter can break or behave differently against the wrapped one — the caller can no longer treat every layer as "just an `ActuatorPort`."
>
> Ignoring wrap order makes behavior impossible to reason about: whether logging captures a blocked attempt depends entirely on whether it sits outside or inside the policy that blocks. Without a deliberate, known order, there's no fixed answer to "does this log once per request or once per inner attempt" — different people on the team end up with different mental models of what the system actually does.