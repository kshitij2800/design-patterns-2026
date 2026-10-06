"""Integration tests: HTTP -> ReadingIngest -> sensor_readings."""
from uuid import uuid4

from sqlalchemy import create_engine, text


def simulation_sensor_id(client):
    r = client.post("/api/devices/provision", params={"family": "simulation"})
    assert r.status_code == 201, r.text
    return next(d["id"] for d in r.json() if d["role"] == "sensor")


def row_count(migrated_db, device_id):
    engine = create_engine(migrated_db)
    with engine.connect() as conn:
        n = conn.execute(
            text("SELECT count(*) FROM sensor_readings WHERE device_id = :id"), {"id": device_id}
        ).scalar_one()
    engine.dispose()
    return n


def test_read_inserts_sensor_reading(client, migrated_db):
    sensor_id = simulation_sensor_id(client)

    r = client.post(f"/api/sensors/{sensor_id}/read")
    assert r.status_code == 201, r.text
    assert set(r.json()) == {"device_id", "value", "unit", "source", "recorded_at"}
    assert row_count(migrated_db, sensor_id) == 1

    client.post(f"/api/sensors/{sensor_id}/read")
    assert row_count(migrated_db, sensor_id) == 2


def test_read_missing_device_404(client):
    assert client.post(f"/api/sensors/{uuid4()}/read").status_code == 404


def test_patch_sampling_round_trip(client):
    sensor_id = simulation_sensor_id(client)
    r = client.patch(
        f"/api/devices/{sensor_id}/sampling",
        json={"sampling_interval_seconds": 30, "tracking_enabled": False},
    )
    assert r.status_code == 200, r.text

    stored = next(s for s in client.get("/api/sensors").json() if s["id"] == sensor_id)
    assert stored["sampling_interval_seconds"] == 30
    assert stored["tracking_enabled"] is False


def test_patch_sampling_too_small_400(client):
    sensor_id = simulation_sensor_id(client)
    r = client.patch(
        f"/api/devices/{sensor_id}/sampling",
        json={"sampling_interval_seconds": 4, "tracking_enabled": True},
    )
    assert r.status_code == 400