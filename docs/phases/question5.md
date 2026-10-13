## A. Pattern

1. State the intent of Adapter in plain language. What problem appears when business code speaks a vendor or legacy protocol (odd field names, units, XML, status codes) directly?

> [!NOTE]
> ***Your Answer***
>
> Adapter converts an interface we cannot change into the interface our code expects, so two incompatible pieces can work together. If business code talked to a vendor directly, it would have to know the vendor's field names, units and formats everywhere. For example, my vendor stub sends `reading_x100` as a whole number, moisture as a percent (`PCT_VWC`) and time as epoch milliseconds. That knowledge would spread through services and routers, every new device would mean editing business code, and changing vendors would break things in many places. With an adapter, that translation happens in one place.

2. Name the participants (**target / port**, **adaptee**, **adapter**, **client**). What does the adapter translate, and what must it **not** decide (business policy)?

> [!NOTE]
> ***Your Answer***
>
> - **Target / port:** `SensorPort`, with `read(device) -> Reading`. It is the interface the application wants.
> - **Adaptee:** the thing with the wrong interface. In my project that is `FakeAcmeClient` (the vendor stub), the simulation generator, or an MQTT payload dict.
> - **Adapter:** `SimulationSensorAdapter`, `VendorStubSensorAdapter` and `MqttSensorAdapter`. Each turns its adaptee's output into a `Reading`.
> - **Client:** `ReadingIngest` (and `SimulationSampler`), which only call the port.
>
> The adapter translates data shape, units, field names and timestamps. For example, `4100` with `PCT_VWC` becomes `0.41` `vwc`. It must **not** decide business rules such as "is the soil too dry?", "should we water?", or whether a device should be sampled. Those decisions belong in the application and domain layers.

3. GoF distinguishes an **object adapter** (composition) from a **class adapter** (inheritance). Which does modern code prefer, and why?

> [!NOTE]
> ***Your Answer***
>
> Modern code prefers the **object adapter**. The adapter holds the adaptee as a field and calls it, instead of inheriting from it. My `VendorStubSensorAdapter` does this: it receives a `FakeAcmeClient` in its constructor. Composition is looser than inheritance. The adapter doesn't expose all of the adaptee's methods. You can pass in a fake client for tests. It still works when the adaptee comes from a library you can't subclass. And it avoids multiple inheritance, which many languages don't support or make messy.

## B. This phase of the application

4. What is `SensorPort` in this lab, and what normalized value type (for example `Reading`) do adapters return? Why do application services depend on the port rather than on a simulation driver or vendor SDK?

> [!NOTE]
> ***Your Answer***
>
> `SensorPort` is an abstract class in the domain layer (`domain/sensors/ports.py`) with one method, `read(device) -> Reading`. `Reading` is a small frozen dataclass with `device_id`, `value`, `unit`, `source` and `recorded_at`. Every adapter returns this same shape.
>
> `ReadingIngest` depends only on the port. It receives a selector function that returns a `SensorPort` and never imports an adapter class. That means I can add a new device type, or swap the simulation for real hardware, without touching the service, the API or the database. It also keeps the domain and application layers free of vendor code, and it makes testing easy, because a test can pass in any adapter.

5. You need three translations onto the same normalized reading: a simulation adapter, a vendor stub, and an MQTT translator that accepts a payload dict. Why is the different raw shape the point of the exercise? How does `source` (`simulation`, `vendor`, or `mqtt`) show which adapter produced the reading, and why must the MQTT translator not open a broker in this phase? Phase 12 may deliver that same dict on a device HTTP route or through an optional broker — why must this phase still not open either transport?

> [!NOTE]
> ***Your Answer***
>
> The point of Adapter is translation. If all three sources already gave the same shape, there would be nothing to adapt. The vendor stub deliberately uses a different shape (`reading_x100`, `uom: PCT_VWC`, `epoch_ms`), so its adapter has real conversion work to do: scaling, percent to fraction, and epoch to datetime. All three still end up as the same `Reading`.
>
> Each adapter sets `source` to its own name (`"simulation"`, `"vendor"` or `"mqtt"`). That value is stored in `sensor_readings` and shown as a badge on the sensor card, so you can always tell which adapter produced a reading.
>
> The MQTT translator only does `translate(device, payload_dict) -> Reading`. Translation and transport are separate jobs. In this phase we only build and test the translation, using a plain dict with no network; my test even blocks sockets to prove it. How the dict arrives (device HTTP or a broker) is Phase 12's job. Opening a broker or an HTTP route now would mix two responsibilities, add infrastructure we don't need yet, and make the tests depend on a running server.

