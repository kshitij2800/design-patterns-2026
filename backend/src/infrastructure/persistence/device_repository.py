from __future__ import annotations
from uuid import UUID
from sqlalchemy.orm import Session
from domain.devices.entity import Device
from infrastructure.persistence.models import DeviceRow


def _row_to_device(row: DeviceRow) -> Device:
    return Device(
        id=UUID(row.id),
        device_type=row.device_type,
        role=row.role,
        device_family=row.device_family,
        display_name=row.display_name or "",
        default_config=row.default_config,
        zone_id=UUID(row.zone_id) if row.zone_id else None,
        location_id=UUID(row.location_id) if row.location_id else None,
    )


def _device_to_row(device: Device) -> DeviceRow:
    return DeviceRow(
        device_type=device.device_type,
        role=device.role,
        device_family=device.device_family,
        display_name=device.display_name,
        default_config=device.default_config,
    )


class DeviceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save_device(self, device: Device) -> Device:
        row = _device_to_row(device)
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return _row_to_device(row)

    def save_devices(self, devices: list[Device]) -> list[Device]:
        rows = [_device_to_row(d) for d in devices]
        for row in rows:
            self._session.add(row)
        self._session.commit()
        for row in rows:
            self._session.refresh(row)
        return [_row_to_device(row) for row in rows]

    def list_devices(
        self,
        *,
        device_family: str | None = None,
        role: str | None = None,
    ) -> list[Device]:
        query = self._session.query(DeviceRow)
        if device_family is not None:
            query = query.filter(DeviceRow.device_family == device_family)
        if role is not None:
            query = query.filter(DeviceRow.role == role)
        return [_row_to_device(row) for row in query.all()]

    def save_sensor(self, sensor) -> object:
        from domain.sensors.entity import Sensor
        row = DeviceRow(
            device_type=sensor.device_type,
            role="sensor",
            device_family="simulation",
            display_name=sensor.display_name,
            default_config=sensor.default_config,
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return Sensor(
            id=UUID(row.id),
            device_type=row.device_type,
            display_name=row.display_name or "",
            default_config=row.default_config,
        )

    def list_sensors(self) -> list[object]:
        from domain.sensors.entity import Sensor
        rows = (
            self._session.query(DeviceRow)
            .filter(DeviceRow.role == "sensor")
            .all()
        )
        return [
            Sensor(
                id=UUID(row.id),
                device_type=row.device_type,
                display_name=row.display_name or "",
                default_config=row.default_config,
            )
            for row in rows
        ]