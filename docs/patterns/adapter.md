# Adapter Pattern — Sensor Readings (Phase 5)

## Problem: incompatible interfaces

Every source of sensor data speaks its own language:

| Source | What it gives us |
|--------|------------------|
| Simulation (in code) | A random float we generate ourselves |
| Vendor SDK (stub "Acme") | `{"channel": "SOIL", "reading_x100": 4100, "uom": "PCT_VWC", "epoch_ms": 1759…}` — integers ×100, moisture as a **percent**, time in **epoch ms** |
| MQTT / ESP32 (Phase 12) | `{"value": 0.41, "unit": "vwc"}` pushed by the device |

If the application read these shapes directly, every service and router would fill up
with `if vendor == …` branches, and adding hardware would mean editing business code.

## Solution: one port, many adapters

The application only knows one interface (the **port**) and one data shape (`Reading`).
Each **adapter** converts one foreign interface into that port.

```text
                ┌──────────────── domain ────────────────┐
ReadingIngest → │ SensorPort.read(device) -> Reading      │
                └─────────────────────────────────────────┘
                     ▲                     ▲
   SimulationSensorAdapter     VendorStubSensorAdapter      MqttSensorAdapter.translate(payload)
   (generates value)           (translates Acme payload)    (translates pushed dict; no broker)
```

`Reading(device_id, value, unit, source, recorded_at)` is the unified shape. `source`
records which adapter produced it: `simulation`, `vendor` or `mqtt`.

The same idea is used for actuators: `ActuatorPort.apply(device_id, command, payload)`
with `SimulationActuatorAdapter`, which only records the command in memory and logs it
(no GPIO). Phase 9 decorators will wrap this port.

## Where in code

| Role | File |
|------|------|
| Target (port) | `backend/src/domain/sensors/ports.py` — `SensorPort` |
| Unified type | `backend/src/domain/sensors/reading.py` — `Reading` |
| Adapters | `backend/src/infrastructure/adapters/sensors/simulation.py`, `vendor_stub.py`, `mqtt.py` |
| Adaptee (fake vendor SDK) | `FakeAcmeClient` in `vendor_stub.py` |
| Selector (only place that names adapter classes) | `backend/src/infrastructure/adapters/sensors/selector.py` |
| Client | `backend/src/application/readings/service.py` — `ReadingIngest` (receives the selector, depends only on `SensorPort`) |
| Actuator port / adapter | `backend/src/domain/actuators/ports.py`, `backend/src/infrastructure/adapters/actuators/simulation.py` |

### Selection rule

1. `default_config.adapter == "vendor_stub"` → `VendorStubSensorAdapter` (checked first, so it never collides with `protocol`)
2. `default_config.protocol == "simulation"` (or no protocol) → `SimulationSensorAdapter`
3. `default_config.protocol == "mqtt"` → no on-demand read (400). MQTT devices push data; the payload goes through `MqttSensorAdapter.translate` and then `ReadingIngest.record`.

The Phase 5 migration renamed the Phase 3 protocol values: `sim` → `simulation`, `gpio-stub` → `mqtt`.

## One write path

`ReadingIngest.record` is the only code that inserts into `sensor_readings`.
`POST /api/sensors/{id}/read`, the `SimulationSampler` (every few seconds, only
`protocol=simulation` sensors with `tracking_enabled`, and only when
`sampling_interval_seconds` has passed since the last row) and, from Phase 12, MQTT/HTTP
ingest all go through it.

## Why Adapter (and not the earlier patterns)

Factory Method, Abstract Factory and Builder are about **creating** objects. Adapter is
structural: the objects already exist (a vendor SDK, a device payload) and have the wrong
interface. The adapter **translates**; it does not decide irrigation policy or state —
that stays in the application/domain (Phase 6 Strategy).

## Extension: adding a third vendor

1. Write `infrastructure/adapters/sensors/<vendor>.py` with a class implementing `SensorPort`
   that calls the vendor SDK and maps its payload to `Reading`.
2. Add one rule to `selector.py` (e.g. `default_config.adapter == "<vendor>"`).
3. Add a unit test that feeds a raw vendor payload and checks the normalized fields.

No change is needed in `ReadingIngest`, the sampler, the API, the database or the frontend.