from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from application.readings.dto import ReadingDto
from application.readings.errors import DeviceNotFoundError
from application.readings.service import ReadingIngest
from application.sensors.service import SensorService
from domain.sensors.errors import SensorReadError
from infrastructure.adapters.sensors.selector import select_sensor_adapter
from infrastructure.db import get_db
from infrastructure.persistence.device_repository import DeviceRepository
from infrastructure.persistence.reading_repository import ReadingRepository

router = APIRouter(prefix="/api/sensors", tags=["sensors"])


class CreateSensorRequest(BaseModel):
    type: str
    display_name: str | None = None


class SensorResponse(BaseModel):
    id: UUID
    device_type: str
    display_name: str
    default_config: dict
    sampling_interval_seconds: int
    tracking_enabled: bool


def _to_response(s) -> SensorResponse:
    return SensorResponse(
        id=s.id,
        device_type=s.device_type,
        display_name=s.display_name,
        default_config=s.default_config,
        sampling_interval_seconds=s.sampling_interval_seconds,
        tracking_enabled=s.tracking_enabled,
    )


def get_service(db: Session = Depends(get_db)) -> SensorService:
    return SensorService(DeviceRepository(db))


@router.get("", response_model=list[SensorResponse])
def list_sensors(service: SensorService = Depends(get_service)):
    return [_to_response(s) for s in service.list_sensors()]


@router.post("", response_model=SensorResponse, status_code=201)
def create_sensor(body: CreateSensorRequest, service: SensorService = Depends(get_service)):
    try:
        sensor = service.create_sensor(body.type, body.display_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _to_response(sensor)


# ---- Phase 5: readings ----

def get_ingest(db: Session = Depends(get_db)) -> ReadingIngest:
    return ReadingIngest(DeviceRepository(db), ReadingRepository(db), select_sensor_adapter)


@router.post("/{sensor_id}/read", response_model=ReadingDto, status_code=201)
def read_sensor(sensor_id: UUID, ingest: ReadingIngest = Depends(get_ingest)):
    """Read the sensor now through its adapter, store the reading, return it."""
    try:
        return ingest.take_reading(sensor_id)
    except DeviceNotFoundError:
        raise HTTPException(status_code=404, detail="Sensor not found")
    except SensorReadError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{sensor_id}/readings", response_model=list[ReadingDto])
def list_readings(
    sensor_id: UUID,
    limit: int = 20,
    ingest: ReadingIngest = Depends(get_ingest),
):
    """Stored readings for this sensor, newest first."""
    try:
        return ingest.list_readings(sensor_id, limit)
    except DeviceNotFoundError:
        raise HTTPException(status_code=404, detail="Sensor not found")