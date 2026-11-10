from datetime import datetime, timedelta, timezone
from uuid import uuid4

from domain.actuators.errors import PolicyBlockedError
from domain.devices.entity import Device
from infrastructure.adapters.actuators.logging_decorator import LoggingActuatorDecorator
from infrastructure.adapters.actuators.max_runtime_decorator import MaxRunTimeActuatorDecorator
from infrastructure.adapters.actuators.simulation import SimulationActuatorAdapter
from infrastructure.persistence.device_repository import DeviceRepository
from infrastructure.persistence.execution_log_repository import ExecutionLogRepository


class FakeStateRow:
    def __init__(self, state, updated_at):
        self.state = state
        self.updated_at = updated_at


class FakeStateRepo:
    def __init__(self, row):
        self._row = row

    def get_row(self, device_id):
        return self._row


def make_actuator(db_session):
    devices = DeviceRepository(db_session)
    (d,) = devices.save_devices([Device(
        id=None, device_type="pump", role="actuator", device_family="simulation",
        display_name="Test pump", default_config={},
    )])
    return d


def test_max_runtime_does_not_call_inner():
    calls = []

    class SpyAdapter:
        def apply(self, device_id, command, payload):
            calls.append((device_id, command, payload))

    old = datetime.now(timezone.utc) - timedelta(minutes=45)
    decorator = MaxRunTimeActuatorDecorator(SpyAdapter(), FakeStateRepo(FakeStateRow("running", old)))

    try:
        decorator.apply(uuid4(), "start_pump", {})
        assert False, "expected PolicyBlockedError"
    except PolicyBlockedError as e:
        assert e.policy_name == "maxRunTime"
    assert calls == []


def test_failed_policy_writes_execution_row(db_session):
    device = make_actuator(db_session)
    old = datetime.now(timezone.utc) - timedelta(minutes=45)
    log_repo = ExecutionLogRepository(db_session)

    chain = LoggingActuatorDecorator(
        MaxRunTimeActuatorDecorator(SimulationActuatorAdapter(), FakeStateRepo(FakeStateRow("running", old))),
        log_repo,
    )
    chain.apply(device.id, "start_pump", {})

    row = log_repo.list_recent(1)[0]
    assert row.success is False
    assert row.policy_applied == ["maxRunTime", "logging"]
    assert row.message == "Max run time exceeded"


def test_successful_apply_logs_logging_only(db_session):
    device = make_actuator(db_session)
    log_repo = ExecutionLogRepository(db_session)

    chain = LoggingActuatorDecorator(
        MaxRunTimeActuatorDecorator(SimulationActuatorAdapter(), FakeStateRepo(None)),
        log_repo,
    )
    chain.apply(device.id, "start_pump", {})

    row = log_repo.list_recent(1)[0]
    assert row.success is True
    assert row.policy_applied == ["logging"]
    assert row.message is None