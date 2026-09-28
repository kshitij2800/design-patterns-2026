# Phases

## Phase 1 — Skeleton (current)
Three-tier project setup: FastAPI backend, PostgreSQL with Alembic migrations, React + TypeScript frontend.

## Phase 2 — Factory Method
Adds `devices` table, sensor creators, `/api/sensors` endpoint, and fills the Sensors dashboard section.

## Phase 3 — Abstract Factory
Provisions coherent simulation and edge device kits (sensors + actuators) via family factories, adds `device_family` column, `/api/devices` endpoints, and a dashboard Devices section.