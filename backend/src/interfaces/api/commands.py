from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from application.commands.dto import CommandLogDto, CommandRequestDto
from application.commands.service import CommandRejectedError, CommandService
from application.readings.errors import DeviceNotFoundError
from domain.commands.invoker import UnknownCommandError
from infrastructure.db import get_db
from infrastructure.persistence.actuator_state_repository import ActuatorStateRepository
from infrastructure.persistence.command_log_repository import CommandLogRepository
from infrastructure.persistence.device_repository import DeviceRepository
from interfaces.api.actuators import build_actuator_port

router = APIRouter(prefix="/api/commands", tags=["commands"])


def get_service(db: Session = Depends(get_db)) -> CommandService:
    return CommandService(
        DeviceRepository(db),
        ActuatorStateRepository(db),
        CommandLogRepository(db),
        build_actuator_port(db),
    )


@router.post(
    "",
    response_model=CommandLogDto,
    responses={
        400: {"description": "Unknown command_type (no row written)"},
        404: {"description": "Device missing or not an actuator"},
        409: {"model": CommandLogDto, "description": "Not allowed in current state (row status 'rejected')"},
    },
)
def execute_command(body: CommandRequestDto, service: CommandService = Depends(get_service)):
    """Run a command. 200 with the log row for `success` and `failed`; 409 with the row for `rejected`."""
    try:
        return service.execute(body)
    except DeviceNotFoundError:
        raise HTTPException(status_code=404, detail="Actuator not found")
    except UnknownCommandError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except CommandRejectedError as e:
        return JSONResponse(status_code=409, content=jsonable_encoder(e.log_row))


@router.get("", response_model=list[CommandLogDto])
def list_commands(
    limit: int = Query(50, ge=1, le=200),
    service: CommandService = Depends(get_service),
):
    """Command history, newest first."""
    return service.list_history(limit)