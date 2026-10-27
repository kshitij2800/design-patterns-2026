
## A. Pattern

1. State the intent of Facade in plain language. What problem appears when every HTTP handler (or every UI screen) repeats the same multi-step dance across repositories and services?

> [!NOTE]
> **_Your Answer_**
>
> A Facade gives one simple entry point to a group of subsystems that are complicated to use together. The caller asks one question ("give me the overview of this location") and the facade does all the steps behind it.
> Without it, every handler or screen repeats the same steps: load the location and zones, load the devices, find the latest readings, read the saved strategy, run evaluate. That causes copied code, and the copies drift apart (one screen counts unassigned devices, another doesn't). Every caller also depends on many classes, so one change in a repository breaks many places.

2. A facade **orchestrates** collaborators. What should it **not** become (a god object that owns all domain logic)? Where should irrigation policy, sensor translation, and persistence stay instead?

> [!NOTE]
> **_Your Answer_**
>
> The facade should only ask other parts for data and put the answer together. It should not contain business rules, SQL, or its own copy of logic that already exists. Otherwise it grows into a god object that knows and does everything.
>
> - **Irrigation policy** stays in the Strategy classes (`ConservativeMoistureStrategy`, `AggressiveMoistureStrategy`), called through `AutomationService.evaluate`. My facade calls `evaluate`; it never calls `decide()` itself.
> - **Sensor translation** stays in the Phase 5 adapters (simulation, vendor stub, MQTT), behind `SensorPort` and `ReadingIngest`.
> - **Persistence** stays in the repositories (`LocationRepository`, `DeviceRepository`, `ReadingRepository`, `AutomationRepository`). The two new queries I needed went into the repositories, not into the facade.

3. When should you use Facade, and when should you skip it (a single repository call is enough; or you actually need to **translate** a mismatched interface)?

> [!NOTE]
> **_Your Answer_**
>
> **Use it** when one use case needs several subsystems in a fixed order, and more than one caller (or a thin router) should not know those details. The dashboard overview is a good example: four subsystems, one answer.
>
> **Skip it** when:
> - one repository or service call is already enough (for example, listing locations). A facade would only add an extra layer.
> - the real problem is that an interface has the wrong shape (a vendor payload with different units and field names). That needs an **Adapter**, not a Facade.

## B. This phase of the application

4. What does `GET /api/locations/{location_id}/overview` return? Name the main pieces of the overview DTO: location, assigned device counts, and `zones` (thresholds, assigned devices, and those devices’ latest readings, including `tracking_enabled` and `sampling_interval_seconds`), plus strategy key and last recommendation. Why may those reading rows come from the sampler or MQTT ingest, not only from `POST /read`? Why is overview scoped by `location_id`?

> [!NOTE]
> **_Your Answer_**
>
> It returns one `LocationOverviewDto`:
> - `location`: `id` and `name`
> - `device_counts`: `sensor` and `actuator`, counting only **assigned** devices (this `location_id` and a non-null `zone_id`)
> - `zones`: **every** zone of the location, also empty ones. Each has `id`, `name`, `moisture_threshold_low`, `moisture_threshold_high`, `devices` (`id`, `device_type`, `role`, `display_name`) and `latest_readings` (`device_id`, `value`, `unit`, `recorded_at`, plus `tracking_enabled` and `sampling_interval_seconds` copied from the device). A device with no reading stays in `devices` but is left out of `latest_readings`.
> - `strategy_key`: the saved key, or `null`
> - `last_recommendation`: `action` and `reason` from evaluate, or `null` when no key is saved
>
> **Readings from any source:** since Phase 5, every reading goes through one path (`ReadingIngest`) into the same `sensor_readings` table, whether it came from "Read now", the background sampler or a translated MQTT payload. The newest row is simply the current value. Filtering to `POST /read` would show old values while the sampler keeps working.
>
> **Scoped by `location_id`:** since Phase 4, a location is the top-level resource. Zones, device assignment and the saved strategy all hang off `location_id`, and there is no `greenhouse_id` anywhere. So one location is the natural unit for one snapshot.

5. Why does this phase **not** require a new business table? What already exists from Phases 2–6 that the facade only **composes**?

> [!NOTE]
> **_Your Answer_**
>
> The overview is a **read model**: it only combines data that is already stored. Nothing new needs to be saved. The recommendation is calculated on every request instead of being stored.
>
> What already exists:
> - `devices` (Phases 2–3), with `location_id` / `zone_id` (Phase 4) and `tracking_enabled` / `sampling_interval_seconds` (Phase 5)
> - `locations` and `zones` with moisture thresholds (Phase 4)
> - `sensor_readings` (Phase 5)
> - `automation_rules` with the saved `strategy_key` (Phase 6), plus `AutomationService.evaluate`
>
> I skipped the optional SQL view because the existing tables are enough. `alembic check` reports no changes.

6. The overview HTTP handler should call **only** the facade, not reading/strategy/device repositories directly. Why? How does that help tests and later changes to the query shape?

> [!NOTE]
> **_Your Answer_**
>
> The router's only job is HTTP: read the path parameter, call one method, and turn "location not found" into 404. If it imported four repositories and a service, the overview logic would live in the interface layer and break the clean architecture.
>
> - **Tests:** the facade can be tested without HTTP. My N+1 test calls `LocationOverviewFacade.from_session(...).get_overview(...)` directly and counts the SQL queries. The facade could also be given fake repositories.
> - **Later changes:** I can change *how* the data is loaded (for example, replace two queries with one join or a SQL view) inside the facade or repository. The router, the response shape and the frontend don't change.

7. The location selector may use the existing locations list. The Overview cards come from **one** overview fetch, and Refresh repeats that same fetch. Why must the React page not stitch device, reading, and automation calls together to build the same snapshot? How does a new reading or a saved strategy show up on overview without extra frontend glue?

> [!NOTE]
> **_Your Answer_**
>
> If React stitched several calls together, the business rules ("only assigned devices", "newest reading per device", "no recommendation without a saved key") would live in the UI. Every other client would have to copy them. It would also need many requests, and the parts could come from different moments, giving an inconsistent snapshot. The server already has all the data, so it is the right place to build the snapshot once.
>
> **New data shows up automatically:** the facade reads the database on every GET and nothing is cached. `last_recommendation` is calculated by `evaluate` on every request. So after a new reading is stored or a strategy is saved, pressing Refresh (the same one `fetchOverview` call) shows it, with no extra frontend code. My test `test_overview_reflects_new_reading_and_keeps_device_without_reading` checks this.

## C. Compare, contrast, and scenarios

8. Contrast Facade with **Adapter**. One makes an existing interface usable; the other makes a subsystem simpler to call. Which is which, and how do both appear in this greenhouse app (Phase 5 vs Phase 7)?

> [!NOTE]
> **_Your Answer_**
>
> - **Adapter** makes an existing interface usable: it **translates** one foreign format into the one our code expects. In **Phase 5**, the vendor stub adapter turns integers ×100, percent and epoch milliseconds into a `Reading`, and the MQTT adapter turns a `{value, unit}` payload into a `Reading`. Both sit behind `SensorPort`.
> - **Facade** makes a subsystem simpler to call: it **coordinates** several of our own parts that already work, and translates nothing. In **Phase 7**, `LocationOverviewFacade.get_overview()` hides four repositories and `AutomationService`.
>
> In short, an Adapter wraps **one** thing with the wrong shape, and a Facade wraps **many** things that are correct but complicated to use together.

9. This phase mentions **N+1** queries. What is an N+1 problem in an overview that lists latest readings for many devices, and what can the facade (or its repository) do about it without putting SQL in the router?

> [!NOTE]
> **_Your Answer_**
>
> N+1 means 1 query to get the list of devices, then 1 more query **per device** to get its latest reading. With 50 devices that is 51 round trips to the database, and it gets slower as the location grows.
>
> My fix is in the repository layer:
> - `DeviceRepository.list_assigned_in_location()` gets all assigned devices in **one** query.
> - `ReadingRepository.latest_for_devices(ids)` gets the newest reading for **all** of them in **one** query. It uses `ROW_NUMBER() OVER (PARTITION BY device_id ORDER BY recorded_at DESC)` and keeps row 1, using the Phase 5 `(device_id, recorded_at DESC)` index.
>
> The facade then matches readings to devices in Python, and the router contains no SQL. My test `test_overview_reading_query_count_does_not_grow_with_devices` shows there is still exactly one readings query with 1 or 5 sensors.
>
> Note: `evaluate` still looks up moisture once per **zone** inside the automation service. I left that there on purpose, because fixing it would mean copying the strategy logic into the facade.

10. A classmate hides every error behind a generic “overview failed,” so a missing location, a DB outage, and a strategy error look the same. Why is that a trap for a facade?

> [!NOTE]
> **_Your Answer_**
>
> A facade hides the subsystems, so it must **not** also hide what went wrong in them. These errors mean different things and need different reactions:
> - **Missing location**: the client's mistake → **404**. The UI can say "location not found".
> - **Database outage**: the server's problem → **500** (or 503). Retrying later may help.
> - **Strategy error** (an unknown saved key): a data or configuration problem that a developer must fix.
>
> If everything becomes "overview failed", the client cannot react correctly, logs lose the real cause, and debugging becomes guessing. It also breaks the spec, which says "no saved strategy" must be **200** and a missing location must be **404**.
>
> In my implementation, only `LocationNotFoundError` is mapped to 404. "No strategy saved" is a normal 200 with both fields `null`, and other errors are not swallowed, so they reach FastAPI as real 500 errors with the original cause in the logs.
