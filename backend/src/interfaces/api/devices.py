from __future__ import annotations
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from application.devices.dto import DeviceDto
from application.devices.mappers import devices_to_dtos
from application.devices.family_service import DeviceFamilyService
from application.devices.sampling_service import DeviceSamplingService
from application.readings.dto import SamplingDto, SamplingUpdateDto
from application.readings.errors import DeviceNotFoundError as SamplingDeviceNotFoundError
from domain.devices.sampling import InvalidSamplingIntervalError
from application.locations.dto import ZoneAssignmentRequestDto
from application.locations.zone_assignment_service import (
    ZoneAssignmentService,
    DeviceNotFoundError,
    ZoneNotFoundError,
)
from infrastructure.db import get_db
from infrastructure.persistence.device_repository import DeviceRepository

router = APIRouter(prefix="/api/devices", tags=["devices"])


def get_service(db: Session = Depends(get_db)) -> DeviceFamilyService:
    return DeviceFamilyService(DeviceRepository(db))


def get_assignment_service(db: Session = Depends(get_db)) -> ZoneAssignmentService:
    return ZoneAssignmentService(db)


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


@router.patch("/{device_id}/zone")
def assign_zone(
    device_id: UUID,
    body: ZoneAssignmentRequestDto,
    service: ZoneAssignmentService = Depends(get_assignment_service),
):
    try:
        service.assign(device_id, body.zone_id)
    except DeviceNotFoundError:
        raise HTTPException(status_code=404, detail="Device not found")
    except ZoneNotFoundError:
        raise HTTPException(status_code=404, detail="Zone not found")
    return {"device_id": str(device_id), "zone_id": str(body.zone_id) if body.zone_id else None}


def get_sampling_service(db: Session = Depends(get_db)) -> DeviceSamplingService:
    return DeviceSamplingService(DeviceRepository(db))


@router.patch("/{device_id}/sampling", response_model=SamplingDto)
def update_sampling(
    device_id: UUID,
    body: SamplingUpdateDto,
    service: DeviceSamplingService = Depends(get_sampling_service),
):
    """Set how often the simulation sampler reads this device, and whether it tracks it."""
    try:
        return service.update(device_id, body)
    except InvalidSamplingIntervalError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SamplingDeviceNotFoundError:
        raise HTTPException(status_code=404, detail="Device not found")