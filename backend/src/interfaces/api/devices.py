from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from application.devices.dto import DeviceDto
from application.devices.mappers import devices_to_dtos
from application.devices.family_service import DeviceFamilyService
from infrastructure.db import get_db
from infrastructure.persistence.device_repository import DeviceRepository
from uuid import UUID
from application.locations.dto import ZoneAssignmentRequestDto
from application.locations.zone_assignment_service import (
    ZoneAssignmentService,
    DeviceNotFoundError,
    ZoneNotFoundError,
)
from infrastructure.db import get_db

router = APIRouter(prefix="/api/devices", tags=["devices"])


def get_service(db: Session = Depends(get_db)) -> DeviceFamilyService:
    return DeviceFamilyService(DeviceRepository(db))


@router.get("", response_model=list[DeviceDto])
def list_devices(
    family: str | None = None,
    role: str | None = None,
    service: DeviceFamilyService = Depends(get_service),
):
    devices = service.list_devices(device_family=family, role=role)
    return devices_to_dtos(devices)


@router.post("/provision", response_model=list[DeviceDto], status_code=201)
def provision_family(
    family: str,
    service: DeviceFamilyService = Depends(get_service),
):
    try:
        devices = service.provision_family(family)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return devices_to_dtos(devices)

def get_assignment_service(db: Session = Depends(get_db)) -> ZoneAssignmentService:
    return ZoneAssignmentService(db)

router.patch("/{device_id}/zone", status_code=200)
def assign_zone(
    device_id: UUID,
    body: ZoneAssignmentRequestDto,
    service: ZoneAssignmentService = Depends(get_assignment_service),
):
    try:
        service.assign(device_id, body.zone_id)
    except (DeviceNotFoundError, ZoneNotFoundError) as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"device_id": str(device_id), "zone_id": str(body.zone_id) if body.zone_id else None}