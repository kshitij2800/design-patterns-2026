from sqlalchemy import create_engine, inspect


def zone(name, low=0.2, high=0.45, schedule=None):
    return {
        "name": name,
        "moisture_threshold_low": low,
        "moisture_threshold_high": high,
        "schedule": schedule or {},
    }


def create_location(client, name, zones):
    r = client.post("/api/locations/config", json={"location_name": name, "zones": zones})
    assert r.status_code == 201, r.text
    return r.json()


def provision(client):
    r = client.post("/api/devices/provision", params={"family": "simulation"})
    assert r.status_code == 201, r.text
    return [d["id"] for d in r.json()]


def assign(client, device_id, zone_id):
    return client.patch(f"/api/devices/{device_id}/zone", json={"zone_id": zone_id})


def get_device(client, device_id):
    devices = client.get("/api/devices").json()
    return next(d for d in devices if d["id"] == device_id)


def zone_device_ids(client, location_id, zone_id):
    r = client.get(f"/api/locations/{location_id}/zones/{zone_id}/devices")
    assert r.status_code == 200, r.text
    return {d["id"] for d in r.json()}


# ---- Migration check ----

def test_migrations_from_empty_db_reach_head(migrated_db):
    engine = create_engine(migrated_db)
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    assert {"locations", "zones", "devices"} <= tables
    assert "location_id" in {c["name"] for c in insp.get_columns("zones")}
    assert {"zone_id", "location_id"} <= {c["name"] for c in insp.get_columns("devices")}
    all_columns = [c["name"] for t in tables for c in insp.get_columns(t)]
    assert "greenhouse_id" not in all_columns
    engine.dispose()


# ---- Create / read ----

def test_create_config_persists_location_and_zones(client):
    created = create_location(client, "Lab Site A", [zone("Bench 1"), zone("Bench 2", 0.1, 0.3)])
    loc_id = created["location"]["id"]

    r = client.get(f"/api/locations/{loc_id}/config")
    assert r.status_code == 200
    body = r.json()
    assert body["location"] == {"id": loc_id, "name": "Lab Site A"}
    assert sorted(z["name"] for z in body["zones"]) == ["Bench 1", "Bench 2"]


def test_get_config_returns_location_id_on_every_zone(client):
    created = create_location(client, "Lab Site A", [zone("Bench 1"), zone("Bench 2")])
    loc_id = created["location"]["id"]
    body = client.get(f"/api/locations/{loc_id}/config").json()
    assert all(z["location_id"] == loc_id for z in body["zones"])


def test_invalid_payload_returns_400_and_saves_nothing(client):
    r = client.post("/api/locations/config", json={"location_name": "L", "zones": []})
    assert r.status_code == 400
    r = client.post("/api/locations/config", json={"location_name": "L", "zones": [zone("Z", 0.5, 0.2)]})
    assert r.status_code == 400
    assert client.get("/api/locations").json() == []


def test_get_missing_location_returns_404(client):
    r = client.get("/api/locations/00000000-0000-0000-0000-000000000000/config")
    assert r.status_code == 404


# ---- List / delete locations ----

def test_list_locations(client):
    assert client.get("/api/locations").json() == []
    a = create_location(client, "Site A", [zone("Bench 1")])
    b = create_location(client, "Site B", [zone("Bench 1")])
    listed = client.get("/api/locations").json()
    assert [l["id"] for l in listed] == [b["location"]["id"], a["location"]["id"]]  # newest first


def test_delete_location_clears_assignments(client):
    a = create_location(client, "Site A", [zone("Bench 1")])
    b = create_location(client, "Site B", [zone("Bench 1")])
    a_id, a_zone = a["location"]["id"], a["zones"][0]["id"]
    device_id = provision(client)[0]
    assert assign(client, device_id, a_zone).status_code == 200

    assert client.delete(f"/api/locations/{a_id}").status_code == 204
    assert client.get(f"/api/locations/{a_id}/config").status_code == 404
    assert [l["id"] for l in client.get("/api/locations").json()] == [b["location"]["id"]]

    device = get_device(client, device_id)
    assert device["zone_id"] is None
    assert device["location_id"] is None


