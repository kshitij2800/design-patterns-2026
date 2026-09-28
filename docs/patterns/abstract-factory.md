# Abstract Factory Pattern — Device Family Provisioning

## Problem

The greenhouse needs coherent sets of devices per deployment environment.
A simulation kit needs sensors and actuators configured for in-process
testing (protocol `sim`). An edge kit needs the same device types but
wired for stub hardware (protocol `gpio-stub`, GPIO pin assignments).

Mixing devices from different families causes silent mismatches — a
simulation sensor paired with an edge actuator compiles and runs but
produces nonsense in production. Creating devices one at a time gives
no guarantee that the resulting set belongs together.

## Solution

The Abstract Factory pattern solves this by grouping creation of a
related product family behind one interface. A single call to
`create_device_set()` always returns a coherent, matched kit.

DeviceFamilyFactory (abstract)
├── SimulationDeviceFactory → 2 sensors (sim) + 2 actuators (sim)
└── EdgeHardwareFactory → 2 sensors (gpio-stub) + 2 actuators (gpio-stub)


`get_family_factory(family)` resolves the right factory by key.
An unknown key raises `ValueError`, which the API layer converts to
a 400 response.

## Contrast with Factory Method (Phase 2)

|           |             Factory Method                  |            Abstract Factory                 |
|-----------|---------------------------------------------|---------------------------------------------|
| Creates   | One product type                            | A family of related products.               |
| Example   | `MoistureSensorCreator` → one `Sensor`      | `SimulationDeviceFactory` → 4 `Device` objects|
| Decision  | Which sensor type                           | Which environment family |

Phase 3 composes Phase 2 creators — `SimulationDeviceFactory` calls
`MoistureSensorCreator` and `LightSensorCreator` internally, then
wraps their output into `Device` with the family tag applied.

## Where in the code

| Concern                               |                  File                                          |
|---------|----------------------------------------------------------------------------------------------|
| Abstract factory + concrete factories | `domain/devices/family_factory.py`                             |
| Unified domain entity                 | `domain/devices/entity.py`.                                    |
| Repository (persist + filter)         | `infrastructure/persistence/device_repository.py`              |
| Application service                   | `application/devices/family_service.py`                        |
| DTO + mapper                          | `application/devices/dto.py`, `application/devices/mappers.py` |
| REST API                              | `interfaces/api/devices.py`                                    |
| Frontend                              | `src/features/devices/DeviceList.tsx`                          |

## Why Device ≠ DeviceDto

`Device` is a pure domain object. It has no knowledge of HTTP, JSON,
or Pydantic. The factory and repository work exclusively with `Device`
so domain logic stays testable without starting a server.

`DeviceDto` is a Pydantic model that lives in the application layer.
The mapper (`device_to_dto`) converts `Device` → `DeviceDto` once,
at the API boundary. This means the domain can change its internals
without breaking the HTTP contract, and vice versa.

## Extension exercise — adding a third family

To add a `cloud` family:

1. Add `CloudDeviceFactory` in `family_factory.py` implementing
   `DeviceFamilyFactory` with `family_key = "cloud"` and
   `create_device_set()` returning devices with `protocol: "mqtt"`.
2. Register it in `_FACTORIES` in `get_family_factory`.
3. Add `"cloud"` to the `DeviceFamily` union type in `services/api.ts`.
4. Add the button in `DeviceFamilySwitcher.tsx`.

No other files need to change — the router, repository, service, and
mapper all handle any family key generically.