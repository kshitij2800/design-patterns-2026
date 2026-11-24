# Phase 11 - Observer questions
 
## A. Pattern
 
1. State the intent of Observer in plain language. What is a **one-to-many** dependency here, and why must the subject notify dependents **without** knowing their concrete classes?
> [!NOTE]
> **_Your Answer_**
>
> Observer lets one object announce "something happened" and lets any number of other objects react, without the announcer knowing who they are.
>
> The **one-to-many** dependency here is one `EventBus` and many handlers. When a reading is stored, one `ReadingCreated` event can reach several listeners. Today that is `MoistureThresholdSubscriber`; later it could also be a WebSocket or a metrics counter.
>
> The subject must not know the concrete classes. If `ReadingIngest` called `AlertRepository` or a socket directly, every new reaction would mean editing the reading code, and the reading code would depend on alerts, the database and the UI. With the bus, the publisher only knows the event. New listeners subscribe without changing it.
 
2. Name the participants (**subject / event bus**, **observer / subscriber**, **concrete observers**, **event**, **publisher**). What does `subscribe` / `unsubscribe` / `publish` (or `notify`) each do? This example’s `EventBus` implements `subscribe` and `publish` only.
> [!NOTE]
> **_Your Answer_**
>
> - **Subject / event bus:** `EventBus` in `domain/events/bus.py`. It keeps a list of handlers for each event class.
> - **Observer / subscriber:** any handler function registered on the bus, called with the event.
> - **Concrete observers:** `MoistureThresholdSubscriber` (`on_reading`) and `AlertPersistenceSubscriber` (`on_threshold`, `on_command`, `on_state`).
> - **Event:** a small, frozen dataclass describing what happened: `ReadingCreated`, `ThresholdCrossed`, `CommandFailed`, `ActuatorStateChanged`.
> - **Publisher:** the code that reports the event: `ReadingIngest`, `CommandService`, `ActuatorStateService`. `MoistureThresholdSubscriber` is also a publisher, because it publishes `ThresholdCrossed`.
>
> - `subscribe(event_type, handler)` adds a handler to the list for that event class.
> - `publish(event)` calls every handler for that event's class, in the order they subscribed.
> - `unsubscribe` would remove a handler. Our bus doesn't have it, because the subscribers are attached once in `build_event_bus` and never removed.
 
3. When should you use Observer, and when should you skip it (only one listener forever; or you need a strict multi-step workflow with guaranteed order)?
> [!NOTE]
> **_Your Answer_**
>
> **Use it** when one thing happening should cause several independent reactions, and you expect more reactions later. Examples: a reading being stored, a command failing, an actuator changing state. Each reaction can be added without touching the code that caused it.
>
> **Skip it** when:
> - There will only ever be one listener. A direct method call is simpler and easier to follow.
> - You need a strict workflow where step B must happen after step A, and must not happen if A fails. Example: in `CommandService`, the state check → apply → state save → log order matters, so it is written as plain code in one method, not as events. Events hide the order and make "what runs next" hard to see.
 
## B. This phase of the application
 
4. Give at least two **domain events** you publish in this lab, including `reading.created` (only when `tracking_enabled` is true), a threshold-crossed event, command-failed, and `ActuatorStateChanged`. The persistence subscriber stores `state.changed` only when that state is `error`. Who publishes `reading.created`, and why do a manual read, the simulation sampler, and MQTT translation share that one ingest publish? Why must a publisher **not** import the alerts repository or the UI?
> [!NOTE]
> **_Your Answer_**
>
> The events and who publishes them:
> - **`ReadingCreated`** (`reading.created`), published by `ReadingIngest.record` after a reading is stored, only if the device has `tracking_enabled`.
> - **`ThresholdCrossed`** (`threshold.crossed`), published by `MoistureThresholdSubscriber` when a `vwc` reading in a zone is strictly below that zone's `moisture_threshold_low`.
> - **`CommandFailed`** (`command.failed`), published by `CommandService` when the max-run-time decorator blocks a command.
> - **`ActuatorStateChanged`** (`state.changed`), published by `CommandService` and `ActuatorStateService` after every successful `save_state`. Only `error` becomes an alert row.
>
> `reading.created` is published in one place, `ReadingIngest.record`. Manual read (`take_reading` → `record`), the sampler and MQTT translation all end in that method. So there is one publish rule, and the tracking check lives in one place. If each path published on its own, one of them could forget the `tracking_enabled` check, or publish twice.
>
> Publishers must not import `AlertRepository` or UI code. Otherwise reading and command code would depend on how alerts are stored and shown, and every new reaction would mean editing them. A test (`test_publishers_do_not_import_alert_repository`) checks that the three publisher modules don't mention `AlertRepository`.
 
