from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from application.sensors.service import SensorService
from infrastructure.db import get_db
from infrastructure.persistence.device_repository import DeviceRepository

router = APIRouter(prefix="/api/sensors", tags=["sensors"])


class CreateSensorRequest(BaseModel):
    type: str
    display_name: str | None = None


class SensorResponse(BaseModel):
    id: UUID
    device_type: str
    display_name: str
    default_config: dict


def get_service(db: Session = Depends(get_db)) -> SensorService:
    return SensorService(DeviceRepository(db))


@router.get("", response_model=list[SensorResponse])
def list_sensors(service: SensorService = Depends(get_service)):
    return [
        SensorResponse(
            id=s.id,
            device_type=s.device_type,
            display_name=s.display_name,
            default_config=s.default_config,
        )
        for s in service.list_sensors()
    ]


@router.post("", response_model=SensorResponse, status_code=201)
def create_sensor(body: CreateSensorRequest, service: SensorService = Depends(get_service)):
    try:
        sensor = service.create_sensor(body.type, body.display_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return SensorResponse(
        id=sensor.id,
        device_type=sensor.device_type,
        display_name=sensor.display_name,
        default_config=sensor.default_config,
    )