from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from application.actuators.dto import ExecutionDto
from application.actuators.service import ActuatorCommandService
from domain.actuators.ports import ActuatorPort
from infrastructure.adapters.actuators.logging_decorator import LoggingActuatorDecorator
from infrastructure.adapters.actuators.max_runtime_decorator import MaxRunTimeActuatorDecorator
from infrastructure.adapters.actuators.simulation import SimulationActuatorAdapter
from infrastructure.db import get_db
from infrastructure.persistence.actuator_state_repository import ActuatorStateRepository
from infrastructure.persistence.execution_log_repository import ExecutionLogRepository

router = APIRouter(prefix="/api/actuators", tags=["actuators"])


def build_actuator_port(db: Session) -> ActuatorPort:
    # Composition order: logging (outermost) -> max-run-time -> simulation (innermost)
    core = SimulationActuatorAdapter()
    guarded = MaxRunTimeActuatorDecorator(core, ActuatorStateRepository(db))
    return LoggingActuatorDecorator(guarded, ExecutionLogRepository(db))


def get_service(db: Session = Depends(get_db)) -> ActuatorCommandService:
    return ActuatorCommandService(build_actuator_port(db), ExecutionLogRepository(db))


@router.get("/executions", response_model=list[ExecutionDto])
def list_executions(limit: int = 20, service: ActuatorCommandService = Depends(get_service)):
    return service.list_recent(limit)