5. What does `AlertPersistenceSubscriber` (or your equivalent) do when it handles an event? Name the three stored rows: `threshold.crossed` / `warning` / `Moisture below zone low`, `command.failed` / `warning` / the failure message, and `state.changed` / `critical` / `Actuator entered error`. Why do alerts live in the `alerts` table so the event feed still shows them after a **refresh**?
> [!NOTE]
> **_Your Answer_**
>
> It turns an event into one active row in the `alerts` table, through `AlertRepository.insert`. It copies `device_id`, `location_id` and `zone_id` from the event. For an unassigned device, like the provisioned pump, `location_id` and `zone_id` stay null.
>
> | Event | `event_type` | `severity` | `message` |
> |-------|--------------|------------|-----------|
> | `ThresholdCrossed` | `threshold.crossed` | `warning` | `Moisture below zone low` |
> | `CommandFailed` | `command.failed` | `warning` | the failure text, e.g. `Max run time exceeded` |
> | `ActuatorStateChanged` with state `error` | `state.changed` | `critical` | `Actuator entered error` |
>
> For any other state (`running`, `idle`…) `on_state` returns without writing anything.
>
> Events are gone as soon as `publish` finishes, and React state is gone when the page reloads. Because the subscriber writes to the database, `GET /api/alerts` can return the alerts at any time. After a refresh, the feed polls again and shows the same rows.
 
6. The dashboard Event feed **polls** `GET /api/alerts` every 5 seconds in this phase. `services/realtime.ts` is only a **stub**. Why is full WebSocket **not** required in this phase? What should Phase 12 plug into so you do **not** re-implement pub/sub inside socket handlers? Phase 12 subscribes a dashboard socket to this same bus, and the example publishes `AlertCreated` after each insert for that socket.
> [!NOTE]
> **_Your Answer_**
>
> This phase is about the Observer pattern inside the backend: publishers, a bus and subscribers. The alerts are already stored, so the UI only has to read them. A 5-second poll of `GET /api/alerts` is enough to show them and is much simpler than a socket. Live push to browsers is a separate topic, and it is Phase 12's job.
>
> `realtime.ts` already exports `RealtimeEvent` and `subscribeRealtime(...)`, which returns an unsubscribe function. Its body does nothing yet. The UI therefore already has the shape it will use, and Phase 12 only fills in the body.
>
> Phase 12 should plug into the **same `EventBus`**: the dashboard socket becomes one more subscriber. For example, after each alert insert an `AlertCreated` event is published, and a socket subscriber sends it to the browsers. The socket handlers then don't need their own list of listeners or their own "who should hear this" logic. The publishers (`ReadingIngest`, `CommandService`, `ActuatorStateService`) don't change at all.
 