# ---- Assignment ----

def test_assign_devices_to_zone(client):
    loc = create_location(client, "Site A", [zone("Zone 1"), zone("Zone 2")])
    loc_id = loc["location"]["id"]
    zones = {z["name"]: z["id"] for z in loc["zones"]}
    d = provision(client)

    assert assign(client, d[0], zones["Zone 2"]).status_code == 200
    assert assign(client, d[1], zones["Zone 2"]).status_code == 200
    assert assign(client, d[2], zones["Zone 1"]).status_code == 200

    in_zone_2 = zone_device_ids(client, loc_id, zones["Zone 2"])
    assert in_zone_2 == {d[0], d[1]}
    assert d[2] not in in_zone_2
    assert get_device(client, d[0])["location_id"] == loc_id


def test_unassign_clears_zone_and_location(client):
    loc = create_location(client, "Site A", [zone("Zone 1")])
    zone_id = loc["zones"][0]["id"]
    device_id = provision(client)[0]

    assign(client, device_id, zone_id)
    assert assign(client, device_id, None).status_code == 200
    device = get_device(client, device_id)
    assert device["zone_id"] is None
    assert device["location_id"] is None


def test_assign_missing_device_or_zone_returns_404(client):
    loc = create_location(client, "Site A", [zone("Zone 1")])
    device_id = provision(client)[0]
    missing = "00000000-0000-0000-0000-000000000000"
    assert assign(client, missing, loc["zones"][0]["id"]).status_code == 404
    assert assign(client, device_id, missing).status_code == 404


def test_zone_devices_404_when_zone_not_in_location(client):
    a = create_location(client, "Site A", [zone("Zone 1")])
    b = create_location(client, "Site B", [zone("Zone 1")])
    r = client.get(f"/api/locations/{a['location']['id']}/zones/{b['zones'][0]['id']}/devices")
    assert r.status_code == 404


# ---- Zone management ----

def test_add_zone_to_location(client):
    loc = create_location(client, "Site A", [zone("Bench 1")])
    loc_id = loc["location"]["id"]

    r = client.post(f"/api/locations/{loc_id}/zones", json=zone("Bench 2", 0.25, 0.5))
    assert r.status_code == 201
    assert r.json()["location_id"] == loc_id

    names = sorted(z["name"] for z in client.get(f"/api/locations/{loc_id}/config").json()["zones"])
    assert names == ["Bench 1", "Bench 2"]


def test_update_zone_rejects_invalid_thresholds(client):
    loc = create_location(client, "Site A", [zone("Bench 1", 0.2, 0.45)])
    loc_id, zone_id = loc["location"]["id"], loc["zones"][0]["id"]

    r = client.patch(f"/api/locations/{loc_id}/zones/{zone_id}", json=zone("Bench 1", 0.8, 0.2))
    assert r.status_code == 400

    stored = client.get(f"/api/locations/{loc_id}/config").json()["zones"][0]
    assert stored["moisture_threshold_low"] == 0.2
    assert stored["moisture_threshold_high"] == 0.45


def test_delete_zone_clears_assignments(client):
    loc = create_location(client, "Site A", [zone("Bench 1"), zone("Bench 2")])
    loc_id = loc["location"]["id"]
    zones = {z["name"]: z["id"] for z in loc["zones"]}
    device_id = provision(client)[0]
    assign(client, device_id, zones["Bench 1"])

    assert client.delete(f"/api/locations/{loc_id}/zones/{zones['Bench 1']}").status_code == 204

    device = get_device(client, device_id)
    assert device["zone_id"] is None
    assert device["location_id"] is None
    remaining = [z["name"] for z in client.get(f"/api/locations/{loc_id}/config").json()["zones"]]
    assert remaining == ["Bench 2"]


def test_delete_last_zone_is_rejected(client):
    loc = create_location(client, "Site A", [zone("Bench 1")])
    loc_id, zone_id = loc["location"]["id"], loc["zones"][0]["id"]

    assert client.delete(f"/api/locations/{loc_id}/zones/{zone_id}").status_code == 400
    assert len(client.get(f"/api/locations/{loc_id}/config").json()["zones"]) == 1