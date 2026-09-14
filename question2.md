## A. Pattern

1. State the intent of Factory Method in plain language. What problem appears when callers scatter `new` / constructors (or a growing `if type == ...`) across the application?

Factory Method gives you one place to create objects instead of scattering constructors everywhere. Without it, every caller needs to know how to build each type, and adding a new type means hunting down every `if type == ...` across the codebase.

2. Name the main participants of Factory Method (**product**, **concrete product**, **creator**, **concrete creator**, **client**). For each, give one sentence: what it is responsible for.

- **Product** - the shared type all created objects conform to (`Sensor`)
- **Concrete Product** - a specific variant with its own data (e.g. a moisture sensor with its defaults)
- **Creator** - the abstract interface that declares `create_sensor()`
- **Concrete Creator** - implements `create_sensor()` and decides the type and config
- **Client** - calls the creator without knowing which concrete class it gets back

3. How do you add a **new product variant** when creators are polymorphic (new class + registry entry) versus when creation lives in one shared `if/elif` function? Why does that difference matter for extension?

With polymorphic creators you add one new class and one registry entry and nothing else changes. With `if/elif` you reopen and edit the same function every time, risking breakage. The first approach lets you extend without modifying existing code.

## B. This phase of the application

4. In this lab, what is the **product** and what are the **concrete creators**? Why must the API handler (or sensor service) go through a creator/registry instead of constructing `MoistureSensor` / `LightSensor` itself?

The product is `Sensor`. The concrete creators are `MoistureSensorCreator` and `LightSensorCreator`. The handler must go through the registry so it never owns construction details, meaning adding a new type requires zero changes to the router.

5. `POST /api/sensors` accepts a short `type` key such as `"moisture"` or `"light"`, while the stored/returned field is `device_type` (for example `moisture_sensor`). Why are those two fields different? Who decides the stored `device_type` and `default_config`?

`"moisture"` is a short API-friendly key. `"moisture_sensor"` is the internal stored value. The concrete creator decides both the `device_type` and `default_config`, and the router just passes the key along.


6. Why is there a single `devices` table with `role="sensor"` instead of a dedicated `sensors` table? What later phase does that choice prepare for?

One table with `role="sensor"` means Phase 3 actuators can be added as `role="actuator"` with no schema change. It directly prepares for Abstract Factory, which bundles sensors and actuators as a device family.


7. What should happen when the client posts an **unknown** `type`? Where should that rejection be decided (registry/service vs router constructing a concrete class anyway)?

The registry raises a `ValueError` for unknown types and the service converts it to a 400. Rejection belongs in the registry/service and not the router, so the router never constructs anything directly.


## C. Compare, contrast, and scenarios

8. Contrast Factory Method with a **simple factory** (one function full of `if type == ...`). When is the simple factory “good enough,” and why does this phase still want polymorphic creators?

A simple factory is fine for two or three stable types in a small project. This phase uses polymorphic creators because sensor types will grow across phases, and each new type should be addable without touching existing code.


9. Contrast Factory Method with **Abstract Factory** (Phase 3). Factory Method answers which question? Abstract Factory answers which different question? Why is Factory Method enough for Phase 2 sensors?

Factory Method answers: how do I create one object without the caller knowing the class? Abstract Factory answers: how do I create a matched family of related objects? Phase 2 only needs individual sensors so Factory Method is enough. Phase 3 needs bundled device families, which is where Abstract Factory comes in.


10. A classmate puts SQLAlchemy session commits (or FastAPI request parsing) **inside** a concrete creator. Why is that a trap? Where should persistence and HTTP stay instead?

Creators live in the domain layer which must have no framework dependencies. Putting a session commit or request parsing inside a creator makes it untestable without a database and unusable outside FastAPI. Persistence stays in the repository and HTTP stays in the router.