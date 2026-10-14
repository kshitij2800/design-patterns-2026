"""Integration: HTTP -> LocationOverviewFacade -> locations, zones, devices, sensor_readings, automation_rules."""
from uuid import UUID, uuid4

from sqlalchemy import create_engine, event, text

from application.overview.facade import LocationOverviewFacade


def seed(migrated_db) -> dict:
    """Location with two zones. Bench 1 has one assigned sensor with readings;
    Bench 2 is empty. One unassigned sensor (with a reading) is not in any zone."""
    engine = create_engine(migrated_db)
    with engine.begin() as conn:
        def one(sql, **params):
            return str(conn.execute(text(sql), params).scalar_one())

        loc = one("INSERT INTO locations (name) VALUES ('Overview site') RETURNING id")
        bench1 = one(
            "INSERT INTO zones (location_id, name, moisture_threshold_low, moisture_threshold_high) "
            "VALUES (:l, 'Bench 1', 0.25, 0.45) RETURNING id", l=loc,
        )
        bench2 = one(
            "INSERT INTO zones (location_id, name, moisture_threshold_low, moisture_threshold_high) "
            "VALUES (:l, 'Bench 2', 0.30, 0.60) RETURNING id", l=loc,
        )
        # Assigned: location_id AND zone_id set. Non-default sampling so we can see it copied.
        sensor = one(
            "INSERT INTO devices (device_type, role, display_name, location_id, zone_id, "
            "sampling_interval_seconds, tracking_enabled) "
            "VALUES ('moisture_sensor', 'sensor', 'Bench moisture', :l, :z, 60, false) RETURNING id",
            l=loc, z=bench1,
        )
        # Unassigned: no location, no zone.
        unassigned = one(
            "INSERT INTO devices (device_type, role, display_name) "
            "VALUES ('moisture_sensor', 'sensor', 'Spare sensor') RETURNING id"
        )
        # Older simulation row, then a newer MQTT row: newest wins, source is not filtered.
        for dev, value, source, age in [
            (sensor, 0.10, "simulation", "10 minutes"),
            (sensor, 0.31, "mqtt", "1 minute"),
            (unassigned, 0.99, "simulation", "1 minute"),
        ]:
            conn.execute(
                text(
                    "INSERT INTO sensor_readings (device_id, value, unit, source, recorded_at) "
                    "VALUES (:d, :v, 'vwc', :s, now() - CAST(:age AS interval))"
                ),
                {"d": dev, "v": value, "s": source, "age": age},
            )
    engine.dispose()
    return {"loc": loc, "bench1": bench1, "bench2": bench2, "sensor": sensor, "unassigned": unassigned}


def zone_named(body, name):
    return next(z for z in body["zones"] if z["name"] == name)


def test_overview_returns_strategy_and_readings(client, migrated_db):
    s = seed(migrated_db)

    # Unknown location -> 404
    assert client.get(f"/api/locations/{uuid4()}/overview").status_code == 404

    # No saved strategy -> still 200, both strategy fields null
    r = client.get(f"/api/locations/{s['loc']}/overview")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["location"] == {"id": s["loc"], "name": "Overview site"}
    assert body["strategy_key"] is None
    assert body["last_recommendation"] is None

    # Counts: assigned devices only
    assert body["device_counts"] == {"sensor": 1, "actuator": 0}

    # Unassigned device is in no zone
    all_device_ids = {d["id"] for z in body["zones"] for d in z["devices"]}
    all_reading_ids = {r["device_id"] for z in body["zones"] for r in z["latest_readings"]}
    assert s["unassigned"] not in all_device_ids
    assert s["unassigned"] not in all_reading_ids

    # Assigned sensor: in Bench 1 with its newest reading + device sampling fields
    bench1 = zone_named(body, "Bench 1")
    assert [d["id"] for d in bench1["devices"]] == [s["sensor"]]
    assert bench1["moisture_threshold_low"] == 0.25
    assert bench1["moisture_threshold_high"] == 0.45
    (reading,) = bench1["latest_readings"]
    assert reading["device_id"] == s["sensor"]
    assert reading["value"] == 0.31                 # newest row (mqtt), not the older 0.10
    assert reading["unit"] == "vwc"
    assert reading["tracking_enabled"] is False
    assert reading["sampling_interval_seconds"] == 60

    # Empty zone is still listed
    bench2 = zone_named(body, "Bench 2")
    assert bench2["devices"] == []
    assert bench2["latest_readings"] == []

    # After saving a key, last_recommendation matches evaluate for the same location
    assert client.put(
        f"/api/locations/{s['loc']}/automation", json={"strategy_key": "conservative"}
    ).status_code == 200
    body = client.get(f"/api/locations/{s['loc']}/overview").json()
    evaluated = client.post(f"/api/locations/{s['loc']}/automation/evaluate").json()
    assert body["strategy_key"] == "conservative"
    assert body["last_recommendation"] == {
        "action": evaluated["action"],
        "reason": evaluated["reason"],
    }


def test_overview_reflects_new_reading_and_keeps_device_without_reading(client, migrated_db):
    s = seed(migrated_db)
    engine = create_engine(migrated_db)
    with engine.begin() as conn:
        actuator = str(conn.execute(
            text(
                "INSERT INTO devices (device_type, role, display_name, location_id, zone_id) "
                "VALUES ('pump', 'actuator', 'Bench pump', :l, :z) RETURNING id"
            ),
            {"l": s["loc"], "z": s["bench1"]},
        ).scalar_one())

    body = client.get(f"/api/locations/{s['loc']}/overview").json()
    bench1 = zone_named(body, "Bench 1")
    assert body["device_counts"] == {"sensor": 1, "actuator": 1}
    assert actuator in {d["id"] for d in bench1["devices"]}                  # listed...
    assert actuator not in {r["device_id"] for r in bench1["latest_readings"]}  # ...no reading

    # A new reading is visible on the next GET (nothing cached)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO sensor_readings (device_id, value, unit, source, recorded_at) "
                "VALUES (:d, 0.42, 'vwc', 'simulation', now())"
            ),
            {"d": s["sensor"]},
        )
    engine.dispose()
    body = client.get(f"/api/locations/{s['loc']}/overview").json()
    assert zone_named(body, "Bench 1")["latest_readings"][0]["value"] == 0.42


def test_overview_reading_query_count_does_not_grow_with_devices(db_session, migrated_db):
    """No N+1: one sensor_readings query whether the location has 1 or 5 assigned sensors."""
    s = seed(migrated_db)

    def reading_queries() -> int:
        statements: list[str] = []
        bind = db_session.get_bind()

        def capture(conn, cursor, statement, *args):
            statements.append(statement)

        event.listen(bind, "before_cursor_execute", capture)
        try:
            LocationOverviewFacade.from_session(db_session).get_overview(UUID(s["loc"]))
        finally:
            event.remove(bind, "before_cursor_execute", capture)
        return sum("sensor_readings" in st for st in statements)

    before = reading_queries()

    engine = create_engine(migrated_db)
    with engine.begin() as conn:
        for i in range(4):
            conn.execute(
                text(
                    "INSERT INTO devices (device_type, role, display_name, location_id, zone_id) "
                    "VALUES ('moisture_sensor', 'sensor', :n, :l, :z)"
                ),
                {"n": f"Extra {i}", "l": s["loc"], "z": s["bench1"]},
            )
    engine.dispose()

    assert before == 1
    assert reading_queries() == before