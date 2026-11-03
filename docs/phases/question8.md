# Phase 8 — State questions

## A. Pattern

1. State the intent of the State pattern in plain language. What problem appears when lifecycle is modelled as boolean flags and scattered `if` guards?

> [!NOTE]
> ***Your Answer***
>
> he State pattern lets an object change its behavior when its internal state changes, so it appears to change class. Instead of one object carrying a pile of conditionals that check "what am I right now" before deciding what to do, the current state (and the rules for what's allowed from it) are pulled out into their own representation, and the object just delegates to whichever state it's currently in.
>
> Modelling lifecycle as booleans (`is_running`, `is_fault`, `is_maintenance`) breaks down fast: nothing stops two flags being true at once (`is_running = True` and `is_fault = True` simultaneously is nonsense but perfectly representable), the transition rules end up duplicated as `if`/`elif` chains everywhere the lifecycle is touched, and adding a new state means hunting down every one of those conditionals instead of changing one place.

2. Name the participants (**context**, **state interface**, **concrete states**, **client**). How does a successful command lead to a **transition**, and where do **guards** live?

> [!NOTE]
> ***Your Answer***
>
> In this implementation: `ActuatorContext` is the **context** — it holds the current state as a string and is what the rest of the app talks to. The **state interface** and **concrete states** are collapsed into a transition table rather than a class per state (`TRANSITIONS` and `ALLOWED_COMMANDS` dicts in `domain/actuators/state.py`) — a legitimate variant of State when the per-state behavior is just "which transitions and commands are legal," with no extra per-state logic needed. `ActuatorStateService` is the **client**: it loads the current state from the database, asks the context to transition, and persists the result.
>
> A successful command flows: API receives `POST /{id}/transition` → `ActuatorStateService.transition` loads the current state → builds an `ActuatorContext` → calls `ctx.transition(target)` → the context checks the table via `validate_transition`, and if legal, updates its own `state` field. Only then does the service call `save_state` to persist it. The **guard** lives entirely inside `validate_transition` in the domain layer — it's checked before the state is ever mutated, so an illegal transition never gets applied even in memory

3. What is `allowed_commands` (or equivalent) for? Why is exposing “what can I do **now**?” better than letting the UI guess from a raw state string?

> [!NOTE]
> ***Your Answer***
>
> `allowed_commands` is a list of command names (`start_pump`, `stop_pump`, etc.) computed from the actuator's current state via `allowed_commands_for(state)`, and it's returned alongside `state` on every device read.
>
> It's better than the UI guessing from the raw state string because it keeps the "what's legal from here" knowledge in exactly one place — the domain's transition table. If the UI inferred legality itself (e.g. "if state is idle, show a Start button"), that logic would be duplicated between frontend and backend, and the two could drift out of sync whenever the table changes. By exposing `allowed_commands` directly, the UI only has to render whatever the backend says is available — it never encodes a rule about what's legal.

## B. This phase of the application

4. Which actuator states did you implement (for example idle, running, error)? Sketch the **legal** transitions (which command or event moves idle → running, running → idle, into error, and out of error).

> [!NOTE]
> ***Your Answer***
>
> Five states: `off`, `idle`, `running`, `error`, `maintenance`.
>
> Legal transitions:
> - `off → idle` (`power_on`)
> - `idle → running` (`start_pump`), `idle → maintenance` (`enter_maintenance`), `idle → off` (`power_off`)
> - `running → idle` (`stop_pump`)
> - `maintenance → idle` (`exit_maintenance`)
> - `error → idle` (`reset`)
> - Any state `→ error` is always legal (an actuator can fault from wherever it happens to be), but `error` can only be left by going back to `idle`.
>
> Anything not in that table — e.g. `off → running`, `running → maintenance`, `maintenance → maintenance` — is rejected.

5. Why is actuator state stored in `actuator_states` (or equivalent) rather than only in process memory? What must still be true after you restart the backend?

> [!NOTE]
> ***Your Answer***
>
>  If state lived only in process memory, it would vanish every time the backend restarts or redeploys, and it couldn't be shared correctly across multiple worker processes/instances serving the same API. Storing it in `actuator_states` (a real table keyed by `device_id`, FK to `devices`) makes it durable and consistent regardless of process lifecycle.
>
> After a restart, every actuator must resolve to the same state it had before the restart — I verified this directly: transitioned an actuator to `running` via `POST /transition`, ran `docker compose restart backend`, then confirmed `GET /api/devices` still showed `"state": "running"` for that actuator rather than resetting to `idle`.

6. An **illegal** transition must raise a domain error and **must not** update the database. Why? Which HTTP status is reasonable for that case (400 or 409), and why should the rule live in the domain rather than in React?

> [!NOTE]
> ***Your Answer***
>
> It must raise and not write because a half-applied illegal transition would break the lifecycle invariant — only states reachable through legal edges should ever be stored. `validate_transition` runs before `self.state` is mutated, so the error fires before there's anything to persist.
>
> I used **409 Conflict**: the target name is valid, but it conflicts with the actuator's current state — not malformed input (that's 422).
>
> The rule belongs in the domain, not React, because the frontend is just one client. If each client reimplemented the rules, they could drift or be bypassed; the backend is the only place that can actually enforce the invariant.

