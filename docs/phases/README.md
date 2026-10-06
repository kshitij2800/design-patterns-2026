# Phases

## Phase 1 — Skeleton 
Three-tier project setup: FastAPI backend, PostgreSQL with Alembic migrations, React + TypeScript frontend.

## Phase 2 — Factory Method
Adds `devices` table, sensor creators, `/api/sensors` endpoint, and fills the Sensors dashboard section.

## Phase 3 — Abstract Factory
Provisions coherent simulation and edge device kits (sensors + actuators) via family factories, adds `device_family` column, `/api/devices` endpoints, and a dashboard Devices section.

## Phase 4 — Builder 
Assembles a validated location configuration (location name plus one or more zones with VWC moisture thresholds and a schedule) via `LocationConfigBuilder`, and saves it transactionally to new `locations` and `zones` tables. Adds nullable `zone_id` and `location_id` columns to `devices`, a separate zone-assignment service, and `/api/locations` endpoints for creating, listing, reading and deleting locations, managing zones, and listing the devices in a zone, plus `PATCH /api/devices/{id}/zone`. Fills the dashboard Configuration section and adds a zone picker to each device card.



## Phase 5 — Adapter (current)
Reads sensors through a `SensorPort` with three adapters (simulation, vendor stub, MQTT payload translator) and adds an `ActuatorPort` with a simulation adapter. Every reading is stored in a new `sensor_readings` table through one ingest path (`ReadingIngest`). Adds `sampling_interval_seconds` and `tracking_enabled` columns to `devices`, a background simulation sampler, `POST /api/sensors/{id}/read`, `GET /api/sensors/{id}/readings` and `PATCH /api/devices/{id}/sampling`, and sensor cards with "Read now", a source badge and sampling controls.