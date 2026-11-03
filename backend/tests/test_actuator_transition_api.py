"""Integration tests: HTTP -> ActuatorStateService -> actuator_states."""
from uuid import uuid4


def provision_actuator_id(client) -> str:
    r = client.post("/api/devices/provision", params={"family": "simulation"})
    assert r.status_code == 201, r.text
    return next(d["id"] for d in r.json() if d["role"] == "actuator")


def provision_sensor_id(client) -> str:
    r = client.post("/api/devices/provision", params={"family": "simulation"})
    assert r.status_code == 201, r.text
    return next(d["id"] for d in r.json() if d["role"] == "sensor")


def test_actuator_starts_idle_with_expected_commands(client):
    actuator_id = provision_actuator_id(client)
    device = next(d for d in client.get("/api/devices").json() if d["id"] == actuator_id)
    assert device["state"] == "idle"
    assert "start_pump" in device["allowed_commands"]


def test_legal_transition_persists(client):
    actuator_id = provision_actuator_id(client)

    r = client.post(f"/api/devices/{actuator_id}/transition", json={"target": "running"})
    assert r.status_code == 200, r.text
    assert r.json()["state"] == "running"
    assert r.json()["allowed_commands"] == ["stop_pump"]

    device = next(d for d in client.get("/api/devices").json() if d["id"] == actuator_id)
    assert device["state"] == "running"


def test_illegal_transition_rejected_and_not_persisted(client):
    actuator_id = provision_actuator_id(client)

    # idle -> running is legal
    r = client.post(f"/api/devices/{actuator_id}/transition", json={"target": "running"})
    assert r.status_code == 200, r.text

    # running -> maintenance is illegal (running's only legal target is idle)
    r = client.post(f"/api/devices/{actuator_id}/transition", json={"target": "maintenance"})
    assert r.status_code == 409

    device = next(d for d in client.get("/api/devices").json() if d["id"] == actuator_id)
    assert device["state"] == "running"  # unchanged by the rejected transition


def test_transition_on_sensor_404(client):
    sensor_id = provision_sensor_id(client)
    r = client.post(f"/api/devices/{sensor_id}/transition", json={"target": "running"})
    assert r.status_code == 404


def test_transition_missing_device_404(client):
    r = client.post(f"/api/devices/{uuid4()}/transition", json={"target": "running"})
    assert r.status_code == 404