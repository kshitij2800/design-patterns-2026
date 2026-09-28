from domain.devices.family_factory import (
    SimulationDeviceFactory,
    EdgeHardwareFactory,
    get_family_factory,
)


def test_simulation_factory_returns_four_devices():
    factory = SimulationDeviceFactory()
    devices = factory.create_device_set()
    assert len(devices) == 4
    roles = {d.role for d in devices}
    assert roles == {"sensor", "actuator"}
    assert all(d.device_family == "simulation" for d in devices)


def test_edge_factory_differs_from_simulation():
    sim = SimulationDeviceFactory().create_device_set()
    edge = EdgeHardwareFactory().create_device_set()
    assert all(d.device_family == "edge" for d in edge)
    sim_protocols = {d.default_config.get("protocol") for d in sim}
    edge_protocols = {d.default_config.get("protocol") for d in edge}
    assert sim_protocols != edge_protocols


def test_unknown_family_raises_value_error():
    try:
        get_family_factory("nonexistent")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass