# Facade Pattern — Location Overview (Phase 7)

## Problem: one screen, many subsystems

The dashboard Overview needs a snapshot of one location. That snapshot lives in
several places that earlier phases built separately:

| Subsystem | Where it lives | Phase |
|-----------|----------------|-------|
| Location and its zones (thresholds) | `locations`, `zones` via `LocationRepository` | 4 |
| Devices assigned to those zones | `devices` via `DeviceRepository` | 2–4 |
| Newest reading per device | `sensor_readings` via `ReadingRepository` | 5 |
| Saved strategy + recommendation | `automation_rules` via `AutomationRepository` and `AutomationService.evaluate` | 6 |

Without a facade, either the router would depend on four repositories and a service,
or React would call four endpoints and stitch the answers together. Both spread the
"what is an overview" knowledge across the outer layers.

## Solution: one entry point

`LocationOverviewFacade.get_overview(location_id)` is the single entry point. It
coordinates the subsystems above and returns one read model, `LocationOverviewDto`.

```text
OverviewPanel (React) ── GET /api/locations/{id}/overview ──► overview router
                                                                 │ (only collaborator)
                                                                 ▼
                                                    LocationOverviewFacade
                                ┌──────────────┬──────────────┼───────────────┬─────────────────────┐
                                ▼              ▼              ▼               ▼                     ▼
                     LocationRepository  DeviceRepository  ReadingRepository  AutomationRepository  AutomationService.evaluate
```

The facade adds no business rules of its own. It does not re-implement the Strategy
`decide()` or the Adapter translation; it only asks the existing subsystems and
assembles the answer.

## Where in code

| Role | File |
|------|------|
| Facade | `backend/src/application/overview/facade.py` — `LocationOverviewFacade` |
| Read model | `backend/src/application/overview/dto.py` — `LocationOverviewDto` |
| Client (HTTP) | `backend/src/interfaces/api/overview.py` — injects only the facade |
| Client (UI) | `frontend/src/components/overview/OverviewPanel.tsx` — one `fetchOverview` call |
| New queries | `DeviceRepository.list_assigned_in_location`, `ReadingRepository.latest_for_devices` |

`LocationOverviewFacade.from_session(session)` wires the subsystems, so the router
imports no repository.

## Recommendation is computed, not cached

`last_recommendation` is produced on every GET by calling the existing
`AutomationService.evaluate(location_id)`, which runs the saved strategy's `decide()`.
It is not stored in a table, so it always reflects the latest readings and the
currently saved key. When no key is saved, the facade does not call `evaluate` at all
and returns `strategy_key: null` and `last_recommendation: null` with HTTP 200.

## Query shape

1. Location + its zones — `LocationRepository.get_config` (location row, zones loaded with `selectinload`).
2. Assigned devices — one query: `location_id = ?` AND `zone_id IS NOT NULL`.
3. Newest reading for those device ids — one query with `ROW_NUMBER() OVER (PARTITION BY device_id ORDER BY recorded_at DESC)`, keeping row 1. It uses the Phase 5 `(device_id, recorded_at DESC)` index and does not filter by `source`, so manual reads, sampler rows and MQTT rows all count.
4. Saved strategy key — one query on `automation_rules`.
5. Only when a key exists: `AutomationService.evaluate`. Evaluate still looks up the latest moisture (and light) once per zone. That lookup stays inside the automation service on purpose: avoiding it would mean re-implementing `decide()` in the facade.

The number of reading queries the facade itself makes does not grow with the number of
devices (`test_overview_reading_query_count_does_not_grow_with_devices`).

## No new table

Phase 7 adds no migration. The existing tables from Phases 2–6 are enough; the
optional `location_overview_v1` view was not needed.

## Facade vs Adapter

Both wrap other code. An Adapter (Phase 5) changes **one** foreign interface into the
interface we expect. A Facade gives a **simpler** interface over **several** of our own
subsystems that already work; nothing is translated, only coordinated.