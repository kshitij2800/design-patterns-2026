## A. Pattern

1. State the intent of Abstract Factory in plain language. What goes wrong when related products are chosen independently (`if format` for each piece) instead of as a **family**?

> [!NOTE]
> ***Your Answer***
>
> Abstract Factory provides an interface for creating a group of related objects together, without specifying their concrete classes. When products are chosen independently using `if/else` logic per piece, you can accidentally mix incompatible siblings — for example a simulation sensor paired with an edge actuator. The code compiles and runs but the combination is logically wrong. The factory solves this by making one decision (which family) that commits all products to a coherent set.

2. Name the main participants (**abstract factory**, **concrete factory**, **abstract products**, **concrete products**, **client**). How does choosing a factory at the start **commit** the client to one family?

> [!NOTE]
> ***Your Answer***
>
> The **abstract factory** is `DeviceFamilyFactory` — it declares `create_device_set()`. The **concrete factories** are `SimulationDeviceFactory` and `EdgeHardwareFactory` — they implement it. The **abstract product** is `Device` — the unified domain entity. The **concrete products** are the actual `Device` instances each factory builds (sim pump, edge pump, etc.). The **client** is `DeviceFamilyService`, which calls `get_family_factory(family)` once and then calls `create_device_set()` — from that point it never checks the family again. Because the client only talks to the abstract interface, every object it receives is guaranteed to belong to the same family.

3. When should you use Abstract Factory, and when should you skip it (for example only one product type per request, or mixing siblings is valid)?

> [!NOTE]
> ***Your Answer***
>
> Use Abstract Factory when you need to enforce that a set of related objects always come from the same family — multiple product types that must be compatible with each other, and where swapping families is a valid runtime decision. Skip it when you only ever create one product type per request (Factory Method is enough), when there is only one family now and no realistic plan for a second, or when mixing products from different families is actually valid for your domain. Over-applying it adds layers of abstraction that cost more than they save.

## B. This phase of the application

4. In this lab, what is a **device family**, and what does `create_device_set()` return? Why must a simulation kit and an edge kit not mix incompatible siblings?

> [!NOTE]
> ***Your Answer***
>
> A device family is a named deployment environment — `simulation` for in-process dev/test, `edge` for stub hardware. `create_device_set()` returns a list of four `Device` objects: two sensors (moisture, light) and two actuators (water pump, grow light), all tagged with the same `device_family`. A simulation kit uses `protocol: "sim"`; an edge kit uses `protocol: "gpio-stub"` with GPIO pin assignments. Mixing them would mean an edge actuator trying to receive commands formatted for simulation, or a sim sensor reporting to a real GPIO handler — a mismatch that would fail silently at runtime rather than at construction time.

5. Phase 2 Factory Method creators still exist. How does Abstract Factory **compose** them rather than replace them? What would you lose if you deleted the sensor creators and inlined all construction inside the family factory?

> [!NOTE]
> ***Your Answer***
>
> `SimulationDeviceFactory.create_device_set()` calls `MoistureSensorCreator().create_sensor()` and `LightSensorCreator().create_sensor()` internally, then wraps their output into `Device` objects with the family tag added. The creators still own the sensor-specific defaults — sampling intervals, thresholds, units. If you deleted the creators and inlined everything, you would duplicate those defaults in every concrete family factory. Adding a third family or changing a sensor default would require editing multiple places. You would also break Phase 2's `/api/sensors` endpoint and its tests, which depend on the creators directly.

6. Why add a `device_family` column on the existing `devices` table (with a default/backfill such as `"simulation"`) instead of a new table per family? What happens to Phase 2 sensor rows if you forget the backfill?

> [!NOTE]
> ***Your Answer***
>
> All devices — regardless of family — share the same structure: id, type, role, family, display name, config. A separate table per family would duplicate that structure, complicate every query that needs to list or filter across families, and require schema changes every time a new family is added. Adding a `device_family` column to the existing table keeps everything in one place and lets you filter with a simple `WHERE device_family = ?`. If you forget the backfill or server default, Phase 2 sensor rows get a `NULL` in a `NOT NULL` column, which causes the migration to fail or existing rows to become unreadable when the repository tries to map them to a `Device`.

7. `POST /api/devices/provision` returns a kit (expected size: two sensors and two actuators). `GET /api/devices` can filter by `family` and `role`. Why must the UI be able to filter by family? Why do `/api/sensors` routes from Phase 2 still need to work?

> [!NOTE]
> ***Your Answer***
>
> Without a family filter, the device list mixes simulation and edge devices together, making it impossible for the user to see only the kit they provisioned for their current environment. The family switcher in the UI only makes sense if the list request passes the selected family — otherwise switching has no visible effect. The Phase 2 `/api/sensors` routes must keep working because they are part of an already-delivered interface: the Sensors dashboard section depends on them, existing tests cover them, and breaking a working endpoint to satisfy a new feature is a regression. Phase 3 extends the system; it does not replace what Phase 2 delivered.

## C. Compare, contrast, and scenarios

8. Draw the contrast in one paragraph: Factory Method vs Abstract Factory. Use the questions "which **one** product?" versus "which product **line**?" and mention that Abstract Factory often **uses** Factory Method–style methods inside.

> [!NOTE]
> ***Your Answer***
>
> Factory Method answers the question "which **one** product should I create for this type?" — it defines a single creator interface and lets subclasses decide which concrete product to return. In Phase 2, `MoistureSensorCreator` and `LightSensorCreator` each produce one `Sensor`. Abstract Factory answers a different question: "which product **line** should I provision for this environment?" — it groups the creation of several related products behind one interface so the entire set is guaranteed to be compatible. In Phase 3, `SimulationDeviceFactory.create_device_set()` returns sensors and actuators together. Importantly, Abstract Factory does not make Factory Method obsolete — it often **uses** Factory Method-style creation methods internally, as our concrete family factories do when they call the Phase 2 sensor creators to build the sensor half of each kit.

9. A DTO or HTTP handler constructs concrete simulation/edge device types directly, bypassing the family factory. What consistency bug can that reintroduce? How should HTTP stay on the abstract factory / service instead?

> [!NOTE]
> ***Your Answer***
>
> If a router handler builds devices with hardcoded `device_family` strings or selects sensor and actuator types independently with `if family == "simulation"` branches, it reintroduces exactly the mixing problem Abstract Factory was designed to prevent. One developer adds a new actuator to the simulation factory but forgets the matching branch in the router; now the provisioned kit is half-correct. The HTTP layer should stay thin — receive the `family` query parameter, pass it to `DeviceFamilyService.provision_family()`, and return the DTOs. All family-specific construction logic belongs in the factory, and the router should never know which concrete devices belong to which family.

10. Someone proposes a single "god factory" that creates locations, readings, and devices "because we already have a factory." Why is that a misuse of Abstract Factory?

> [!NOTE]
> ***Your Answer***
>
> Abstract Factory is designed for creating **families of related products** — objects that must be compatible with each other and belong to the same variant. Locations, readings, and devices are not siblings in a family; they are independent domain concepts with no compatibility constraint between them. Grouping their creation into one factory does not enforce any useful invariant — it just concentrates unrelated construction logic in one place. The result is a class with too many responsibilities that changes for too many reasons, making it harder to test, extend, and understand. The pattern should be applied where family coherence is the actual problem, not as a general-purpose object-creation hub.