# Builder Pattern — Location Configuration (Phase 4)

## Intent in this project

A location configuration is a location name plus one or more zones. Each zone has a
name, a low and high moisture threshold (VWC, 0.0–1.0), and a schedule. The object is
only valid as a whole: a location with no zones, or a zone whose low threshold is not
below its high threshold, must never reach the database.

`LocationConfigBuilder` lets the caller assemble this step by step and then asks for the
finished result in one place:

```python
config = (
    LocationConfigBuilder()
    .with_location_name("Lab Site A")
    .add_zone("Bench 1", 0.2, 0.45, {"watering": "08:00"})
    .add_zone("Bench 2", 0.1, 0.30)
    .build()
)
```

`build()` either returns an immutable `LocationConfig` (frozen dataclasses, no ids yet)
or raises `ConfigurationError`. Only a successfully built config is passed to
`LocationRepository.save_config`, which writes the location and all its zones in one
transaction.

| Role | File |
|------|------|
| Builder | `backend/src/domain/locations/config_builder.py` |
| Product | `backend/src/domain/locations/entity.py` (`LocationConfig`, `Location`, `Zone`) |
| Validation rules | `backend/src/domain/locations/validation.py` |
| Error | `backend/src/domain/locations/errors.py` (`ConfigurationError`) |
| Director / client | `backend/src/application/locations/config_service.py` (`build_and_save`) |

## Why Builder, not Factory Method or Abstract Factory

- **Factory Method** (Phase 2) lets a subclass decide *which class* to instantiate — for
  example, which sensor type to create. The product is created in one call and there is
  no multi-step assembly.
- **Abstract Factory** (Phase 3) creates *families of related objects* that must match —
  a simulation kit or an edge kit of devices. It answers "which family?", not "how is one
  complex object assembled?".
- **Builder** solves a different problem: one complex product whose parts are added
  incrementally (a variable number of zones) and which must be validated as a whole
  before it exists. The number and content of the parts comes from the user, and the
  product is only meaningful once `build()` has checked every rule together (for
  example, zone names must be unique *within* the location, which cannot be checked by
  looking at one zone alone).

## Where validation lives

Business rules live in the **domain layer**, not in the API:

- `build()` checks that the location name is non-empty, that there is at least one zone,
  and that zone names are unique within the location (case-insensitive).
- `validate_zone_fields()` in `validation.py` checks each zone: a non-empty name,
  thresholds within 0.0–1.0, and low strictly less than high.

The same `validate_zone_fields()` is reused by `ZoneManagementService` when a zone is
added to or edited on a saved location, so the rules are identical whether a zone comes
through the builder or through the zone endpoints — without calling the builder.

The API layer only checks JSON *shape* (Pydantic DTOs) and converts `ConfigurationError`
into HTTP 400. Invalid input is rejected before any database write.

## Why `location_id` naming

The product context is a smart greenhouse, but the relational resource is a **location**:
one installation may contain several physical sites (a lab bench, a greenhouse, a
growing room). Using `locations` / `location_id` keeps the schema general and consistent
across phases:

- `zones.location_id` → `locations.id` (`ON DELETE CASCADE`)
- `devices.location_id` → `locations.id` (`ON DELETE SET NULL`)
- API paths use `/api/locations/{location_id}/...`

No table, column, DTO, or endpoint uses `greenhouse_id`.

## Why device assignment is not a builder method

The builder has **no** `add_device` method, deliberately:

1. **Zones have no id until saved.** A device is linked by `devices.zone_id`, which must
   reference an existing `zones.id`. Inside the builder, nothing has been saved yet.
2. **Devices already exist.** They were provisioned in Phases 2–3. Assigning one is an
   update to an existing row, not part of constructing a new location.
3. **Assignment changes independently.** Moving a device between zones must not rebuild
   the location. `ZoneAssignmentService` handles it separately: it sets `zone_id` and
   copies `location_id` from the zone in the same write, and clears both on unassign.
   The client never sends `location_id`, so it cannot disagree with the zone.

For the same reason, listing and deleting locations, and adding, editing, or deleting a
zone on a saved location, are separate operations that never call `build()`.

## Related behaviour

- `GET /api/locations` returns locations **newest first**.
- Deleting a location removes its zones and leaves its devices unassigned
  (`zone_id` and `location_id` null).
- Deleting a zone clears `zone_id` and `location_id` on its devices first, because
  `ON DELETE SET NULL` would only clear `zone_id`. The last zone of a location cannot be
  deleted (400).

## Extension idea

A `LocationConfigDirector` could hold presets such as "standard 3-bench greenhouse",
calling the same builder steps with fixed values. Future per-zone settings (for example
temperature limits) would be new optional builder steps, validated in `build()`, without
changing how existing callers use the builder.