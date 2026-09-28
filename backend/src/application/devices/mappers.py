from __future__ import annotations
from domain.devices.entity import Device
from application.devices.dto import DeviceDto


def device_to_dto(device: Device) -> DeviceDto:
    if device.id is None:
        raise ValueError("Cannot map unpersisted device (id is None) to DTO")
    return DeviceDto(
        id=device.id,
        device_type=device.device_type,
        role=device.role,
        device_family=device.device_family,
        display_name=device.display_name,
        default_config=device.default_config,
    )


def devices_to_dtos(devices: list[Device]) -> list[DeviceDto]:
    return [device_to_dto(d) for d in devices]