7. Describe the must-demo path: a **tracked** low-moisture reading leads to an alert row that appears in the feed after poll. Which objects collaborate (reading pipeline → bus → subscriber → API → UI), and which object must **not** write the alert directly? What is stored, and what is not published, when `tracking_enabled` is false?
> [!NOTE]
> **_Your Answer_**
>
> Example: a moisture sensor on Bench 1 (low threshold `0.20`) reports `0.10`.
>
> 1. **Reading pipeline:** a manual read, the sampler or MQTT gives a `Reading`. `ReadingIngest.record` stores it in `sensor_readings`. The device is tracked, so it publishes `ReadingCreated` with the device's `location_id` and `zone_id`.
> 2. **Bus → `MoistureThresholdSubscriber`:** the unit is `vwc`, a zone is set, and `0.10 < 0.20`, so it publishes `ThresholdCrossed`.
> 3. **Bus → `AlertPersistenceSubscriber`:** inserts a `threshold.crossed` / `warning` / `Moisture below zone low` row with that location and zone.
> 4. **API:** `GET /api/alerts?zone_id=<Bench 1>` returns the row, newest first.
> 5. **UI:** `EventFeed` in `#events` polls every 5 seconds and shows the row with a yellow warning badge.
>
> `ReadingIngest`, and the router that called it, must **not** write the alert directly. Only `AlertPersistenceSubscriber` inserts alert rows.
>
> When `tracking_enabled` is false, the reading **is still stored** in `sensor_readings`, but **`reading.created` is not published**. So no threshold check runs, and no alert is created.
 
## C. Compare, contrast, and scenarios
 
8. Contrast Observer with **Facade**. Facade simplifies **calling into** a subsystem. Observer **fans out** notifications after something happened. How do both appear in this greenhouse (Phase 7 overview vs this phase)?
> [!NOTE]
> **_Your Answer_**
>
> **Facade** is about asking: one caller wants something from many subsystems, and one object hides how to get it. In Phase 7, `LocationOverviewFacade.get_overview(location_id)` collects the location, zones, devices, latest readings and strategy, and returns one response. The router calls one method, and the facade knows all the parts. Information flows **in**, as a request, and back as one answer.
>
> **Observer** is about telling: one thing happened, and many listeners may react. In this phase, `ReadingIngest` publishes `ReadingCreated`, and it doesn't know who listens or what they do. Information flows **out** after the fact, to any number of subscribers.
>
> A facade knows everything it calls. A publisher knows nothing about its subscribers.
 
9. Contrast Observer with **Command**. Command captures **intent to act**. Observer propagates **outcomes**. How can `execute()` publish an event without the command class knowing who persists alerts?
> [!NOTE]
> **_Your Answer_**
>
> A **command** says "do this": `StartPumpCommand` wants the pump to start. It exists before anything happens, and it can be checked, rejected or logged. An **event** says "this happened": `CommandFailed` or `ActuatorStateChanged` reports the result afterwards.
>
> In my code, the command classes themselves stay small. They only call `port.apply(...)`. The publishing happens in `CommandService.execute`, which already knows the outcome:
> - if the decorator blocks it → `bus.publish(CommandFailed(...))`
> - after `save_state` → `bus.publish(ActuatorStateChanged(...))`
>
> `CommandService` only gets an `EventBus` in its constructor. It never sees `AlertRepository` or `AlertPersistenceSubscriber`. Who persists alerts is decided once, in `build_event_bus`, where the subscribers are attached. The command side reports outcomes, and the alert side decides what to do with them.
 
10. One subscriber throws during `notify` / `publish` and aborts the loop, so later subscribers never run. Why is that a trap? What should the bus do so a failing alert writer does not block metrics (or later WebSocket) subscribers?
> [!NOTE]
> **_Your Answer_**
>
> The handlers are supposed to be independent, but a plain `for handler in handlers: handler(event)` loop makes them depend on each other. If the alert writer throws (for example the database insert fails), every handler after it is skipped, so a metrics counter or a WebSocket push never happens. The exception also travels back into the publisher. A reading that was already stored then looks like a failed request, and an unrelated bug in alerts breaks reading ingest.
>
> My current `EventBus.publish` is this simple loop, so it has this weakness. A safer bus would:
> - wrap each handler call in `try/except`,
> - log the error with the handler name and the event,
> - continue with the next handler,
> - not re-raise to the publisher.
>
> One failing subscriber then only loses its own work. Phase 12 could also add a retry or a dead-letter list for failed events.
 