"""Observer: publishers -> EventBus -> subscribers -> alerts table -> GET /api/alerts."""
import inspect
from uuid import UUID

from sqlalchemy import create_engine, text

import application.commands.service as command_service
import application.devices.actuator_state_service as transition_service
import application.readings.service as reading_service
from application.alerts.subscribers import build_event_bus
from application.readings.service import ReadingIngest
from domain.devices.entity import Device
from domain.events.bus import EventBus
from domain.events.events import ReadingCreated, ThresholdCrossed
from infrastructure.adapters.sensors.mqtt import MqttSensorAdapter
from infrastructure.adapters.sensors.selector import select_sensor_adapter
from infrastructure.persistence.alert_repository import AlertRepository
from infrastructure.persistence.device_repository import DeviceRepository
from infrastructure.persistence.reading_repository import ReadingRepository


# ---------- helpers ----------

def sql(migrated_db, statement, **params):
    engine = create_engine(migrated_db)
    with engine.begin() as conn:
        result = conn.execute(text(statement), params)
        value = result.scalar() if result.returns_rows else None
    engine.dispose()
    return value


def seed_benches(migrated_db) -> dict:
    """One location, Bench 1 (low 0.20) and Bench 2, one tracked moisture sensor on Bench 1."""
    loc = str(sql(migrated_db, "INSERT INTO locations (name) VALUES ('Greenhouse A') RETURNING id"))
    zone_sql = ("INSERT INTO zones (location_id, name, moisture_threshold_low, moisture_threshold_high) "
                "VALUES (:l, :n, 0.20, 0.40) RETURNING id")
    bench1 = str(sql(migrated_db, zone_sql, l=loc, n="Bench 1"))
    bench2 = str(sql(migrated_db, zone_sql, l=loc, n="Bench 2"))
    sensor = str(sql(
        migrated_db,
        "INSERT INTO devices (device_type, role, display_name, location_id, zone_id) "
        "VALUES ('moisture_sensor', 'sensor', 'Bench 1 moisture', :l, :z) RETURNING id",
        l=loc, z=bench1,
    ))
    return {"loc": loc, "bench1": bench1, "bench2": bench2, "sensor": sensor}


def sim_sensor(name: str) -> Device:
    return Device(id=None, device_type="moisture_sensor", role="sensor", device_family="simulation",
                  display_name=name, default_config={"protocol": "simulation"})


def provision(client) -> dict[str, str]:
    r = client.post("/api/devices/provision", params={"family": "simulation"})
    assert r.status_code == 201, r.text
    return {d["device_type"]: d["id"] for d in r.json()}


def command(client, command_type, device_id):
    return client.post("/api/commands", json={"command_type": command_type, "device_id": device_id})


# ---------- tests ----------

def test_subscriber_inserts_on_published_event(db_session):
    bus = build_event_bus(db_session)

    bus.publish(ThresholdCrossed(device_id=None, location_id=None, zone_id=None,
                                 moisture=0.10, threshold_low=0.20))

    rows = AlertRepository(db_session).list_alerts()
    assert len(rows) == 1
    assert (rows[0].event_type, rows[0].severity, rows[0].message) == (
        "threshold.crossed", "warning", "Moisture below zone low")


def test_ingest_publishes_reading_created_only_when_tracking_on(db_session):
    devices, readings = DeviceRepository(db_session), ReadingRepository(db_session)
    bus = EventBus()
    received: list[ReadingCreated] = []
    bus.subscribe(ReadingCreated, received.append)
    ingest = ReadingIngest(devices, readings, select_sensor_adapter, bus)

    tracked, untracked = devices.save_devices([sim_sensor("Tracked"), sim_sensor("Not tracked")])
    devices.update_sampling(untracked.id, 300, tracking_enabled=False)

    ingest.take_reading(tracked.id)                           # the POST /read path
    assert len(received) == 1
    assert received[0].device_id == tracked.id

    ingest.take_reading(untracked.id)
    assert len(received) == 1                                 # tracking off -> not published
    assert len(readings.list_for_device(untracked.id)) == 1   # ...but the row is stored


def test_low_moisture_on_bench1_creates_zone_alert(client, db_session, migrated_db):
    s = seed_benches(migrated_db)
    devices = DeviceRepository(db_session)
    ingest = ReadingIngest(devices, ReadingRepository(db_session), select_sensor_adapter,
                           build_event_bus(db_session))
    sensor = devices.get_device(UUID(s["sensor"]))

    ingest.record(sensor.id, MqttSensorAdapter().translate(sensor, {"value": 0.10, "unit": "vwc"}))

    rows = client.get("/api/alerts", params={"zone_id": s["bench1"]}).json()
    assert len(rows) == 1
    assert rows[0]["event_type"] == "threshold.crossed"
    assert (rows[0]["location_id"], rows[0]["zone_id"]) == (s["loc"], s["bench1"])

    assert client.get("/api/alerts", params={"zone_id": s["bench2"]}).json() == []   # other zone


def test_failed_command_on_unassigned_pump_has_null_ids(client, migrated_db):
    pump = provision(client)["water_pump"]                    # provisioned = unassigned
    assert command(client, "start_pump", pump).status_code == 200
    sql(migrated_db, "UPDATE actuator_states SET updated_at = now() - interval '45 minutes' "
                     "WHERE device_id = :d", d=pump)

    assert command(client, "stop_pump", pump).json()["status"] == "failed"

    rows = client.get("/api/alerts").json()
    assert len(rows) == 1
    assert rows[0]["event_type"] == "command.failed"
    assert rows[0]["message"] == "Max run time exceeded"
    assert rows[0]["location_id"] is None and rows[0]["zone_id"] is None


def test_transition_to_error_inserts_critical_alert(client):
    pump = provision(client)["water_pump"]
    assert command(client, "start_pump", pump).status_code == 200      # idle -> running

    r = client.post(f"/api/devices/{pump}/transition", json={"target": "error"})
    assert r.status_code == 200, r.text

    rows = client.get("/api/alerts").json()
    assert len(rows) == 1
    assert rows[0]["event_type"] == "state.changed"
    assert rows[0]["severity"] == "critical"
    assert rows[0]["message"] == "Actuator entered error"


def test_publishers_do_not_import_alert_repository():
    for module in (reading_service, command_service, transition_service):
        assert "AlertRepository" not in inspect.getsource(module), module.__name__