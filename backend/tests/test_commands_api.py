"""Integration: HTTP -> CommandService -> state guard -> decorated port -> actuator_states + command_log."""


def provision_pump_id(client) -> str:
    r = client.post("/api/devices/provision", params={"family": "simulation"})
    assert r.status_code == 201, r.text
    return next(d["id"] for d in r.json() if d["device_type"] == "water_pump")


def state_of(client, device_id) -> str:
    return next(d for d in client.get("/api/devices").json() if d["id"] == device_id)["state"]


def test_illegal_command_rejected_logged(client):
    pump = provision_pump_id(client)                     # starts idle

    r = client.post("/api/commands", json={"command_type": "stop_pump", "device_id": pump})
    assert r.status_code == 409, r.text
    assert r.json()["status"] == "rejected"

    assert state_of(client, pump) == "idle"              # actuator_states unchanged
    assert r.json()["id"] in {row["id"] for row in client.get("/api/commands").json()}


def test_start_pump_transitions_to_running(client):
    pump = provision_pump_id(client)

    r = client.post("/api/commands", json={"command_type": "start_pump", "device_id": pump})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "success"

    assert state_of(client, pump) == "running"
    assert client.get("/api/commands").json()[0]["id"] == r.json()["id"]