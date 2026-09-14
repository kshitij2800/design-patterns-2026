# Factory Method Pattern — Sensor Creation

## Problem
The greenhouse system needs to create different sensor types (moisture, light, and future types).
Without a pattern, every caller (HTTP handler, test, CLI) would need to know the exact constructor
arguments and default configuration for each type — and adding a new type would mean updating every
caller.

## Solution
The Factory Method pattern defines an abstract `SensorCreator` interface with a single
`create_sensor()` method. Each concrete creator (e.g. `MoistureSensorCreator`) encapsulates
the device type and its default configuration. Callers depend only on the abstract interface
and use a registry (`get_creator(type_key)`) to get the right creator.

## Where to look in the code
- `src/domain/sensors/entity.py` — the `Sensor` dataclass (pure Python, no framework deps)
- `src/domain/sensors/creators.py` — `SensorCreator` ABC, concrete creators, and registry
- `src/application/sensors/service.py` — calls `get_creator()`, never imports concrete types
- `src/interfaces/api/sensors.py` — HTTP layer passes `type` string to service only

## Extension exercise
Add a `TemperatureSensorCreator` that produces:
- `device_type = "temperature_sensor"`
- `default_config = {"unit": "celsius", "sampling_interval_seconds": 120, "min_temp_celsius": 10}`

Then register it under the key `"temperature"` in `_REGISTRY` and verify that
`POST /api/sensors` with `{"type": "temperature"}` returns a 201 with the correct config.
