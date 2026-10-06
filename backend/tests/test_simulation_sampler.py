"""Sampler tests with a fake clock: no HTTP, no broker, no sleeping."""
from datetime import datetime, timedelta, timezone

from application.readings.sampler import SimulationSampler
from application.readings.service import ReadingIngest
from domain.devices.entity import Device
from infrastructure.adapters.sensors.mqtt import MqttSensorAdapter
from infrastructure.adapters.sensors.selector import select_sensor_adapter
from infrastructure.persistence.device_repository import DeviceRepository
from infrastructure.persistence.reading_repository import ReadingRepository

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


def sensor(protocol: str, name: str) -> Device:
    return Device(
        id=None,
        device_type="moisture_sensor",
        role="sensor",
        device_family="simulation" if protocol == "simulation" else "edge",
        display_name=name,
        default_config={"protocol": protocol},
    )


def build(db_session):
    devices = DeviceRepository(db_session)
    readings = ReadingRepository(db_session)
    ingest = ReadingIngest(devices, readings, select_sensor_adapter)
    sampler = SimulationSampler(devices, readings, ingest, select_sensor_adapter)
    return devices, readings, ingest, sampler


def count(readings, device):
    return len(readings.list_for_device(device.id, limit=100))


def test_sampler_respects_interval_and_tracking(db_session):
    devices, readings, _, sampler = build(db_session)
    sim, disabled, mqtt = devices.save_devices([
        sensor("simulation", "Sim"),
        sensor("simulation", "Sim (tracking off)"),
        sensor("mqtt", "Edge"),
    ])
    devices.update_sampling(sim.id, 60, tracking_enabled=True)
    devices.update_sampling(disabled.id, 60, tracking_enabled=False)

    sampler.run_once(T0)                                    # no previous row -> due
    assert count(readings, sim) == 1

    sampler.run_once(T0 + timedelta(seconds=30))            # inside the 60 s interval
    assert count(readings, sim) == 1

    sampler.run_once(T0 + timedelta(seconds=60))            # interval elapsed
    assert count(readings, sim) == 2

    assert count(readings, disabled) == 0                   # tracking off
    assert count(readings, mqtt) == 0                       # MQTT skipped


def test_record_persists_translated_mqtt_reading(db_session):
    devices, readings, ingest, _ = build(db_session)
    (mqtt,) = devices.save_devices([sensor("mqtt", "Edge")])
    reading = MqttSensorAdapter().translate(mqtt, {"value": 0.33, "unit": "vwc"})

    dto = ingest.record(mqtt.id, reading)

    assert dto.source == "mqtt"
    assert count(readings, mqtt) == 1