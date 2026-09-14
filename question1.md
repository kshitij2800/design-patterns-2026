# Phase 1 — Skeleton questions

## A. Pattern

1. In your own words, what is a design pattern? What is it *not*?

A design pattern is a general, reusable solution to a problem that comes up often in software development. It's like a blueprint — it guides how you structure your code but isn't code itself. It's not a library you install, not a copy-paste solution, and not something you need to use everywhere.

2. Name the three GoF pattern families. For each family, give one-sentence: what kind of design problem it addresses. Then place **Factory Method** and **Strategy** into the correct family.

Creational — solves problems around how objects are created. Factory Method belongs here.

Structural — solves problems around how classes and objects are composed together.

Behavioral — solves problems around how objects communicate and share responsibility. Strategy belongs here.

3. A teammate wants to add a pattern “because it is on the course list,” even though the feature is small and unlikely to grow. When should you **skip** a pattern? What risk do you take if you apply one too early?

Skip a pattern when the feature is simple and won't grow. If a feature only needs a few lines of straightforward code, adding a pattern just makes it harder to read and understand. The risk of applying one too early is over-engineering — you spend time building complex abstractions for a problem that never actually needed them.

## B. This phase of the application

4. Why does Phase 1 ship a vertical slice that does almost no greenhouse business logic? What does “empty but running” prove that a folder of unimplemented classes would not?

Phase 1 proves the three tiers actually work together end to end. I built a FastAPI backend that connects to PostgreSQL running in Docker, and a React frontend that calls the backend's /health endpoint and shows the result. A folder of unimplemented classes would prove nothing — you can't run it, test it, or build on it with confidence. Having everything connected and running, even with no business logic, means Phase 2 can just start adding features.

5. List the four backend layer packages used in this course (`domain`, `application`, `infrastructure`, `interfaces/api`). For each, state what belongs there and give one example of something that must **not** live in `domain`.

domain — pure business logic, no framework dependencies. In my project this folder exists but is empty in Phase 1 since there's no business logic yet. Something that must NOT live here: a database connection or a FastAPI router.

application — use cases that coordinate between domain and infrastructure. Also empty in Phase 1, ready for Phase 2.

infrastructure — technical details like database connections and settings. I put settings.py here which reads the .env 
file, and db.py which creates the database engine and the check_db() function.

interfaces/api — HTTP layer. I put health.py here which defines the GET /health route.

6. What does `GET /health` return, and why does it check the database instead of only reporting that the HTTP process is up? Why is API documentation served at `/scalar`, and why is `/docs` disabled?

It returns `{"status": "ok", "db": "ok"}` when everything is running. It checks the database specifically because the HTTP process being up does not mean the app is actually functional — if PostgreSQL is down, nothing works. I implemented this in `health.py` using the `check_db()` function from `infrastructure/db.py` which runs a `SELECT 1` against the database. Scalar is served at `/scalar` as the API documentation tool required by the course, and `/docs` is disabled in `main.py` with `docs_url=None` to avoid having two competing documentation interfaces.

7. Phase 1 requires Alembic (or equivalent) with a **baseline** migration and **no** business tables such as `devices`. Why introduce the migration toolchain before any product schema? What would go wrong if you created tables by hand in Postgres and only added migrations later?

I set up Alembic with a baseline revision (`001_baseline.py`) that creates no tables. The reason is that Alembic needs to track the database from the very beginning. If I had created tables manually in PostgreSQL first and added Alembic later, Alembic would have no record of those tables and would think the database is empty — causing conflicts. Starting with the baseline means every future schema change goes through Alembic, so the database can be reproduced from scratch on any machine just by running `alembic upgrade head`.

## C. Compare, contrast, and scenarios

8. Explain **dependency direction** in this skeleton: which layers may import which? Why must domain code not import FastAPI, SQLAlchemy, or Pydantic models used as HTTP schemas?

Outer layers import from inner layers, never the other way around. So `interfaces/api` can import from `infrastructure` and `application`, but `domain` cannot import anything from FastAPI, SQLAlchemy, or Pydantic. In my project, `health.py` imports `check_db` from `infrastructure/db.py` — that is fine because api is an outer layer. The reason domain must stay clean is that it should contain pure business logic that works regardless of what framework you use. If you later swap FastAPI for something else, the domain layer should not need to change at all.


9. The frontend cannot show a healthy badge. A classmate blames “the patterns.” What should you check first (stack, CORS/proxy, health JSON), and why is that a Phase 1 concern rather than a later pattern concern?

The order to check is: first make sure Docker is running and PostgreSQL is healthy with `docker compose ps`, then make sure the backend is running with `PYTHONPATH=src uvicorn src.main:app`, then check that `GET /health` returns the correct JSON in the browser, then check that CORS is configured to allow requests from `localhost:5173`. This is a Phase 1 concern because all of it — the stack, the health endpoint, and CORS — was set up in Phase 1. Design patterns have nothing to do with whether the health badge works.

10. Course completion is at **Phase 12**, not Phase 1. What is still missing after a successful skeleton, and how do later phases add behaviour without rewriting the foundations you laid here?

All the actual greenhouse functionality is missing — no devices, no sensors, no readings, no automation, nothing business-related. The dashboard shows six placeholder cards with no real data. Later phases will fill these in by adding ORM models to `infrastructure`, use cases to `application`, new API routes to `interfaces/api`, and React components to the frontend. None of this requires restructuring the project because the layered foundation is already in place — each phase just fills in the empty layers without rewriting the foundations laid in Phase 1.