"""Integration: HTTP -> AutomationService -> automation_rules + zones + sensor_readings."""
from uuid import uuid4

from sqlalchemy import create_engine, text


def seed(migrated_db, moisture=None) -> str:
    """One location, one zone (0.25-0.45). With `moisture`, also a sensor in the zone with a reading."""
    engine = create_engine(migrated_db)
    with engine.begin() as conn:
        loc = str(conn.execute(
            text("INSERT INTO locations (name) VALUES ('Test location') RETURNING id")
        ).scalar_one())
        zone = str(conn.execute(
            text(
                "INSERT INTO zones (location_id, name, moisture_threshold_low, moisture_threshold_high) "
                "VALUES (:l, 'Zone A', 0.25, 0.45) RETURNING id"
            ),
            {"l": loc},
        ).scalar_one())
        if moisture is not None:
            dev = str(conn.execute(
                text("INSERT INTO devices (device_type, role, zone_id) VALUES ('moisture_sensor', 'sensor', :z) RETURNING id"),
                {"z": zone},
            ).scalar_one())
            conn.execute(
                text(
                    "INSERT INTO sensor_readings (device_id, value, unit, source, recorded_at) "
                    "VALUES (:d, :v, 'vwc', 'simulation', now())"
                ),
                {"d": dev, "v": moisture},
            )
    engine.dispose()
    return loc


def rule_count(migrated_db, location_id) -> int:
    engine = create_engine(migrated_db)
    with engine.connect() as conn:
        n = conn.execute(
            text("SELECT count(*) FROM automation_rules WHERE location_id = :l"), {"l": location_id}
        ).scalar_one()
    engine.dispose()
    return n


def test_evaluate_follows_persisted_strategy(client, migrated_db):
    loc = seed(migrated_db, moisture=0.30)

    assert client.put(f"/api/locations/{loc}/automation", json={"strategy_key": "conservative"}).status_code == 200
    body = client.post(f"/api/locations/{loc}/automation/evaluate").json()
    assert body["strategy_key"] == "conservative"
    assert body["action"] == "wait"

    assert client.put(f"/api/locations/{loc}/automation", json={"strategy_key": "aggressive"}).status_code == 200
    body = client.post(f"/api/locations/{loc}/automation/evaluate").json()
    assert body["strategy_key"] == "aggressive"
    assert body["action"] == "irrigate"
    assert body["zones"][0]["action"] == "irrigate"

    assert rule_count(migrated_db, loc) == 1          # upsert, not a second row


def test_unknown_strategy_key_400(client, migrated_db):
    loc = seed(migrated_db)
    r = client.put(f"/api/locations/{loc}/automation", json={"strategy_key": "yolo"})
    assert r.status_code == 400
    assert rule_count(migrated_db, loc) == 0


def test_missing_location_404(client):
    missing = uuid4()
    assert client.put(f"/api/locations/{missing}/automation", json={"strategy_key": "conservative"}).status_code == 404
    assert client.post(f"/api/locations/{missing}/automation/evaluate").status_code == 404


def test_zone_without_moisture_sensor_waits(client, migrated_db):
    loc = seed(migrated_db)          # zone exists, no sensor assigned
    body = client.post(f"/api/locations/{loc}/automation/evaluate").json()
    assert body["action"] == "wait"
    assert "no moisture reading" in body["zones"][0]["reason"]