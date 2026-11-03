from __future__ import annotations
from uuid import UUID

from application.devices.dto import ActuatorStateDto
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from application.devices.dto import (
    ActuatorStateDto,
    StateTransitionRequestDto,
)

from application.devices.dto import DeviceDto
from application.devices.mappers import devices_to_dtos
from application.devices.family_service import DeviceFamilyService
from application.devices.sampling_service import DeviceSamplingService
from application.devices.actuator_state_service import ActuatorStateService
from application.readings.errors import DeviceNotFoundError as ActuatorDeviceNotFoundError
from domain.actuators.state import IllegalTransitionError, allowed_commands_for
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
from infrastructure.persistence.actuator_state_repository import ActuatorStateRepository


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
    db: Session = Depends(get_db),
):
    devices = service.list_devices(device_family=family, role=role)
    actuator_ids = [d.id for d in devices if d.role == "actuator"]
    states = ActuatorStateRepository(db).get_states(actuator_ids)
    return devices_to_dtos(devices, states)


@router.post("/provision", response_model=list[DeviceDto], status_code=201)
def provision_family(
    family: str,
    service: DeviceFamilyService = Depends(get_service),
    db: Session = Depends(get_db),
):
    try:
        devices = service.provision_family(family)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    actuator_ids = [d.id for d in devices if d.role == "actuator"]
    states = ActuatorStateRepository(db).get_states(actuator_ids)
    return devices_to_dtos(devices, states)


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

def get_actuator_state_service(db: Session = Depends(get_db)) -> ActuatorStateService:
    return ActuatorStateService(DeviceRepository(db), ActuatorStateRepository(db))


@router.post("/{device_id}/transition", response_model=ActuatorStateDto)
def transition_device(
    device_id: UUID,
    body: StateTransitionRequestDto,
    service: ActuatorStateService = Depends(get_actuator_state_service),
):
    """Guarded state transition for one actuator. 404 missing actuator, 409 illegal transition."""
    try:
        new_state = service.transition(device_id, body.target)
    except ActuatorDeviceNotFoundError:
        raise HTTPException(status_code=404, detail="Actuator not found")
    except IllegalTransitionError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return ActuatorStateDto(
        device_id=device_id,
        state=new_state,
        allowed_commands=allowed_commands_for(new_state),
    )