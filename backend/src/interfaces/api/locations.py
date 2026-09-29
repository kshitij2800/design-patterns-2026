from __future__ import annotations
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from application.devices.dto import DeviceDto
from application.locations.config_service import LocationConfigService
from application.locations.dto import (
    LocationConfigReadDto,
    LocationConfigRequestDto,
    LocationSummaryDto,
    ZoneReadDto,
    ZoneRequestDto,
)
from application.locations.mappers import device_row_to_dto, zone_row_to_dto
from application.locations.zone_assignment_service import ZoneAssignmentService, ZoneNotFoundError
from application.locations.zone_management_service import LocationNotFoundError, ZoneManagementService
from domain.locations.errors import ConfigurationError
from infrastructure.db import get_db
from infrastructure.persistence.location_repository import LocationRepository

router = APIRouter(prefix="/api/locations", tags=["locations"])


def get_service(db: Session = Depends(get_db)) -> LocationConfigService:
    return LocationConfigService(LocationRepository(db))


def get_repo(db: Session = Depends(get_db)) -> LocationRepository:
    return LocationRepository(db)


def get_assignment_service(db: Session = Depends(get_db)) -> ZoneAssignmentService:
    return ZoneAssignmentService(db)


def get_zone_service(db: Session = Depends(get_db)) -> ZoneManagementService:
    return ZoneManagementService(db)


@router.post("/config", response_model=LocationConfigReadDto, status_code=201)
def create_config(
    request: LocationConfigRequestDto,
    service: LocationConfigService = Depends(get_service),
):
    try:
        return service.build_and_save(request)
    except ConfigurationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=list[LocationSummaryDto])
def list_locations(repo: LocationRepository = Depends(get_repo)):
    """List all locations, newest first."""
    rows = repo.list_locations()
    return [LocationSummaryDto(id=UUID(r.id), name=r.name) for r in rows]


@router.get("/{location_id}/config", response_model=LocationConfigReadDto)
def get_config(
    location_id: UUID,
    service: LocationConfigService = Depends(get_service),
):
    result = service.get(location_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Location not found")
    return result


@router.delete("/{location_id}", status_code=204)
def delete_location(
    location_id: UUID,
    repo: LocationRepository = Depends(get_repo),
):
    if not repo.delete_location(location_id):
        raise HTTPException(status_code=404, detail="Location not found")


@router.get("/{location_id}/zones/{zone_id}/devices", response_model=list[DeviceDto])
def list_zone_devices(
    location_id: UUID,
    zone_id: UUID,
    service: ZoneAssignmentService = Depends(get_assignment_service),
):
    try:
        rows = service.list_devices_in_zone(location_id, zone_id)
    except ZoneNotFoundError:
        raise HTTPException(status_code=404, detail="Zone not found in this location")
    return [device_row_to_dto(r) for r in rows]


@router.post("/{location_id}/zones", response_model=ZoneReadDto, status_code=201)
def add_zone(
    location_id: UUID,
    body: ZoneRequestDto,
    service: ZoneManagementService = Depends(get_zone_service),
):
    try:
        return zone_row_to_dto(service.add_zone(location_id, body))
    except LocationNotFoundError:
        raise HTTPException(status_code=404, detail="Location not found")
    except ConfigurationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{location_id}/zones/{zone_id}", response_model=ZoneReadDto)
def update_zone(
    location_id: UUID,
    zone_id: UUID,
    body: ZoneRequestDto,
    service: ZoneManagementService = Depends(get_zone_service),
):
    try:
        return zone_row_to_dto(service.update_zone(location_id, zone_id, body))
    except (LocationNotFoundError, ZoneNotFoundError):
        raise HTTPException(status_code=404, detail="Zone not found in this location")
    except ConfigurationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{location_id}/zones/{zone_id}", status_code=204)
def delete_zone(
    location_id: UUID,
    zone_id: UUID,
    service: ZoneManagementService = Depends(get_zone_service),
):
    try:
        service.delete_zone(location_id, zone_id)
    except (LocationNotFoundError, ZoneNotFoundError):
        raise HTTPException(status_code=404, detail="Zone not found in this location")
    except ConfigurationError as e:
        raise HTTPException(status_code=400, detail=str(e))