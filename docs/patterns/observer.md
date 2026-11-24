# Observer Pattern — Event Bus and Alerts (Phase 11)

## Intent

Let one part of the system announce "something happened" without knowing who cares.
Publishers emit domain events on an `EventBus`; subscribers react. Adding a reaction
(an alert, later a WebSocket push) never changes the publisher.

## Before

Without events, every place that can cause an alert would write the alerts table itself:
`ReadingIngest` would check thresholds and insert rows, `CommandService` would insert on
failure, the transition service would insert on `error`. Three services would depend on
alerts, and Phase 12's WebSocket would need yet another call in each of them.

## After

```text
POST /read ─┐
sampler ────┼─► ReadingIngest.record ──► bus.publish(ReadingCreated)   (tracked devices only)
MQTT ───────┘                                   │
                                                ▼
                                  MoistureThresholdSubscriber
                          unit=vwc, zone set, value < zone low? ──► bus.publish(ThresholdCrossed)
                                                                           │
CommandService ── max-run-time block ──► bus.publish(CommandFailed) ───────┤
CommandService / ActuatorStateService ── save_state ──► bus.publish(ActuatorStateChanged)
                                                                           │
                                                                           ▼
                                                        AlertPersistenceSubscriber ──► alerts
                                                                                          │
                                                       GET /api/alerts ◄── EventFeed (#events, every 5 s)
```

| Role | Class / file |
|------|--------------|
| Subject | `domain/events/bus.py` — `EventBus.subscribe(event_type, handler)`, `publish(event)` |
| Events | `domain/events/events.py` — `ReadingCreated`, `ThresholdCrossed`, `CommandFailed`, `ActuatorStateChanged` |
| Publishers | `ReadingIngest`, `CommandService`, `ActuatorStateService` (Phase 8 transition service) |
| Observers | `application/alerts/subscribers.py` — `MoistureThresholdSubscriber`, `AlertPersistenceSubscriber` |
| Wiring | `build_event_bus(session)` in `subscribers.py` — one bus, both subscribers attached |
| Storage / API | `alerts` table, `AlertRepository`, `GET /api/alerts` |

## Rules

| Event | Row | Severity | Message |
|-------|-----|----------|---------|
| `ThresholdCrossed` | `threshold.crossed` | warning | `Moisture below zone low` |
| `CommandFailed` | `command.failed` | warning | the failure text (`Max run time exceeded`) |
| `ActuatorStateChanged` with `state == "error"` | `state.changed` | critical | `Actuator entered error` |

- `reading.created` is published from one place (`ReadingIngest.record`), so manual read,
  sampler and MQTT translation share one rule; nothing is published when
  `tracking_enabled` is false (the reading is still stored).
- `location_id` / `zone_id` are copied from the device and stay null for an unassigned device.
- Alert FKs are nullable and `ON DELETE SET NULL`. Alerts live in the database, not React
  state, so they survive a refresh.

## Subject vs subscribers

The bus knows handlers only as callables keyed by event class and runs them in
subscription order. Publishers depend on `EventBus` only — they never import
`AlertRepository` (a test checks this). Subscribers depend on event types, not on who
published them. `MoistureThresholdSubscriber` is both an observer (of `ReadingCreated`)
and a publisher (of `ThresholdCrossed`).

## Phase 11 bus vs Phase 12 WebSocket

| | Phase 11 `EventBus` | Phase 12 WebSocket |
|---|---|---|
| Where | inside one backend process, synchronous | backend → browser, over the network |
| Who listens | Python subscribers | dashboard clients |
| Delivery to UI | `EventFeed` polls `GET /api/alerts` every 5 s | pushed as it happens |
| Frontend | `services/realtime.ts` is a no-op stub | `subscribeRealtime` opens the socket |

In Phase 12 the WebSocket becomes one more subscriber on the same bus; no publisher changes.