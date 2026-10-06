"""Adapter selection rule (the only place that knows concrete sensor adapter classes).

1. default_config["adapter"] == "vendor_stub"  -> VendorStubSensorAdapter  (checked first)
2. default_config["protocol"] == "simulation"  -> SimulationSensorAdapter  (also the default)
3. default_config["protocol"] == "mqtt"        -> no on-demand read: MQTT devices push data;
                                                  their payloads go through MqttSensorAdapter.translate
"""
from __future__ import annotations
from domain.devices.entity import Device
from domain.sensors.errors import SensorReadError
from domain.sensors.ports import SensorPort
from infrastructure.adapters.sensors.simulation import SimulationSensorAdapter
from infrastructure.adapters.sensors.vendor_stub import VendorStubSensorAdapter

VENDOR_STUB_FLAG = "vendor_stub"

_simulation = SimulationSensorAdapter()
_vendor = VendorStubSensorAdapter()


def select_sensor_adapter(device: Device) -> SensorPort:
    if device.default_config.get("adapter") == VENDOR_STUB_FLAG:
        return _vendor
    if device.protocol == "simulation":
        return _simulation
    if device.protocol == "mqtt":
        raise SensorReadError(
            "MQTT devices push their readings; on-demand read is not supported"
        )
    raise SensorReadError(f"Unknown protocol '{device.protocol}'")