7. Device JSON gains `state` and `allowed_commands`. How does the dashboard use those fields (badges, disable illegal buttons)? How does this prepare **Phase 10 Command**?

> [!NOTE]
> ***Your Answer***
>
> `ActuatorStateBadge` renders a color-coded pill per actuator using `state` (slate idle/off, emerald running, red error, amber maintenance), with `allowed_commands` shown as a hover tooltip. Full action buttons are deferred to Phase 10.
>
> This sets up Phase 10: Command can read `allowed_commands` to decide which buttons to enable, and its handlers can re-check the same guard server-side before executing — UI and execution both defer to one source of truth instead of each guessing legality independently.
 

## C. Compare, contrast, and scenarios

8. Contrast State with **Strategy**. Both look like “context delegates to an object.” Who typically **changes** the active object, and is the variation a **lifecycle** or a **selectable policy**? Give a greenhouse example of each (this phase vs Phase 6).

> [!NOTE]
> ***Your Answer***
>
> In Strategy (Phase 6), the **user** picks the active policy, and it stays picked until changed — saving `strategy_key` doesn't change by itself. The variation is a **selectable policy**: both strategies are always valid, it's just a choice of rule.
>
> In State (Phase 8), the **object itself** changes its active state as a side effect of commands — `start_pump` moves `idle → running` automatically, nobody "chooses" it. The variation is a **lifecycle**: only certain states are reachable from others.

9. Contrast State with a pile of booleans (`is_running`, `is_fault`, `is_maintenance`). Why do illegal combinations of flags appear, and how do explicit state objects (or a transition table) prevent that?

> [!NOTE]
> ***Your Answer***
>
>  With separate booleans, nothing stops `is_running` and `is_maintenance` both being `True` at once — each flag is set independently, so meaningless combinations are still representable. Every reader also has to re-derive "what does this mean" by checking several flags together.
>
> A single `state: str` plus a transition table makes illegal combinations unrepresentable by construction — the actuator is in exactly one state, and every change goes through `ActuatorContext.transition`, which checks the table before mutating.

10. A classmate puts HTTP status mapping or SQLAlchemy commits **inside** a concrete state class. Another state mutates a flag directly and skips `transition` / `set_state`. Explain why each is a trap.

> [!NOTE]
> ***Your Answer***
>
>  HTTP status mapping or commits inside a state class break the domain's isolation from infrastructure — `domain/actuators/` has no FastAPI or SQLAlchemy imports, which is why the 7 domain tests run with zero database. Coupling a state to infrastructure means it can't be reused or tested the same way.
>
> Mutating state directly and skipping `transition` is worse: it bypasses `validate_transition` entirely, so illegal jumps (e.g. `running → maintenance`) get written with no guard catching them — silently breaking the one invariant the pattern exists to protect.