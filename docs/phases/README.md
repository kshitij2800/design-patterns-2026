# Phases

## Phase 1 — Skeleton 
Three-tier project setup: FastAPI backend, PostgreSQL with Alembic migrations, React + TypeScript frontend.

## Phase 2 — Factory Method
Adds `devices` table, sensor creators, `/api/sensors` endpoint, and fills the Sensors dashboard section.

## Phase 3 — Abstract Factory
Provisions coherent simulation and edge device kits (sensors + actuators) via family factories, adds `device_family` column, `/api/devices` endpoints, and a dashboard Devices section.

## Phase 4 — Builder 
Assembles a validated location configuration (location name plus one or more zones with VWC moisture thresholds and a schedule) via `LocationConfigBuilder`, and saves it transactionally to new `locations` and `zones` tables. Adds nullable `zone_id` and `location_id` columns to `devices`, a separate zone-assignment service, and `/api/locations` endpoints for creating, listing, reading and deleting locations, managing zones, and listing the devices in a zone, plus `PATCH /api/devices/{id}/zone`. Fills the dashboard Configuration section and adds a zone picker to each device card.

## Phase 5 — Adapter 
Reads sensors through a `SensorPort` with three adapters (simulation, vendor stub, MQTT payload translator) and adds an `ActuatorPort` with a simulation adapter. Every reading is stored in a new `sensor_readings` table through one ingest path (`ReadingIngest`). Adds `sampling_interval_seconds` and `tracking_enabled` columns to `devices`, a background simulation sampler, `POST /api/sensors/{id}/read`, `GET /api/sensors/{id}/readings` and `PATCH /api/devices/{id}/sampling`, and sensor cards with "Read now", a source badge and sampling controls.

## Phase 6 — Strategy 
Adds pluggable irrigation strategies behind one `AutomationStrategy.decide(context)` interface, with `ConservativeMoistureStrategy` (irrigates below the zone's low threshold) and `AggressiveMoistureStrategy` (irrigates below the middle of the band). The active `strategy_key` is stored per location in a new `automation_rules` table (unique `location_id`). Adds `PUT /api/locations/{id}/automation` and `POST /api/locations/{id}/automation/evaluate`, which evaluates each zone using its thresholds from `zones` and the latest moisture reading from sensors assigned to that zone, and returns a recommendation (`irrigate` or `wait`) with a reason. Fills the dashboard Automation section with a strategy panel for saving a strategy and evaluating it.

## Phase 7 — Facade 
Adds `LocationOverviewFacade.get_overview(location_id)`, one entry point that combines the location and its zones, the devices assigned to those zones, the newest reading per assigned device (any source) and the saved strategy into one `LocationOverviewDto`. When a strategy key is saved, `last_recommendation` is computed on each request by the existing automation evaluate service; it is never stored. Adds `GET /api/locations/{id}/overview` (the handler's only collaborator is the facade) and fills the dashboard Overview section with count, strategy, recommendation and per-zone cards from that one response. No new table.

## Phase 8 — State 
Adds a persisted actuator lifecycle behind `ActuatorContext`, which guards every transition against a domain transition table (`off`, `idle`, `running`, `error`, `maintenance`) rather than letting routers or React encode `if state == ...` rules. State is stored per actuator in a new `actuator_states` table (seeded to `idle` for existing actuators), not kept only in process memory — confirmed by surviving a backend restart. `GET /api/devices` gains `state` and `allowed_commands` per actuator, and `POST /api/devices/{id}/transition` applies a guarded transition (404 missing actuator, 409 illegal transition — nothing is written on rejection). Adds color-coded state badges to actuator cards on the dashboard, with `allowed_commands` shown as a tooltip. Sets up Phase 10 (Command), which will consult the same `allowed_commands`/state guard before executing a command.


## Phase 9 — Decorator (current)
Wraps `ActuatorPort` in two decorators — `LoggingActuatorDecorator` (outermost, always writes a row) and `MaxRunTimeActuatorDecorator` (rejects `apply()` when the actuator has been `running` for 30+ minutes per `actuator_states.updated_at`, and never calls the inner component when it blocks) — composed in front of the Phase 5 `SimulationActuatorAdapter`. Every attempt is persisted to a new `actuator_execution_log` table (`success`, `policy_applied`, `message`, `created_at`); a blocked attempt is visible as `success=false` with `policy_applied: ["maxRunTime", "logging"]` and the message `Max run time exceeded`. Adds `GET /api/actuators/executions` and a demo `POST /api/actuators/{id}/apply` route (Phase 10 replaces the demo route with the real command endpoint), plus an Execution Log table on the dashboard.