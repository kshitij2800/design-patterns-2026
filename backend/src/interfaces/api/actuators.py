from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from application.actuators.dto import ApplyCommandDto, ExecutionDto
from application.actuators.service import ActuatorCommandService
from infrastructure.adapters.actuators.logging_decorator import LoggingActuatorDecorator
from infrastructure.adapters.actuators.max_runtime_decorator import MaxRunTimeActuatorDecorator
from infrastructure.adapters.actuators.simulation import SimulationActuatorAdapter
from infrastructure.db import get_db
from infrastructure.persistence.actuator_state_repository import ActuatorStateRepository
from infrastructure.persistence.execution_log_repository import ExecutionLogRepository

router = APIRouter(prefix="/api/actuators", tags=["actuators"])


def get_service(db: Session = Depends(get_db)) -> ActuatorCommandService:
    log_repo = ExecutionLogRepository(db)
    states = ActuatorStateRepository(db)
    # Composition order: logging (outermost) -> max-run-time -> simulation (innermost)
    core = SimulationActuatorAdapter()
    guarded = MaxRunTimeActuatorDecorator(core, states)
    decorated = LoggingActuatorDecorator(guarded, log_repo)
    return ActuatorCommandService(decorated, log_repo)


@router.get("/executions", response_model=list[ExecutionDto])
def list_executions(limit: int = 20, service: ActuatorCommandService = Depends(get_service)):
    return service.list_recent(limit)


# Demo only — Phase 10 (Command) replaces this with the real command route.
@router.post("/{device_id}/apply", status_code=202)
def apply_demo(
    device_id: UUID, body: ApplyCommandDto, service: ActuatorCommandService = Depends(get_service)
):
    service.apply(device_id, body.command, body.payload)
    return {"status": "accepted"}