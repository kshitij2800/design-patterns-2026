# Strategy Pattern — Irrigation Automation (Phase 6)

## Problem

The decision "should this zone be irrigated?" can follow different policies. Putting
`if strategy == "conservative": ... elif ...` in the API handler would tie the router to
every algorithm, and each new policy would mean editing it.

## Solution: one interface, interchangeable algorithms

```text
AutomationService ──► get_strategy(key) ──► AutomationStrategy.decide(context) -> Recommendation
                                              ▲                      ▲
                                ConservativeMoistureStrategy   AggressiveMoistureStrategy
```

- `decide(context)` is the only method callers use.
- `LocationAutomationContext` is plain Python: zone id, latest moisture, zone low/high
  thresholds, optional light. Strategies never see ORM rows.
- `Recommendation(action, reason, score)` is the result.
- `get_strategy(key)` is the single lookup. An unknown key raises `UnknownStrategyError`
  before `decide()` is ever called (the API turns it into a 400).

## The two strategies

| Strategy | Irrigates when | Example: band 0.25–0.45, moisture 0.30 |
|----------|----------------|-----------------------------------------|
| conservative | moisture < `low` | wait |
| aggressive | moisture < midpoint `(low + high) / 2` | irrigate (0.30 < 0.35) |

## Persistence

Table `automation_rules` (chosen over extra columns on `locations`, so strategy settings
and their `parameters` can grow without widening `locations`): `location_id` is UNIQUE, so
each location has one active `strategy_key`. `PUT /api/locations/{id}/automation` upserts
the row. A location with no row uses the default `conservative`.

## How a zone is evaluated

For each zone in the location, thresholds come from `zones` and moisture is the latest
`sensor_readings` row among sensors whose `devices.zone_id` is that zone. The reading may
come from a manual read, the simulation sampler, or a translated MQTT payload; the strategy
does not care. A zone with no reading never borrows another device's value. It gets `wait`
("no moisture reading for this zone") and the strategy is not called. The location-level
`action` is `irrigate` if any zone needs it, and per-zone results are in `zones`.

## Where in code

| Role | File |
|------|------|
| Strategy interface, concrete strategies, lookup | `backend/src/domain/automation/strategy.py` |
| Context | `backend/src/domain/automation/context.py` |
| Orchestration | `backend/src/application/automation/service.py` |
| Persistence and context assembly | `backend/src/infrastructure/persistence/automation_repository.py` |
| API | `backend/src/interfaces/api/automation.py` |
| UI | `frontend/src/features/automation/StrategyPanel.tsx` |

## Exercise: add a third strategy

1. Add a class with a `key` and a `decide(context)` method in `strategy.py`.
2. Add an instance to `_STRATEGIES`.
3. Add its key to `STRATEGY_KEYS` in `frontend/src/services/api.ts`.
4. Add a unit test with a fake context.

The router, service, repository and database need no change.