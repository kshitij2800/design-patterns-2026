# Phase 10 - Command questions

## A. Pattern

1. State the intent of Command in plain language. What does it mean to **objectify a request**, and what can you do with that object that you cannot do with a bare `actuator.start()` call (queue, audit, undo, history)?

> [!NOTE]
> **_Your Answer_**
>
> Command turns a request ("start this pump") into an object instead of a direct method call. The object holds everything about the request: what to do (`command_type`), which device (`device_id`), the extra data (`payload`), and which state it should lead to (`target_state`).
>
> Because the request is now a thing we can hold, we can do more with it than just run it:
> - **Check it before running:** the service asks "is `start_pump` allowed in the current state?" before anything happens.
> - **Audit / history:** every attempt is saved in `command_log` with its status, even the ones that were refused.
> - **Queue or schedule it:** an object can be stored and executed later (we don't do this yet).
> - **Undo:** a command can remember what it changed and reverse it (we don't implement undo in this phase).
>
> A bare `actuator.start()` call just happens. Nothing is checked first, nothing is remembered, and nothing can be replayed.

2. Name the participants (**command**, **receiver**, **invoker**, **client**). Who creates the command, who triggers `execute()`, and who actually changes actuator/hardware state?

> [!NOTE]
> **_Your Answer_**
>
> - **Command:** the `Command` base class with `execute(port)`, and the concrete classes `StartPumpCommand`, `StopPumpCommand` and `SetLightLevelCommand`.
> - **Receiver:** the `ActuatorPort`, meaning the Phase 9 decorator stack (logging → max run time → simulation adapter). It does the real work.
> - **Invoker:** `CommandInvoker.run(command, port)`. It just calls `command.execute(port)` and never looks at the command type.
> - **Client:** `CommandService`. It turns the HTTP request into a command with `command_for(...)`, checks the state, and decides what to log.
>
> The **client** (`CommandService`) creates the command through the registry. The **invoker** triggers `execute()`. The **receiver** (the simulation adapter at the end of the decorator chain) performs the action on the "hardware". The saved state in `actuator_states` is updated afterwards by the service through `ActuatorContext.transition`.

3. If a command supports undo, when must it capture the data needed to reverse the action? Why is "capture **before** mutate" critical?

> [!NOTE]
> **_Your Answer_**
>
> It must save the old values **before** it changes anything, for example "this light was at level 2 and in state `idle`". Only after that may it apply the change.
>
> If it tried to read the old value afterwards, the old value would already be gone: the light would already be at the new level. Then undo would "restore" the wrong value.
>
> Our Phase 10 commands don't support undo. If we added it, `SetLightLevelCommand` would have to store the previous level and state before calling `port.apply(...)`.

## B. This phase of the application

4. Which command types did you implement (for example `start_pump`, `stop_pump`, `set_light_level`)? Why does the HTTP handler create a command and pass it to an **invoker** (or application service) instead of calling the actuator adapter from the router?

> [!NOTE]
> **_Your Answer_**
>
> I implemented three: `StartPumpCommand` (target state `running`), `StopPumpCommand` (target `idle`) and `SetLightLevelCommand` (target `running`). A registry maps each type string to its class.
>
> The router only passes the request to `CommandService`. It never calls the adapter itself, because then every route would have to repeat the same rules:
> - check `allowed_commands` first,
> - go through the decorators (logging and max run time),
> - update `actuator_states` afterwards,
> - write a `command_log` row.
>
> It would be easy to forget one of these, and a raw adapter call would skip the decorators completely. With commands, all of this is in one place. A new command is just one new class plus one registry line, with no `if command_type == ...` in the router.

5. Walk through the execute path: (1) consult State / `allowed_commands`, (2) if illegal → **rejected**, (3) if legal → decorated `apply`, update `actuator_states`, log **success** or **failed**. Why must a rejected command **not** change actuator state and **not** reach inner `apply`?

> [!NOTE]
> **_Your Answer_**
>
> `CommandService.execute` does this:
> 1. Load the device. If it is missing or is not an actuator → 404.
> 2. Find the command class in the registry. If the type is unknown → 400, and no row is written.
> 3. Load the saved state and ask `ActuatorContext.allowed_commands()`. If the command is not in the list → save a `rejected` row and return 409. Stop here.
> 4. Otherwise, run the command through the invoker and the decorated port. If the max-run-time decorator blocks it → save a `failed` row. The state is not changed.
> 5. If the apply worked, transition to `target_state` (only if it is different from the current state), then save a `success` row.
>
> A rejected command must not change anything because it was never valid. If it reached `apply`, the pump could physically start or stop in a state where that is not allowed, for example stopping a pump that is already idle, or starting one that is in maintenance. If it changed `actuator_states`, the database would no longer match what the device is really doing.

6. Distinguish **`rejected`** vs **`failed`** vs **`success`** in `command_log`. Give one greenhouse example of each. Why is "illegal in this state" not the same as "policy or adapter error after the command was accepted"?

> [!NOTE]
> **_Your Answer_**
>
> - **`rejected`:** the command is not allowed in the current state, so it never runs. Example: `stop_pump` on an idle pump returns 409 with "'stop_pump' is not allowed in state 'idle'".
> - **`failed`:** the command was allowed, but the actuator stack refused or failed while doing it. Example: `stop_pump` on a pump that has been `running` for over 30 minutes is blocked by the max-run-time decorator, giving "Max run time exceeded". The state stays `running`.
> - **`success`:** the command was allowed and applied. Example: `start_pump` on an idle pump moves it to `running`.
>
> They are different questions. "Rejected" means the request makes no sense right now, so we didn't even try. "Failed" means the request was valid, we tried, and something on the way (a policy or the hardware) stopped it. That difference matters when debugging: rejected points to the user or the UI, while failed points to a policy or the device.

7. Why is `command_log` a **different** table from Phase 9 `actuator_execution_log`? What concern does each log record (operator intent vs policy/adapter attempt)?

> [!NOTE]
> **_Your Answer_**
>
> They record different things at different layers:
> - **`command_log`** records **what someone asked for** and the result: every command attempt, with type, payload and status (`success` / `failed` / `rejected`). It is written by the application service.
> - **`actuator_execution_log`** records **what happened at the actuator**: each time the decorator stack was called, whether it worked, and which policies applied. It is written by the logging decorator.
>
> A rejected command appears only in `command_log`, because it never reached the actuator. A blocked command appears in both: `failed` in `command_log`, and a row with "Max run time exceeded" in the execution log. Keeping them separate means each table has one job, and the decorator does not need to know anything about commands.

## C. Compare, contrast, and scenarios

8. Contrast Command with **Strategy**. Strategy is an interchangeable **algorithm** (decide / quote). Command is a **side-effectful request** with history. How do they cooperate in this app (Phase 6 recommends; Phase 10 executes)?

> [!NOTE]
> **_Your Answer_**
>
> - **Strategy** answers "what should we do?" A strategy such as conservative or aggressive looks at moisture and thresholds and returns a recommendation ("irrigate" or "wait"). It changes nothing in the system.
> - **Command** answers "do this now." It has a side effect (a pump starts) and leaves a record in `command_log`.
>
> They work together: the Phase 6 strategy *recommends* irrigation for a zone, and a Phase 10 `start_pump` command *carries it out*. Today the user reads the recommendation and clicks the button. Later, automation could create the command from the recommendation itself, and it would still go through the same state check and audit.

9. Contrast Command with **State**. Who **triggers** the action, and who **decides whether it is legal**? Why must commands not bypass state guards?

> [!NOTE]
> **_Your Answer_**
>
> - **Command triggers the action:** "start the pump".
> - **State decides whether it is legal:** `ActuatorContext.allowed_commands()` says which commands are allowed in `idle`, `running`, `maintenance` and so on. After a successful apply, `ActuatorContext.transition()` also checks that the move to the new state is a legal transition.
>
> Commands must not bypass the state guard, because the state machine is the single source of truth for what a device may do. If a command could skip it, a pump in `maintenance` or `error` could be started, and the saved state would say one thing while the device does another.

10. The controls UI should disable actions that are not in `allowed_commands`. Why must the **backend** still reject illegal commands even if the UI is correct? What happens if a classmate's command calls the raw adapter and skips State and Decorator?

> [!NOTE]
> **_Your Answer_**
>
> Disabling buttons in the UI is only for convenience. It is not protection, because:
> - Anyone can call the API directly with `curl`, Scalar or a script. I did exactly that in my manual test, with `stop_pump` on an idle pump, and the backend correctly returned 409.
> - The UI can be out of date: another tab or user may have changed the state since the page loaded.
> - There may be other clients later, such as automation or MQTT.
>
> So the rule has to live in the backend.
>
> If a classmate's command called the raw `SimulationActuatorAdapter` directly, it would skip:
> - the state check, so illegal actions would run,
> - the max-run-time decorator, so a pump could run forever,
> - the logging decorator, so there would be no execution-log row.
>
> The pump would act, but `actuator_states` and the logs would not show it. That is why `CommandService` always gets its port from `build_actuator_port`, never a bare adapter.