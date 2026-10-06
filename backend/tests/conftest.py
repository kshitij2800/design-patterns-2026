import os
import subprocess
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from infrastructure.settings import settings

BACKEND_DIR = Path(__file__).resolve().parents[1]
TEST_DB_NAME = "greenhouse_test"

_base_url = make_url(settings.database_url)
assert _base_url.database != TEST_DB_NAME, "Refusing to run: base URL already points at the test DB"
ADMIN_URL = _base_url.render_as_string(hide_password=False)
TEST_URL = _base_url.set(database=TEST_DB_NAME).render_as_string(hide_password=False)

# Point the app at the test database before infrastructure.db creates its engine.
settings.database_url = TEST_URL
os.environ["DATABASE_URL"] = TEST_URL
# Phase 5: tests drive the sampler by hand with a fake clock — no background loop.
settings.sampler_enabled = False


@pytest.fixture(scope="session")
def migrated_db():
    """Recreate an empty test database and migrate it to head."""
    admin = create_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}" WITH (FORCE)'))
        conn.execute(text(f'CREATE DATABASE "{TEST_DB_NAME}"'))
    admin.dispose()

    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        env={**os.environ, "DATABASE_URL": TEST_URL},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    yield TEST_URL


@pytest.fixture
def client(migrated_db):
    from fastapi.testclient import TestClient
    from infrastructure.db import engine
    from main import app

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE sensor_readings, locations, zones, devices CASCADE"))
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db_session(migrated_db):
    """A clean DB session for service-level tests (no HTTP)."""
    from infrastructure.db import SessionLocal, engine

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE sensor_readings, locations, zones, devices CASCADE"))
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()