
## A. Pattern

1. State the intent of Builder in plain language. Why does construction of a complex object need **stepwise assembly** and **validation at the end** (`build()`), instead of a telescoping constructor or a half-filled dict written straight to the database?

> [!NOTE]
> **_Your Answer_**
>
> Builder separates the assembly of a complex object from the finished object. Parts are added step by step, and a final `build()` checks the whole and either returns a valid object or refuses. A telescoping constructor does not suit a location, because the number of zones varies and each zone has several fields; it also cannot check rules that span parts, such as unique zone names. A half-filled dict written straight to the database has no guarantee of completeness, so a location with no zones or inverted thresholds could be stored and break later phases. With Builder, construction is gradual, but the object only exists once it is valid.

2. Name the main participants (**product**, **builder**, **optional director**, **client**). Until `build()` succeeds, is the intermediate object a finished domain product? Why does that distinction matter?

> [!NOTE]
> **_Your Answer_**
>
> The product is `LocationConfig` (a `Location` with its `Zone`s), the builder is `LocationConfigBuilder`, and `LocationConfigService.build_and_save()` acts as the director by calling the builder steps from the request DTO. The client is the `POST /api/locations/config` handler. Until `build()` succeeds, there is no product, only unvalidated builder state. This matters because the repository only accepts a `LocationConfig`, so unvalidated data has no route into the database.


3. List at least three kinds of invalid configuration a location/zone `build()` should reject in **this** lab (name, zones, moisture thresholds). Why must those rules live in the **domain** builder, not only in the HTTP layer?

> [!NOTE]
> **_Your Answer_**
>
> `build()` rejects an empty location name, a location with no zones, a zone without a name, thresholds outside 0.0–1.0, a low threshold that is not strictly below the high one, and duplicate zone names within a location. These rules belong in the domain because the HTTP layer is only one entry point; services, tests and future interfaces must obey the same rules. Some rules, such as low < high or unique names, involve several fields and cannot be expressed cleanly per field. Keeping them in `validate_zone_fields()` also lets the zone add and edit operations reuse exactly the same checks.


## B. This phase of the application

4. What aggregate does the builder produce (location plus zones)? Why does this course use **`location_id`** (and never `greenhouse_id`) as the name for that scope?

> [!NOTE]
> **_Your Answer_**
>
> The builder produces one aggregate: a location together with all of its zones, each with moisture thresholds and a schedule. The course uses `location_id` because one smart-greenhouse installation can cover several places, such as a lab bench or a growing room, so "location" is the general scope. Using the same name everywhere (`zones.location_id`, `devices.location_id`, `/api/locations/...`) keeps the schema and API consistent, whereas adding `greenhouse_id` would create two names for one concept.


5. Describe the path from API request to persistence: DTO → builder steps → `build()` → repository. What must **not** be persisted if `build()` raises `ConfigurationError` (or equivalent)? Why does assigning a device wait until the zone row exists, and why does the client send only `zone_id`?

> [!NOTE]
> **_Your Answer_**
>
> A request is parsed into `LocationConfigRequestDto`, the service calls `with_location_name()` and `add_zone()` for each zone, and `build()` either returns a `LocationConfig` or raises `ConfigurationError`. Only a successful result reaches `LocationRepository.save_config()`. If `build()` raises, nothing is saved, neither the location nor any zone, and the API returns 400. Device assignment happens afterwards because `devices.zone_id` must reference a saved zone, and a zone has no id before it is stored. The client sends only `zone_id` so that the server can copy `location_id` from the zone itself, which prevents the two values from ever disagreeing.


6. Saving a location and its zones must be **one transaction**. What goes wrong if the location row commits and a later zone insert fails? How does that relate to “no half-built aggregates in the database”?

> [!NOTE]
> **_Your Answer_**
>
> If the location committed and a later zone insert failed, the database would contain a location with no zones or with only some of them, breaking the "at least one zone" rule that `build()` enforces. Saving everything in one transaction, with a rollback on failure, stores the aggregate all or nothing. Builder prevents half-built objects in memory, and the transaction prevents half-built aggregates in the database.


7. The configuration wizard UI collects fields in steps. How does that UI map to Builder without turning React (or the HTTP handler) into the place that owns domain validation?

> [!NOTE]
> **_Your Answer_**
>
> The wizard collects the location name and zone rows, which mirror the builder steps, and its inline messages only give quick feedback. It sends the complete configuration in one request and displays whatever error the server returns. The HTTP handler is equally thin, mapping the DTO to builder calls and converting `ConfigurationError` into a 400 response. The domain therefore remains the single authority on what is valid.


## C. Compare, contrast, and scenarios

8. Contrast Builder with Factory Method and with Abstract Factory. Which pattern answers “which type?”, which answers “which matching kit?”, and which answers “how do we assemble one **valid whole** in steps?”

> [!NOTE]
> **_Your Answer_**
>
> Factory Method, used in Phase 2, answers "which type?" by letting a creator choose which sensor class to instantiate. Abstract Factory, used in Phase 3, answers "which matching kit?" by producing a coherent family of devices such as a simulation or edge kit. Builder answers "how do we assemble one valid whole in steps?" by building a single complex object from a variable number of parts and validating it at the end. The factories are about choosing what to create, while Builder is about assembling and validating it.


9. Fluent method chaining (`builder.add_zone(...).build()`) is a coding style. Why is a fluent interface **not** the same thing as the Builder pattern?

> [!NOTE]
> **_Your Answer_**
>
> A fluent interface is only a coding style in which methods return `self` so calls can be chained. Builder is defined by its structure: a separate object holds intermediate state, the product does not exist until construction finishes, and `build()` validates the whole. The same builder would still be a Builder without chaining, while a fluent class that skips validation would not be one.


10. A classmate validates thresholds only in FastAPI / Pydantic and leaves `build()` empty. Another mutates builder fields after `build()` while treating the product as immutable. Explain why each is a trap.

> [!NOTE]
> **_Your Answer_**
>
> Validating only in FastAPI or Pydantic leaves the domain unprotected, so any other path, such as a service call, a script or a future endpoint, can save an invalid configuration, and cross-field rules are hard to express there anyway. Mutating builder fields after `build()` is dangerous if the product shares lists or dictionaries with the builder, because an already validated product can then change silently. This project avoids that by returning frozen dataclasses, converting zones to a new tuple and copying each schedule, so a different configuration must be built again rather than edited in place.
