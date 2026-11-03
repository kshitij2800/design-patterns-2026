from __future__ import annotations
from uuid import UUID

from domain.devices.entity import Device
from domain.actuators.state import allowed_commands_for
from application.devices.dto import DeviceDto


def device_to_dto(device: Device, actuator_states: dict[UUID, str] | None = None) -> DeviceDto:
    if device.id is None:
        raise ValueError("Cannot map unpersisted device (id is None) to DTO")
    actuator_states = actuator_states or {}
    dto = DeviceDto(
        id=device.id,
        device_type=device.device_type,
        role=device.role,
        device_family=device.device_family,
        display_name=device.display_name,
        default_config=device.default_config,
        zone_id=device.zone_id,
        location_id=device.location_id,
    )
    if device.role == "actuator":
        state = actuator_states.get(device.id, "idle")
        dto.state = state
        dto.allowed_commands = allowed_commands_for(state)
    return dto


def devices_to_dtos(devices: list[Device], actuator_states: dict[UUID, str] | None = None) -> list[DeviceDto]:
    actuator_states = actuator_states or {}
    return [device_to_dto(d, actuator_states) for d in devices]