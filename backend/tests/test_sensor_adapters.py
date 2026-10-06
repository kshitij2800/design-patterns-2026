"""Adapter unit tests: no database, no HTTP, no broker."""
import socket
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from domain.devices.entity import Device
from infrastructure.adapters.actuators.simulation import SimulationActuatorAdapter
from infrastructure.adapters.sensors.mqtt import MqttSensorAdapter
from infrastructure.adapters.sensors.simulation import SIMULATION_RANGES, SimulationSensorAdapter
from infrastructure.adapters.sensors.vendor_stub import VendorStubSensorAdapter


def make_device(device_type="moisture_sensor") -> Device:
    return Device(
        id=uuid4(),
        device_type=device_type,
        role="sensor",
        device_family="simulation",
        display_name="Test",
        default_config={"protocol": "simulation"},
    )


def test_vendor_adapter_normalizes_raw_payload():
    device = make_device("moisture_sensor")
    raw = {"channel": "SOIL", "reading_x100": 4100, "uom": "PCT_VWC", "epoch_ms": 1_790_000_000_000}

    reading = VendorStubSensorAdapter().translate(device, raw)

    assert reading.device_id == device.id
    assert reading.value == pytest.approx(0.41)          # 41.00 % -> 0.41 vwc
    assert reading.unit == "vwc"
    assert reading.source == "vendor"
    assert reading.recorded_at == datetime.fromtimestamp(1_790_000_000, tz=timezone.utc)


@pytest.mark.parametrize("device_type", ["moisture_sensor", "light_sensor"])
def test_simulation_adapter_value_in_range(device_type):
    low, high, unit = SIMULATION_RANGES[device_type]
    adapter = SimulationSensorAdapter()
    for _ in range(200):
        reading = adapter.read(make_device(device_type))
        assert low <= reading.value <= high
        assert reading.unit == unit
        assert reading.source == "simulation"


def test_simulation_and_vendor_give_different_source():
    device = make_device("light_sensor")
    assert SimulationSensorAdapter().read(device).source == "simulation"
    assert VendorStubSensorAdapter().read(device).source == "vendor"


def test_mqtt_adapter_translates_payload(monkeypatch):
    def no_sockets(*args, **kwargs):
        raise AssertionError("MQTT translation must not open a socket")
    monkeypatch.setattr(socket, "socket", no_sockets)

    device = make_device("moisture_sensor")
    reading = MqttSensorAdapter().translate(device, {"value": 0.41, "unit": "vwc"})

    assert reading.device_id == device.id
    assert reading.value == 0.41
    assert reading.unit == "vwc"
    assert reading.source == "mqtt"


def test_simulation_actuator_apply_records_command():
    actuator = SimulationActuatorAdapter()
    device_id = uuid4()
    actuator.apply(device_id, "start", {"duration_seconds": 30})

    assert len(actuator.applied) == 1
    assert actuator.applied[0].command == "start"