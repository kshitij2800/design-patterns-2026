
## A. Pattern

1. State the intent of Strategy in plain language. How does the **context** use a strategy, and why must “choose which algorithm” stay separate from “run the algorithm”?

> [!NOTE]
> ***Your Answer***
>
> Strategy lets you define a family of interchangeable algorithms behind one interface, so the code that needs a decision doesn't care which algorithm produces it. In my app, `AutomationService` is the context. It builds a plain `LocationAutomationContext` for each zone and calls `strategy.decide(context)` without knowing whether the strategy is conservative or aggressive. "Choose which algorithm" (`get_strategy(key)` using the saved `strategy_key`) is kept separate from "run the algorithm" (`decide`). That way a new policy never touches the code that runs it, and an unknown key is rejected before any decision logic runs.

2. Name the participants (**strategy**, **concrete strategies**, **context**, **client**). What goes wrong when all policies live as `if/elif` inside the context (or inside an HTTP router)?

> [!NOTE]
> ***Your Answer***
>
> - **Strategy:** the `AutomationStrategy` interface with `decide(context)`.
> - **Concrete strategies:** `ConservativeMoistureStrategy` and `AggressiveMoistureStrategy`.
> - **Context:** `AutomationService` together with `LocationAutomationContext`. It gathers the data and delegates the decision.
> - **Client:** the code that picks the strategy: the API call that saves the key, and the service that looks it up.
>
> If all policies lived as `if/elif` inside the context or the router, every new policy would mean editing that file, and the file would keep growing. The policies would be hard to unit test without HTTP or a database, and the HTTP layer would end up holding irrigation rules.


3. When should you use Strategy, and when should you skip it (one algorithm only; or the variation is a **lifecycle mode** rather than a chosen policy)?

> [!NOTE]
> ***Your Answer***
>
> Use Strategy when there are several ways to do the same job, such as deciding whether to irrigate, and one of them should be chosen or swapped at runtime or by configuration. Skip it when there is only one algorithm, because the interface would be extra code with no benefit. Also skip it when the variation is a lifecycle mode, meaning the object's behaviour changes because of what has happened to it (for example idle, running, faulted). That is State, not a policy someone selects.


## B. This phase of the application

4. In this lab, what does a strategy’s `decide(context)` return (action + reason)? Give a concrete difference you implemented (or were required to implement) between **conservative** and **aggressive** on the **same** moisture reading and zone thresholds.

> [!NOTE]
> ***Your Answer***
>
> `decide(context)` returns a `Recommendation` with an `action` (`irrigate` or `wait`), a `reason` string, and an optional `score` (how far below the trigger level the moisture is). Conservative irrigates only when moisture is below the zone's `low` threshold. Aggressive irrigates once moisture falls below the midpoint of the band, `(low + high) / 2`. For a zone with band 0.20–0.45 and a moisture reading of 0.30, conservative says `wait` and aggressive says `irrigate` (score 0.025), because the midpoint is 0.325. I confirmed this both with curl and in the dashboard.


5. Where do the numbers in `LocationAutomationContext` (or your equivalent) come from? Latest moisture may already be in `sensor_readings` from a manual read, the simulation sampler, or MQTT translation — why does this phase not add a scheduler or a broker? Why must strategies receive a plain context object, not SQLAlchemy rows or FastAPI types? Why are thresholds read from **zones**, not hardcoded in the strategy class?

> [!NOTE]
> ***Your Answer***
>
> The numbers come from the database. Thresholds come from the zone's row in `zones`, and moisture is the latest `sensor_readings` row among sensors whose `devices.zone_id` is that zone. The repository assembles these values into a context. This phase doesn't add a scheduler or broker because the readings already arrive through the Phase 5 ingest path (manual read, simulation sampler, or translated MQTT payload), so Strategy only needs to read whatever is latest. Strategies receive a plain context object so they stay pure Python. They can be unit tested with a fake context and don't depend on SQLAlchemy or FastAPI. Thresholds come from `zones` because they are per-zone configuration the user sets, and hardcoding them in a strategy would ignore that configuration.

6. The active `strategy_key` is **persisted** per `location_id` (for example in `automation_rules`). Why must `POST .../automation/evaluate` use the **saved** key rather than a key the client sends only in that request? What happens on the next evaluate after the operator changes strategy but moisture stays the same?

> [!NOTE]
> ***Your Answer***
>
> The saved key is what the operator chose for that location, so it should be the single source of truth. If evaluate trusted a key sent only in that request, then evaluating with one key and the saved key could disagree, and different clients could get different answers for the same location. With the key persisted in `automation_rules` (one row per `location_id`), the next evaluate after a strategy change reads the new key. If the moisture reading is unchanged, the recommendation can still change. For example, at 0.30 with band 0.20–0.45, switching from conservative to aggressive turns `wait` into `irrigate`.

7. Strategy **recommends** (irrigate / wait). It should not itself start a pump. Why keep **decide** separate from **execute**? Which later pattern is meant to carry out the action?

> [!NOTE]
> ***Your Answer***
>
> A strategy should only decide, and the pump action should be carried out elsewhere. Keeping `decide` separate from execute means the decision logic is easy to test without any hardware, can be shown in the UI as a recommendation, and can be reviewed or overridden before anything physical happens. Starting a pump from inside a strategy would couple the algorithm to hardware and make it risky to test. The action is meant to be carried out by a later pattern, most likely Command, an object that represents "run this action" and can be queued, logged or undone, using the actuator port and adapter from Phase 5.

## C. Compare, contrast, and scenarios

8. Contrast Strategy with **State** (Phase 8). Both delegate to an object with the same shape. Who typically **changes** the active object, and is the variation a **policy** or a **lifecycle**?

> [!NOTE]
> ***Your Answer***
>
> Both patterns delegate work to an object that has the same interface. The difference is who changes the active object and why. In Strategy, the client or operator picks the object (for example, saving `conservative` or `aggressive` for a location), and the variation is a **policy**, meaning different ways to do the same job. In State, the object changes itself or is moved by events as it goes through its **lifecycle** (for example, a device moving from idle to running to faulted). In Strategy, the strategies don't normally know about each other, but in State the states usually know which state comes next.

9. Contrast Strategy with **Adapter** (Phase 5) and with **Builder** (Phase 4). Which one translates a foreign API, which one assembles a valid aggregate, and which one swaps an algorithm?

> [!NOTE]
> ***Your Answer***
>
> - **Adapter (Phase 5)** translates a foreign interface into the one the app expects. In my app, `VendorStubSensorAdapter` turns a vendor payload into a normal `Reading`.
> - **Builder (Phase 4)** assembles a valid aggregate step by step, such as a location with its zones.
> - **Strategy (Phase 6)** swaps an algorithm behind one interface, such as conservative vs aggressive irrigation decisions.
>
> In short, Adapter translates, Builder assembles, and Strategy swaps the decision logic.


10. A classmate writes one “mega-strategy” that still contains `if conservative` / `if aggressive` inside a single class. Another strategy class calls the actuator adapter to water immediately. Explain why each is a trap.

> [!NOTE]
> ***Your Answer***
>
> A single "mega-strategy" with `if conservative` / `if aggressive` inside it just moves the `if/elif` problem into one class. Adding a third policy still means editing that class, and the pattern's benefit (separate, small, testable classes behind one interface) is lost. A strategy that calls the actuator adapter to water immediately mixes deciding with doing. Evaluating becomes a side effect, so merely pressing Evaluate or running a test could start a pump. It also couples the algorithm to hardware, so it can't be tested with a fake context. A strategy should only return a recommendation, and executing it should be a separate step.