6. Readings are **appended** to `sensor_readings` (history grows). Why not keep only the latest value in memory or overwrite a single row, and which later phase consumes this history? Why do a manual read, the simulation sampler, and (later) MQTT share **one** writer of that table? Why does the sampler skip devices with tracking off and MQTT devices, and why do sensor cards poll the latest stored reading until Phase 12?

> [!NOTE]
> ***Your Answer***
>
> - **Why append:** a value kept only in memory is lost when the server restarts, and overwriting one row loses the history. Appending keeps every reading with its time, so the latest value survives a page refresh and we have a history. Phase 6 (Strategy) uses the latest moisture reading for each zone to decide on irrigation, and the optional Phase 13 charts use the full history.
> - **One writer:** every path goes through `ReadingIngest.record`. That way all readings are saved the same way. Later, Phase 11 can publish a `reading.created` event from that one place, instead of in three places that could drift apart.
> - **What the sampler skips:** it skips devices with tracking off because the user switched them off. It skips MQTT devices because they push their own readings and we can't pull a value from them; only simulation devices are generated in code.
> - **Why the cards poll:** without polling, a card would only change when you click "Read now", so you wouldn't see the sampler's new rows. Polling `GET /readings?limit=1` every few seconds is a simple temporary fix. Phase 12 replaces it with a WebSocket push.

7. `POST /api/sensors/{id}/read` runs an adapter, persists, and returns a DTO. What HTTP status is appropriate when the device is missing versus when the adapter fails? Why must the router never see vendor-shaped types?

> [!NOTE]
> ***Your Answer***
>
> - **Missing device:** **404 Not Found**, because the resource doesn't exist.
> - **Adapter fails:** for example an MQTT device that can't be read on demand, or a bad vendor payload. This is **400**, with a `detail` message explaining why. The device exists, but the read couldn't be done.
> - **Success:** **201**, because a new reading row was created.
>
> The router should only know about `ReadingDto`. If vendor types reached the router, the API layer would depend on a specific vendor. Changing or adding a vendor would mean changing the API and possibly the frontend, and the Adapter pattern would be pointless. The translation has to finish inside the adapter.

## C. Compare, contrast, and scenarios

8. Contrast Adapter with **Facade**. Adapter changes the **shape** of an existing interface; Facade simplifies **how to use** a subsystem. Give a greenhouse-shaped example of each (Adapter this phase; Facade in Phase 7).

> [!NOTE]
> ***Your Answer***
>
> An Adapter wraps **one** incompatible thing and makes it look like an interface the client already expects. In this phase, `VendorStubSensorAdapter` makes the Acme vendor payload look like `SensorPort` and return a `Reading`.
>
> A Facade sits in front of **several** parts of a system and gives one simple entry point, so the client doesn't need to know all the steps. A greenhouse example for Phase 7 is a "water this zone" facade: one call that loads the zone, checks the latest moisture, picks the pump, sends the actuator command and logs the event, hiding all those classes behind one method.
>
> In short, Adapter answers "how do I make this fit?" and Facade answers "how do I make this easy to use?"

9. Contrast Adapter with **Decorator**. Both wrap an object. What is different about the interface they present to the client?

> [!NOTE]
> ***Your Answer***
>
> An Adapter presents a **different** interface from the object it wraps. It turns the adaptee's interface into the target interface; for example, the Acme client's `fetch()` becomes `SensorPort.read()`.
>
> A Decorator presents the **same** interface as the object it wraps, and adds behaviour around it. In Phase 9 a decorator will wrap `ActuatorPort` and still be an `ActuatorPort`, but add something like logging, a safety check or a retry before calling the inner `SimulationActuatorAdapter`. Decorators can be stacked because the interface never changes. An adapter is used to change the interface.

10. A classmate puts irrigation policy ("if moisture &lt; 0.3 then water") inside the vendor adapter. Why is that a trap? Where should that decision live instead (later Strategy), and what should stay in the adapter?

> [!NOTE]
> ***Your Answer***
>
> It's a trap because:
> - The rule would only apply to readings from that vendor; simulation and MQTT devices wouldn't follow it.
> - The threshold would be hard-coded instead of using each zone's `moisture_threshold_low` / `moisture_threshold_high`.
> - Changing the rule would mean editing infrastructure code.
> - An adapter that triggers watering is no longer just translating, so it's harder to test and reason about.
>
> The decision belongs in the application/domain layer, in Phase 6's **Strategy**: an irrigation strategy that takes a zone's thresholds and the latest moisture reading and decides whether to water. It works the same whatever adapter produced the reading. The adapter should only translate the raw vendor data into a normalized `Reading` (value, unit, source, timestamp), and nothing more.