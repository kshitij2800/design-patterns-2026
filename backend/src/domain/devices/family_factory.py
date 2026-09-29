from __future__ import annotations
from abc import ABC, abstractmethod
from uuid import UUID
from domain.devices.entity import Device
from domain.sensors.creators import MoistureSensorCreator, LightSensorCreator

def _sensor_to_device(sensor_type: str, display_name: str, config: dict, family: str) -> Device:
    """Convert a sensor creator's output fields into a unified Device."""
    return Device(
        id=None,
        device_type=sensor_type,
        role="sensor",
        device_family=family,
        display_name=display_name,
        default_config=config,
    )


def _make_actuator(device_type: str, display_name: str, config: dict, family: str) -> Device:
    """Build an actuator Device directly (no Phase 2 creator for actuators)."""
    return Device(
        id=None,
        device_type=device_type,
        role="actuator",
        device_family=family,
        display_name=display_name,
        default_config=config,
    )


class DeviceFamilyFactory(ABC):
    @property
    @abstractmethod
    def family_key(self) -> str: ...

    @abstractmethod
    def create_device_set(self) -> list[Device]: ...



class SimulationDeviceFactory(DeviceFamilyFactory):
    @property
    def family_key(self) -> str:
        return "simulation"

    def create_device_set(self) -> list[Device]:
        family = self.family_key

        # Compose Phase 2 creators — call them, then convert to Device
        moisture = MoistureSensorCreator().create_sensor("Sim Moisture Sensor")
        light = LightSensorCreator().create_sensor("Sim Light Sensor")

        return [
            _sensor_to_device(
                moisture.device_type,
                moisture.display_name,
                {**moisture.default_config, "protocol": "sim"},
                family,
            ),
            _sensor_to_device(
                light.device_type,
                light.display_name,
                {**light.default_config, "protocol": "sim"},
                family,
            ),
            _make_actuator("water_pump",  "Sim Irrigation Pump", {"protocol": "sim", "flow_rate_lph": 12}, family),
            _make_actuator("grow_light",  "Sim Grow Light",      {"protocol": "sim", "spectrum": "full"}, family),
        ]



class EdgeHardwareFactory(DeviceFamilyFactory):
    @property
    def family_key(self) -> str:
        return "edge"

    def create_device_set(self) -> list[Device]:
        family = self.family_key

        # Same creators, different display names and protocol
        moisture = MoistureSensorCreator().create_sensor("Edge Moisture Sensor")
        light = LightSensorCreator().create_sensor("Edge Light Sensor")

        return [
            _sensor_to_device(
                moisture.device_type,
                moisture.display_name,
                {**moisture.default_config, "protocol": "gpio-stub"},
                family,
            ),
            _sensor_to_device(
                light.device_type,
                light.display_name,
                {**light.default_config, "protocol": "gpio-stub"},
                family,
            ),
            _make_actuator("water_pump", "Edge Pump",       {"protocol": "gpio-stub", "pin": 17}, family),
            _make_actuator("grow_light", "Edge Grow Light", {"protocol": "gpio-stub", "pin": 18}, family),
        ]


_FACTORIES: dict[str, DeviceFamilyFactory] = {
    "simulation": SimulationDeviceFactory(),
    "edge":       EdgeHardwareFactory(),
}


def get_family_factory(family: str) -> DeviceFamilyFactory:
    factory = _FACTORIES.get(family)
    if factory is None:
        raise ValueError(f"Unknown device family: '{family}'. Valid families: {list(_FACTORIES)}")
    return factory