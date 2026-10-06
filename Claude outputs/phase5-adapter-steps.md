# Phase 5 — Adapter: step-by-step guide

Written against your actual repo (`~/greenhouse-project`, Phase 4 head `28075874ce60`). Every file below was run end-to-end in a copy of your project: **45 tests pass** (your 33 old + 12 new), the migration upgrades and downgrades cleanly, `alembic check` reports no drift, the frontend builds, and the live sampler was observed writing rows on its interval.

## Kept strictly to the brief — the only points it leaves open

1. **Protocol values.** The brief says `default_config.protocol` is `simulation` or `mqtt`, and edge = `mqtt`. Your Phase 3 kits store `"sim"` / `"gpio-stub"`, so the migration renames those two values and `family_factory.py` uses the new ones. Phase 2 sensors have no protocol; `Device.protocol` treats that as `simulation`.
2. **Vendor stub flag** (the brief asks you to choose and document one): `default_config.adapter == "vendor_stub"`.
3. **MQTT "Read now"** is an adapter error → **400** ("adapter/domain errors → 400-level with detail").
4. **Tests never sleep:** `conftest.py` sets `settings.sampler_enabled = False` so the background loop doesn't run, and tests call `run_once(now)` with a fake clock.

Malformed JSON (missing field, wrong type) still gets FastAPI's default 422, the same as Phases 2–4. The 400 cases the brief names (adapter errors, interval below 5) return 400.

Backend code is volume-mounted into Docker with `--reload`, so new files are picked up automatically. Run commands from `~/greenhouse-project` unless stated. One command per block.

---

## Step 1 — Database model

Replace the whole file (adds the two `devices` columns and `ReadingRow`):

**`backend/src/infrastructure/persistence/models.py`**

```python
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from infrastructure.db import Base


class LocationRow(Base):
    __tablename__ = "locations"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[str] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    zones: Mapped[list["ZoneRow"]] = relationship(
        back_populates="location",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ZoneRow.name",
    )


class ZoneRow(Base):
    __tablename__ = "zones"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    location_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("locations.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    moisture_threshold_low: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    moisture_threshold_high: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    schedule: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'"))

    location: Mapped["LocationRow"] = relationship(back_populates="zones")

    __table_args__ = (
        Index("ix_zones_location_id", "location_id"),
    )


class DeviceRow(Base):
    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    device_type: Mapped[str] = mapped_column(String(64), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="sensor")
    display_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    default_config: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'"))
    created_at: Mapped[str] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
    device_family: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=text("'simulation'"),
    )
    zone_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("zones.id", ondelete="SET NULL"),
        nullable=True,
    )
    location_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("locations.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Phase 5: sampling settings (source of truth after this phase)
    sampling_interval_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("300"),
    )
    tracking_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )

    __table_args__ = (
        Index("ix_devices_role", "role"),
        Index("ix_devices_family", "device_family"),
        Index("ix_devices_zone_id", "zone_id"),
    )


class ReadingRow(Base):
    __tablename__ = "sensor_readings"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    device_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("devices.id"),
        nullable=False,
    )
    value: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(16), nullable=False)
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        # "latest reading per device" = WHERE device_id = ? ORDER BY recorded_at DESC LIMIT 1
        Index(
            "ix_sensor_readings_device_id_recorded_at",
            "device_id",
            text("recorded_at DESC"),
        ),
    )
```

Why `text("recorded_at DESC")`: the index matches the query "latest reading for this device" (`WHERE device_id = ? ORDER BY recorded_at DESC LIMIT 1`). `alembic/env.py` already imports `models`, so autogenerate will see `ReadingRow`.

---

## Step 2 — Generate the migration via Alembic

Make sure the stack is running:

```zsh
docker compose up -d
```

Autogenerate (runs inside the backend container; the file appears on your Mac because `alembic/` is mounted):

```zsh
docker compose exec backend alembic revision --autogenerate -m "sensor_readings"
```

Open the new file `backend/alembic/versions/<id>_sensor_readings.py`. **Review** that `upgrade()` has: `create_table('sensor_readings', …)` with the FK to `devices.id`, `create_index('ix_sensor_readings_device_id_recorded_at', … literal_column('recorded_at DESC'))`, and two `add_column('devices', …)` with server defaults `300` / `true`. Your revision id will differ from mine; that's fine.

Autogenerate cannot write data changes, so **paste this at the end of `upgrade()`**, right after the `# ### end Alembic commands ###` line:

```python
    # Backfill: copy sampling_interval_seconds from default_config when it is a number.
    op.execute("""
        UPDATE devices
        SET sampling_interval_seconds = (default_config->>'sampling_interval_seconds')::numeric::int
        WHERE jsonb_typeof(default_config->'sampling_interval_seconds') = 'number'
    """)
    # Protocol values the Phase 5 selector understands: "simulation" or "mqtt".
    op.execute("""
        UPDATE devices SET default_config = jsonb_set(default_config, '{protocol}', '"simulation"')
        WHERE default_config->>'protocol' = 'sim'
    """)
    op.execute("""
        UPDATE devices SET default_config = jsonb_set(default_config, '{protocol}', '"mqtt"')
        WHERE default_config->>'protocol' = 'gpio-stub'
    """)
```

And paste this at the **start** of `downgrade()` (it undoes the protocol rename) (right after its docstring):

```python
    op.execute("""
        UPDATE devices SET default_config = jsonb_set(default_config, '{protocol}', '"sim"')
        WHERE default_config->>'protocol' = 'simulation'
    """)
    op.execute("""
        UPDATE devices SET default_config = jsonb_set(default_config, '{protocol}', '"gpio-stub"')
        WHERE default_config->>'protocol' = 'mqtt'
    """)
```

Apply it:

```zsh
docker compose exec backend alembic upgrade head
```

```zsh
docker compose exec backend alembic current
```

Check the table and index:

```zsh
docker compose exec postgres psql -U greenhouse_user -d greenhouse_db -c "\d sensor_readings"
```

Check the backfill (light sensors should show 60, protocols should be `simulation` / `mqtt`):

```zsh
docker compose exec postgres psql -U greenhouse_user -d greenhouse_db -c "SELECT device_type, device_family, default_config->>'protocol' AS protocol, sampling_interval_seconds, tracking_enabled FROM devices;"
```

**Acceptance:** `alembic current` shows the new id `(head)`; `\d sensor_readings` shows the FK and `(device_id, recorded_at DESC)` index; every device has an interval and `tracking_enabled = t`. (The Phase 2 sensor shows an empty protocol — that counts as `simulation`.)

Commit:

```zsh
git add -A && git commit -m "Phase 5 Steps 1-2: sensor_readings table, sampling columns, backfill"
```

---

## Step 3 — Ports and adapters

Create the new folders and empty `__init__.py` files:

```zsh
cd backend/src
```

```zsh
mkdir -p domain/actuators application/readings infrastructure/adapters/sensors infrastructure/adapters/actuators interfaces/background
```

```zsh
touch domain/actuators/__init__.py application/readings/__init__.py infrastructure/adapters/__init__.py infrastructure/adapters/sensors/__init__.py infrastructure/adapters/actuators/__init__.py interfaces/background/__init__.py
```

```zsh
cd ../..
```

### 3a — Domain (no FastAPI / SQLAlchemy / Pydantic here)

Replace `Device` (adds the sampling fields and a `protocol` property), then create the new domain files:

**`backend/src/domain/devices/entity.py`**

```python
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class Device:
    id: UUID | None
    device_type: str
    role: str
    device_family: str
    display_name: str
    default_config: dict
    zone_id: UUID | None = None
    location_id: UUID | None = None
    # Phase 5: sampling settings (columns on `devices`)
    sampling_interval_seconds: int = 300
    tracking_enabled: bool = True

    @property
    def protocol(self) -> str:
        """Which transport talks to this device: "simulation" or "mqtt".

        Devices saved before Phase 5 without a protocol count as simulation.
        """
        return self.default_config.get("protocol", "simulation")
```

**`backend/src/domain/devices/sampling.py`**

```python
MIN_SAMPLING_INTERVAL_SECONDS = 5


class InvalidSamplingIntervalError(ValueError):
    pass


def validate_sampling_interval(seconds: int) -> None:
    if seconds < MIN_SAMPLING_INTERVAL_SECONDS:
        raise InvalidSamplingIntervalError(
            f"sampling_interval_seconds must be at least {MIN_SAMPLING_INTERVAL_SECONDS}"
        )
```

**`backend/src/domain/sensors/reading.py`**

```python
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class Reading:
    """Normalized sensor reading — the one shape every adapter must return."""
    device_id: UUID
    value: float
    unit: str            # e.g. "vwc", "lux"
    source: str          # "simulation", "mqtt" or "vendor"
    recorded_at: datetime  # timezone-aware
```

**`backend/src/domain/sensors/errors.py`**

```python
class SensorReadError(Exception):
    """An adapter could not produce a valid Reading (bad payload, unsupported device...)."""
```

**`backend/src/domain/sensors/ports.py`**

```python
from __future__ import annotations
from abc import ABC, abstractmethod
from domain.devices.entity import Device
from domain.sensors.reading import Reading


class SensorPort(ABC):
    """What the application needs from any sensor, whatever the hardware or vendor."""

    @abstractmethod
    def read(self, device: Device) -> Reading:
        ...
```

**`backend/src/domain/actuators/ports.py`**

```python
from __future__ import annotations
from abc import ABC, abstractmethod
from uuid import UUID


class ActuatorPort(ABC):
    """What the application needs from any actuator (pump, light...)."""

    @abstractmethod
    def apply(self, device_id: UUID, command: str, payload: dict) -> None:
        ...
```

In `backend/src/domain/sensors/entity.py` add two fields under `id` (so `/api/sensors` can return them):

```python
    id: UUID | None = None
    sampling_interval_seconds: int = 300
    tracking_enabled: bool = True
```

In `backend/src/domain/devices/family_factory.py` rename the protocol strings (8 places): every `"protocol": "sim"` → `"protocol": "simulation"` and every `"protocol": "gpio-stub"` → `"protocol": "mqtt"`. One command does it:

```zsh
sed -i '' 's/"protocol": "sim"/"protocol": "simulation"/g; s/"protocol": "gpio-stub"/"protocol": "mqtt"/g' backend/src/domain/devices/family_factory.py
```

(`sed -i ''` is the macOS form.) Check:

```zsh
grep -n protocol backend/src/domain/devices/family_factory.py
```

You should see only `simulation` and `mqtt`.

### 3b — Adapters (infrastructure)

**`backend/src/infrastructure/adapters/sensors/simulation.py`**

```python
from __future__ import annotations
import random
from collections.abc import Callable
from datetime import datetime, timezone

from domain.devices.entity import Device
from domain.sensors.errors import SensorReadError
from domain.sensors.ports import SensorPort
from domain.sensors.reading import Reading

# Documented value ranges for generated readings: device_type -> (low, high, unit)
SIMULATION_RANGES: dict[str, tuple[float, float, str]] = {
    "moisture_sensor": (0.2, 0.6, "vwc"),
    "light_sensor": (200.0, 2000.0, "lux"),
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SimulationSensorAdapter(SensorPort):
    """Generates a plausible value in code — no hardware needed."""

    def __init__(
        self,
        rng: random.Random | None = None,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._rng = rng or random.Random()
        self._clock = clock

    def read(self, device: Device) -> Reading:
        spec = SIMULATION_RANGES.get(device.device_type)
        if spec is None:
            raise SensorReadError(f"No simulation range for device type '{device.device_type}'")
        low, high, unit = spec
        value = round(self._rng.uniform(low, high), 4)
        return Reading(
            device_id=device.id,
            value=value,
            unit=unit,
            source="simulation",
            recorded_at=self._clock(),
        )
```

**`backend/src/infrastructure/adapters/sensors/vendor_stub.py`**

```python
from __future__ import annotations
import random
from datetime import datetime, timezone

from domain.devices.entity import Device
from domain.sensors.errors import SensorReadError
from domain.sensors.ports import SensorPort
from domain.sensors.reading import Reading


class FakeAcmeClient:
    """Pretend vendor SDK. Its payload shape is deliberately NOT our Reading shape:

        {"channel": "SOIL", "reading_x100": 4100, "uom": "PCT_VWC", "epoch_ms": 1759...}

    - values are integers scaled by 100
    - moisture comes as a percentage (41.00 %), not a 0–1 fraction
    - time is epoch milliseconds, not a datetime
    """

    _CHANNELS = {"moisture_sensor": ("SOIL", "PCT_VWC", 20.0, 60.0),
                 "light_sensor": ("LIGHT", "LUX", 200.0, 2000.0)}

    def fetch(self, device_type: str) -> dict:
        channel, uom, low, high = self._CHANNELS[device_type]
        return {
            "channel": channel,
            "reading_x100": int(random.uniform(low, high) * 100),
            "uom": uom,
            "epoch_ms": int(datetime.now(timezone.utc).timestamp() * 1000),
        }


class VendorStubSensorAdapter(SensorPort):
    """Adapter: translates the vendor's raw payload into our normalized Reading."""

    def __init__(self, client: FakeAcmeClient | None = None) -> None:
        self._client = client or FakeAcmeClient()

    def read(self, device: Device) -> Reading:
        if device.device_type not in FakeAcmeClient._CHANNELS:
            raise SensorReadError(f"Vendor stub does not support '{device.device_type}'")
        raw = self._client.fetch(device.device_type)
        return self.translate(device, raw)

    def translate(self, device: Device, raw: dict) -> Reading:
        try:
            scaled = raw["reading_x100"] / 100
            uom = raw["uom"]
            recorded_at = datetime.fromtimestamp(raw["epoch_ms"] / 1000, tz=timezone.utc)
        except (KeyError, TypeError) as e:
            raise SensorReadError(f"Malformed vendor payload: {e}") from e

        if uom == "PCT_VWC":
            value, unit = round(scaled / 100, 4), "vwc"     # 41.00 % -> 0.41
        elif uom == "LUX":
            value, unit = scaled, "lux"
        else:
            raise SensorReadError(f"Unknown vendor unit '{uom}'")

        return Reading(
            device_id=device.id,
            value=value,
            unit=unit,
            source="vendor",
            recorded_at=recorded_at,
        )
```

**`backend/src/infrastructure/adapters/sensors/mqtt.py`**

```python
from __future__ import annotations
from datetime import datetime, timezone

from domain.devices.entity import Device
from domain.sensors.errors import SensorReadError
from domain.sensors.reading import Reading


class MqttSensorAdapter:
    """Translates an inbound payload such as {"value": 0.41, "unit": "vwc"} into a Reading.

    No broker in this phase: Phase 12 delivers the payload (device HTTP or optional broker).
    """

    def translate(self, device: Device, payload: dict) -> Reading:
        value = payload.get("value")
        unit = payload.get("unit")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise SensorReadError("MQTT payload 'value' must be a number")
        if not isinstance(unit, str) or not unit:
            raise SensorReadError("MQTT payload 'unit' must be a non-empty string")
        return Reading(
            device_id=device.id,
            value=float(value),
            unit=unit,
            source="mqtt",
            recorded_at=datetime.now(timezone.utc),
        )
```

**`backend/src/infrastructure/adapters/sensors/selector.py`**

```python
"""Adapter selection rule (the only place that knows concrete sensor adapter classes).

1. default_config["adapter"] == "vendor_stub"  -> VendorStubSensorAdapter  (checked first)
2. default_config["protocol"] == "simulation"  -> SimulationSensorAdapter  (also the default)
3. default_config["protocol"] == "mqtt"        -> no on-demand read: MQTT devices push data;
                                                  their payloads go through MqttSensorAdapter.translate
"""
from __future__ import annotations
from domain.devices.entity import Device
from domain.sensors.errors import SensorReadError
from domain.sensors.ports import SensorPort
from infrastructure.adapters.sensors.simulation import SimulationSensorAdapter
from infrastructure.adapters.sensors.vendor_stub import VendorStubSensorAdapter

VENDOR_STUB_FLAG = "vendor_stub"

_simulation = SimulationSensorAdapter()
_vendor = VendorStubSensorAdapter()


def select_sensor_adapter(device: Device) -> SensorPort:
    if device.default_config.get("adapter") == VENDOR_STUB_FLAG:
        return _vendor
    if device.protocol == "simulation":
        return _simulation
    if device.protocol == "mqtt":
        raise SensorReadError(
            "MQTT devices push their readings; on-demand read is not supported"
        )
    raise SensorReadError(f"Unknown protocol '{device.protocol}'")
```

**`backend/src/infrastructure/adapters/actuators/simulation.py`**

```python
from __future__ import annotations
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from domain.actuators.ports import ActuatorPort

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AppliedCommand:
    device_id: UUID
    command: str
    payload: dict
    applied_at: datetime


class SimulationActuatorAdapter(ActuatorPort):
    """Records intent in memory and logs it. No GPIO, no physical output.
    Phase 9 decorators will wrap this class."""

    def __init__(self) -> None:
        self.applied: list[AppliedCommand] = []

    def apply(self, device_id: UUID, command: str, payload: dict) -> None:
        entry = AppliedCommand(device_id, command, dict(payload), datetime.now(timezone.utc))
        self.applied.append(entry)
        logger.info("SIM actuator %s <- %s %s", device_id, command, payload)
```

The vendor adapter does real **translation**: ×100 integers → float, percent → 0–1 fraction, epoch ms → aware datetime. That is the heart of the pattern.

**Acceptance:** only `selector.py` imports adapter classes; MQTT translation needs just a dict; the actuator adapter only records/logs.

---

## Step 4 — Persistence and application service

### 4a — Repositories

Replace `device_repository.py` (maps the two new columns and adds `get_device`, `list_tracked_sensors`, `update_sampling`):

**`backend/src/infrastructure/persistence/device_repository.py`**

```python
from __future__ import annotations
from uuid import UUID
from sqlalchemy.orm import Session
from domain.devices.entity import Device
from infrastructure.persistence.models import DeviceRow


def _row_to_device(row: DeviceRow) -> Device:
    return Device(
        id=UUID(row.id),
        device_type=row.device_type,
        role=row.role,
        device_family=row.device_family,
        display_name=row.display_name or "",
        default_config=row.default_config,
        zone_id=UUID(row.zone_id) if row.zone_id else None,
        location_id=UUID(row.location_id) if row.location_id else None,
        sampling_interval_seconds=row.sampling_interval_seconds,
        tracking_enabled=row.tracking_enabled,
    )


def _device_to_row(device: Device) -> DeviceRow:
    return DeviceRow(
        device_type=device.device_type,
        role=device.role,
        device_family=device.device_family,
        display_name=device.display_name,
        default_config=device.default_config,
    )


class DeviceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save_device(self, device: Device) -> Device:
        row = _device_to_row(device)
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return _row_to_device(row)

    def save_devices(self, devices: list[Device]) -> list[Device]:
        rows = [_device_to_row(d) for d in devices]
        for row in rows:
            self._session.add(row)
        self._session.commit()
        for row in rows:
            self._session.refresh(row)
        return [_row_to_device(row) for row in rows]

    def list_devices(
        self,
        *,
        device_family: str | None = None,
        role: str | None = None,
    ) -> list[Device]:
        query = self._session.query(DeviceRow)
        if device_family is not None:
            query = query.filter(DeviceRow.device_family == device_family)
        if role is not None:
            query = query.filter(DeviceRow.role == role)
        return [_row_to_device(row) for row in query.all()]

    # ---- Phase 5 ----

    def get_device(self, device_id: UUID) -> Device | None:
        row = self._session.get(DeviceRow, str(device_id))
        return _row_to_device(row) if row else None

    def list_tracked_sensors(self) -> list[Device]:
        """Sensors with tracking on (protocol filtering happens in the sampler)."""
        rows = (
            self._session.query(DeviceRow)
            .filter(DeviceRow.role == "sensor", DeviceRow.tracking_enabled.is_(True))
            .all()
        )
        return [_row_to_device(row) for row in rows]

    def update_sampling(
        self, device_id: UUID, interval_seconds: int, tracking_enabled: bool
    ) -> Device | None:
        row = self._session.get(DeviceRow, str(device_id))
        if row is None:
            return None
        row.sampling_interval_seconds = interval_seconds
        row.tracking_enabled = tracking_enabled
        self._session.commit()
        self._session.refresh(row)
        return _row_to_device(row)

    def save_sensor(self, sensor) -> object:
        from domain.sensors.entity import Sensor
        row = DeviceRow(
            device_type=sensor.device_type,
            role="sensor",
            device_family="simulation",
            display_name=sensor.display_name,
            default_config=sensor.default_config,
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return Sensor(
            id=UUID(row.id),
            device_type=row.device_type,
            display_name=row.display_name or "",
            default_config=row.default_config,
            sampling_interval_seconds=row.sampling_interval_seconds,
            tracking_enabled=row.tracking_enabled,
        )

    def list_sensors(self) -> list[object]:
        from domain.sensors.entity import Sensor
        rows = (
            self._session.query(DeviceRow)
            .filter(DeviceRow.role == "sensor")
            .all()
        )
        return [
            Sensor(
                id=UUID(row.id),
                device_type=row.device_type,
                display_name=row.display_name or "",
                default_config=row.default_config,
                sampling_interval_seconds=row.sampling_interval_seconds,
                tracking_enabled=row.tracking_enabled,
            )
            for row in rows
        ]
```

**`backend/src/infrastructure/persistence/reading_repository.py`**

```python
from __future__ import annotations
from uuid import UUID

from sqlalchemy.orm import Session

from domain.sensors.reading import Reading
from infrastructure.persistence.models import ReadingRow


def _row_to_reading(row: ReadingRow) -> Reading:
    return Reading(
        device_id=UUID(row.device_id),
        value=float(row.value),          # NUMERIC comes back as Decimal
        unit=row.unit,
        source=row.source,
        recorded_at=row.recorded_at,
    )


class ReadingRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def insert(self, reading: Reading) -> Reading:
        row = ReadingRow(
            device_id=str(reading.device_id),
            value=reading.value,
            unit=reading.unit,
            source=reading.source,
            recorded_at=reading.recorded_at,
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return _row_to_reading(row)

    def list_for_device(self, device_id: UUID, limit: int = 20) -> list[Reading]:
        rows = (
            self._session.query(ReadingRow)
            .filter(ReadingRow.device_id == str(device_id))
            .order_by(ReadingRow.recorded_at.desc())
            .limit(limit)
            .all()
        )
        return [_row_to_reading(r) for r in rows]

    def latest_for_device(self, device_id: UUID) -> Reading | None:
        rows = self.list_for_device(device_id, limit=1)
        return rows[0] if rows else None
```

### 4b — Application

**`backend/src/application/readings/dto.py`**

```python
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class ReadingDto(BaseModel):
    device_id: UUID
    value: float
    unit: str
    source: str
    recorded_at: datetime


class SamplingUpdateDto(BaseModel):
    sampling_interval_seconds: int
    tracking_enabled: bool


class SamplingDto(BaseModel):
    device_id: UUID
    sampling_interval_seconds: int
    tracking_enabled: bool
```

**`backend/src/application/readings/errors.py`**

```python
class DeviceNotFoundError(Exception):
    pass
```

**`backend/src/application/readings/service.py`**

```python
from __future__ import annotations
from collections.abc import Callable
from uuid import UUID

from application.readings.dto import ReadingDto
from application.readings.errors import DeviceNotFoundError
from domain.devices.entity import Device
from domain.sensors.ports import SensorPort
from domain.sensors.reading import Reading
from infrastructure.persistence.device_repository import DeviceRepository
from infrastructure.persistence.reading_repository import ReadingRepository

# Given a device, return the port that can read it. The selector lives in
# infrastructure and is injected, so this service never imports adapter classes.
AdapterSelector = Callable[[Device], SensorPort]


def reading_to_dto(reading: Reading) -> ReadingDto:
    return ReadingDto(
        device_id=reading.device_id,
        value=reading.value,
        unit=reading.unit,
        source=reading.source,
        recorded_at=reading.recorded_at,
    )


class ReadingIngest:
    """The only writer of sensor_readings."""

    def __init__(
        self,
        devices: DeviceRepository,
        readings: ReadingRepository,
        select_adapter: AdapterSelector,
    ) -> None:
        self._devices = devices
        self._readings = readings
        self._select_adapter = select_adapter

    def _load_device(self, device_id: UUID) -> Device:
        device = self._devices.get_device(device_id)
        if device is None:
            raise DeviceNotFoundError(str(device_id))
        return device

    def take_reading(self, device_id: UUID) -> ReadingDto:
        """One-shot read: load device -> select adapter -> read -> persist -> DTO."""
        device = self._load_device(device_id)
        reading = self._select_adapter(device).read(device)   # may raise SensorReadError
        return self.record(device_id, reading)

    def record(self, device_id: UUID, reading: Reading) -> ReadingDto:
        """Persist an already translated reading (e.g. MqttSensorAdapter output)."""
        self._load_device(device_id)
        return reading_to_dto(self._readings.insert(reading))

    def list_readings(self, device_id: UUID, limit: int = 20) -> list[ReadingDto]:
        self._load_device(device_id)
        return [reading_to_dto(r) for r in self._readings.list_for_device(device_id, limit)]
```

**`backend/src/application/readings/sampler.py`**

```python
from __future__ import annotations
import logging
from dataclasses import replace
from datetime import datetime, timedelta

from application.readings.service import AdapterSelector, ReadingIngest
from domain.sensors.errors import SensorReadError
from infrastructure.persistence.device_repository import DeviceRepository
from infrastructure.persistence.reading_repository import ReadingRepository

logger = logging.getLogger(__name__)


class SimulationSampler:
    """Records a reading for each tracked simulation sensor whose interval has elapsed.

    It has no clock of its own: the caller passes `now`. The app lifespan passes the
    real time every few seconds; tests pass a fake time and never sleep.
    """

    def __init__(
        self,
        devices: DeviceRepository,
        readings: ReadingRepository,
        ingest: ReadingIngest,
        select_adapter: AdapterSelector,
    ) -> None:
        self._devices = devices
        self._readings = readings
        self._ingest = ingest
        self._select_adapter = select_adapter

    def run_once(self, now: datetime) -> None:
        for device in self._devices.list_tracked_sensors():
            if device.protocol != "simulation":
                continue                                   # MQTT devices push their own data
            last = self._readings.latest_for_device(device.id)
            interval = timedelta(seconds=device.sampling_interval_seconds)
            if last is not None and now - last.recorded_at < interval:
                continue                                   # not due yet
            try:
                reading = self._select_adapter(device).read(device)
            except SensorReadError as e:
                logger.warning("Sampler skipped %s: %s", device.id, e)
                continue
            # Stamp the reading with the tick time so interval maths uses one clock.
            self._ingest.record(device.id, replace(reading, recorded_at=now))
```

**`backend/src/application/devices/sampling_service.py`**

```python
from __future__ import annotations
from uuid import UUID

from application.readings.dto import SamplingDto, SamplingUpdateDto
from application.readings.errors import DeviceNotFoundError
from domain.devices.sampling import validate_sampling_interval
from infrastructure.persistence.device_repository import DeviceRepository


class DeviceSamplingService:
    def __init__(self, repo: DeviceRepository) -> None:
        self._repo = repo

    def update(self, device_id: UUID, body: SamplingUpdateDto) -> SamplingDto:
        validate_sampling_interval(body.sampling_interval_seconds)  # raises InvalidSamplingIntervalError
        device = self._repo.update_sampling(
            device_id, body.sampling_interval_seconds, body.tracking_enabled
        )
        if device is None:
            raise DeviceNotFoundError(str(device_id))
        return SamplingDto(
            device_id=device.id,
            sampling_interval_seconds=device.sampling_interval_seconds,
            tracking_enabled=device.tracking_enabled,
        )
```

Key design points:

- `ReadingIngest` receives the selector as a function (`AdapterSelector`), so it depends on `SensorPort` only and never imports an adapter class.
- `take_reading` → `record` → `insert`: `record` is the **only** writer of `sensor_readings`.
- `SimulationSampler.run_once(now)` has no clock of its own. It stamps each reading with `now`, so the interval maths uses one clock, and tests can pass any fake time.

---

## Step 5 — API endpoints + background sampler

Add one setting in `backend/src/infrastructure/settings.py`, under `cors_origins`:

```python
    # Phase 5: tests turn the background sampler off and call run_once(now) directly
    sampler_enabled: bool = True
```

Replace / create these files:

**`backend/src/interfaces/api/sensors.py`**

```python
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
```

**`backend/src/interfaces/api/devices.py`**

```python
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
```

**`backend/src/interfaces/background/sampler_loop.py`**

```python
"""Runs SimulationSampler.run_once on a timer while the app is up.

Wiring lives here (outer layer), so the sampler itself stays clock-free and testable.
"""
from __future__ import annotations
import asyncio
import logging
from datetime import datetime, timezone

from application.readings.sampler import SimulationSampler
from application.readings.service import ReadingIngest
from infrastructure.adapters.sensors.selector import select_sensor_adapter
from infrastructure.db import SessionLocal
from infrastructure.persistence.device_repository import DeviceRepository
from infrastructure.persistence.reading_repository import ReadingRepository

logger = logging.getLogger(__name__)


def _tick() -> None:
    session = SessionLocal()                 # fresh session per tick
    try:
        devices = DeviceRepository(session)
        readings = ReadingRepository(session)
        ingest = ReadingIngest(devices, readings, select_sensor_adapter)
        sampler = SimulationSampler(devices, readings, ingest, select_sensor_adapter)
        sampler.run_once(datetime.now(timezone.utc))
    finally:
        session.close()


TICK_SECONDS = 5   # same as the minimum sampling interval


async def run_sampler_forever() -> None:
    while True:
        try:
            await asyncio.to_thread(_tick)   # DB work off the event loop
        except Exception:
            logger.exception("Simulation sampler tick failed")
        await asyncio.sleep(TICK_SECONDS)
```

**`backend/src/main.py`**

```python
import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from scalar_fastapi import get_scalar_api_reference
from interfaces.api.devices import router as devices_router
from interfaces.api.locations import router as locations_router

from infrastructure.settings import settings
from interfaces.api.health import router as health_router
from interfaces.api.sensors import router as sensors_router
from interfaces.background.sampler_loop import run_sampler_forever


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = None
    if settings.sampler_enabled:
        task = asyncio.create_task(run_sampler_forever())
    yield
    if task is not None:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


app = FastAPI(
    lifespan=lifespan,
    title="Smart Greenhouse API",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health_router)
app.include_router(sensors_router)
app.include_router(locations_router)
app.include_router(devices_router)

# Discovery root
@app.get("/", include_in_schema=False)
def root():
    return JSONResponse({
        "message": "Smart Greenhouse API",
        "api_reference": "/scalar",
        "openapi": "/openapi.json",
    })


# Scalar UI
@app.get("/scalar", include_in_schema=False)
def scalar_ui():
    return get_scalar_api_reference(
        openapi_url="/openapi.json",
        title="Smart Greenhouse API",
    )
```

Error mapping: missing device → **404**; adapter errors (e.g. MQTT read) and interval below 5 → **400**. The interval rule is checked in the domain (`validate_sampling_interval`), not with Pydantic `ge=5`, because Pydantic would give 422 and the brief asks for 400.

Watch the backend reload (Ctrl+C to stop following):

```zsh
docker compose logs -f backend
```

Open http://localhost:8000/scalar — under **sensors** you should see `POST /api/sensors/{sensor_id}/read` and `GET …/readings`, under **devices** `PATCH /api/devices/{device_id}/sampling`, and the `ReadingDto` schema.

Quick manual check — copy a simulation sensor id from:

```zsh
curl -s localhost:8000/api/sensors
```

Then (replace `<ID>`):

```zsh
curl -s -X POST localhost:8000/api/sensors/<ID>/read
```

```zsh
curl -s "localhost:8000/api/sensors/<ID>/readings?limit=5"
```

```zsh
curl -s -X PATCH localhost:8000/api/devices/<ID>/sampling -H "Content-Type: application/json" -d '{"sampling_interval_seconds": 4, "tracking_enabled": true}'
```

The last one must return `400` with `sampling_interval_seconds must be at least 5`.

Commit:

```zsh
git add -A && git commit -m "Phase 5 Steps 3-5: ports, adapters, ReadingIngest, sampler, API"
```

---

## Step 6 — Frontend

In `frontend/src/services/api.ts`, add two fields to `SensorDto`:

```ts
export interface SensorDto {
  id: string;
  device_type: string;
  display_name: string;
  default_config: Record<string, unknown>;
  sampling_interval_seconds: number;
  tracking_enabled: boolean;
}
```

Then append this block to the **end** of `api.ts` (it reuses your existing `readError` and `JSON_HEADERS`):

```ts
// ---- Phase 5: readings & sampling ----

export interface ReadingDto {
  device_id: string;
  value: number;
  unit: string;
  source: string; // "simulation" | "mqtt" | "vendor"
  recorded_at: string;
}

export interface SamplingDto {
  device_id: string;
  sampling_interval_seconds: number;
  tracking_enabled: boolean;
}

export async function readSensorNow(sensorId: string): Promise<ReadingDto> {
  const res = await fetch(`${API_BASE}/api/sensors/${sensorId}/read`, { method: "POST" });
  if (!res.ok) throw await readError(res, "Could not read sensor.");
  return res.json();
}

export async function fetchLatestReading(sensorId: string): Promise<ReadingDto | null> {
  const res = await fetch(`${API_BASE}/api/sensors/${sensorId}/readings?limit=1`);
  if (!res.ok) throw await readError(res, "Could not load readings.");
  const rows: ReadingDto[] = await res.json();
  return rows[0] ?? null;
}

export async function updateSampling(
  deviceId: string,
  samplingIntervalSeconds: number,
  trackingEnabled: boolean
): Promise<SamplingDto> {
  const res = await fetch(`${API_BASE}/api/devices/${deviceId}/sampling`, {
    method: "PATCH",
    headers: JSON_HEADERS,
    body: JSON.stringify({
      sampling_interval_seconds: samplingIntervalSeconds,
      tracking_enabled: trackingEnabled,
    }),
  });
  if (!res.ok) throw await readError(res, "Could not update sampling.");
  return res.json();
}
```

New file:

**`frontend/src/features/sensors/SensorCard.tsx`**

```tsx
import { useEffect, useState } from "react";
import {
  fetchLatestReading,
  readSensorNow,
  updateSampling,
  type ReadingDto,
  type SensorDto,
} from "../../services/api";

// TEMPORARY: poll the latest stored reading every few seconds so sampler rows show up.
// Phase 12 replaces this poll with a WebSocket.
const POLL_MS = 3000;

export default function SensorCard({ sensor }: { sensor: SensorDto }) {
  const [reading, setReading] = useState<ReadingDto | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [interval, setIntervalSecs] = useState(String(sensor.sampling_interval_seconds));
  const [tracking, setTracking] = useState(sensor.tracking_enabled);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function poll() {
      try {
        const latest = await fetchLatestReading(sensor.id);
        if (!cancelled) setReading(latest);
      } catch {
        if (!cancelled) setError("Could not load latest reading.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    poll();
    const id = window.setInterval(poll, POLL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [sensor.id]);

  async function handleReadNow() {
    try {
      setBusy(true);
      setError(null);
      setReading(await readSensorNow(sensor.id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not read sensor.");
    } finally {
      setBusy(false);
    }
  }

  async function saveSampling(nextInterval: string, nextTracking: boolean) {
    try {
      setBusy(true);
      setError(null);
      const res = await updateSampling(sensor.id, Number(nextInterval), nextTracking);
      setIntervalSecs(String(res.sampling_interval_seconds));
      setTracking(res.tracking_enabled);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not update sampling.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="border rounded p-3 text-sm space-y-2">
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="font-medium">{sensor.display_name}</div>
          <div className="text-gray-500">{sensor.device_type}</div>
        </div>
        {reading && (
          <span className="px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-700">
            {reading.source}
          </span>
        )}
      </div>

      {loading ? (
        <p className="text-gray-400">Loading…</p>
      ) : reading ? (
        <p>
          <span className="text-xl font-semibold">{reading.value}</span>{" "}
          <span className="text-gray-500">{reading.unit}</span>{" "}
          <span className="text-gray-400 text-xs">
            {new Date(reading.recorded_at).toLocaleTimeString()}
          </span>
        </p>
      ) : (
        <p className="text-gray-400">No readings yet</p>
      )}

      <button
        onClick={handleReadNow}
        disabled={busy}
        className="px-3 py-1.5 bg-slate-800 text-white rounded hover:bg-slate-700 disabled:opacity-50 text-xs"
      >
        {busy ? "Working…" : "Read now"}
      </button>

      <div className="flex items-center gap-3 text-xs">
        <label className="flex items-center gap-1">
          Every
          <input
            type="number"
            min={5}
            value={interval}
            onChange={(e) => setIntervalSecs(e.target.value)}
            onBlur={() => saveSampling(interval, tracking)}
            disabled={busy}
            className="w-16 border rounded px-1 py-0.5"
          />
          s
        </label>
        <label className="flex items-center gap-1">
          <input
            type="checkbox"
            checked={tracking}
            onChange={(e) => saveSampling(interval, e.target.checked)}
            disabled={busy}
          />
          Tracking
        </label>
      </div>

      <p className="text-gray-400 text-xs">Value refreshes every few seconds (temporary polling).</p>
      {error && <p className="text-red-500 text-xs">{error}</p>}
    </div>
  );
}
```

In `frontend/src/features/sensors/SensorList.tsx`:

1. Add the import under the existing one:

```tsx
import SensorCard from "./SensorCard";
```

2. Replace the whole `sensors.map(...)` block (the `<div key={s.id} …>` with the JSON dump) with:

```tsx
      {sensors.map((s) => (
        <SensorCard key={s.id} sensor={s} />
      ))}
```

Open http://localhost:5173/dashboard. Each sensor card shows "Loading…", then the latest stored value with a source badge, "Read now", an interval box (saves when you click out of it) and a Tracking checkbox. Edge (MQTT) cards say "No readings yet"; "Read now" there shows the 400 message.

**Acceptance checks (by hand):**

- Refresh the page → the value is still there (it comes from the DB).
- Set a simulation sensor to `5` s → its timestamp changes every ~5 s without clicking.
- Untick Tracking → the timestamp stops changing. Tick it again → it resumes.
- Type `3` and click out → red error from the API, nothing saved.

Optional — see the vendor badge: flag one sensor as vendor stub (replace `<ID>`), then click Read now:

```zsh
docker compose exec postgres psql -U greenhouse_user -d greenhouse_db -c "UPDATE devices SET default_config = default_config || '{\"adapter\": \"vendor_stub\"}' WHERE id = '<ID>';"
```

The badge turns amber `vendor` (the sampler also uses the vendor adapter for that sensor).

---

## Step 7 — Tests

Replace `conftest.py` (sampler off in tests, `sensor_readings` truncated, new `db_session` fixture), then add three test files:

**`backend/tests/conftest.py`**

```python
import os
import subprocess
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from infrastructure.settings import settings

BACKEND_DIR = Path(__file__).resolve().parents[1]
TEST_DB_NAME = "greenhouse_test"

_base_url = make_url(settings.database_url)
assert _base_url.database != TEST_DB_NAME, "Refusing to run: base URL already points at the test DB"
ADMIN_URL = _base_url.render_as_string(hide_password=False)
TEST_URL = _base_url.set(database=TEST_DB_NAME).render_as_string(hide_password=False)

# Point the app at the test database before infrastructure.db creates its engine.
settings.database_url = TEST_URL
os.environ["DATABASE_URL"] = TEST_URL
# Phase 5: tests drive the sampler by hand with a fake clock — no background loop.
settings.sampler_enabled = False


@pytest.fixture(scope="session")
def migrated_db():
    """Recreate an empty test database and migrate it to head."""
    admin = create_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}" WITH (FORCE)'))
        conn.execute(text(f'CREATE DATABASE "{TEST_DB_NAME}"'))
    admin.dispose()

    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        env={**os.environ, "DATABASE_URL": TEST_URL},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    yield TEST_URL


@pytest.fixture
def client(migrated_db):
    from fastapi.testclient import TestClient
    from infrastructure.db import engine
    from main import app

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE sensor_readings, locations, zones, devices CASCADE"))
    with TestClient(app) as c:
        yield c

@pytest.fixture
def db_session(migrated_db):
    """A clean DB session for service-level tests (no HTTP)."""
    from infrastructure.db import SessionLocal, engine

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE sensor_readings, locations, zones, devices CASCADE"))
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
```

**`backend/tests/test_sensor_adapters.py`**

```python
"""Adapter unit tests: no database, no HTTP, no broker."""
import socket
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from domain.devices.entity import Device
from infrastructure.adapters.actuators.simulation import SimulationActuatorAdapter
from infrastructure.adapters.sensors.mqtt import MqttSensorAdapter
from infrastructure.adapters.sensors.simulation import SIMULATION_RANGES, SimulationSensorAdapter
from infrastructure.adapters.sensors.vendor_stub import VendorStubSensorAdapter


def make_device(device_type="moisture_sensor") -> Device:
    return Device(
        id=uuid4(),
        device_type=device_type,
        role="sensor",
        device_family="simulation",
        display_name="Test",
        default_config={"protocol": "simulation"},
    )


def test_vendor_adapter_normalizes_raw_payload():
    device = make_device("moisture_sensor")
    raw = {"channel": "SOIL", "reading_x100": 4100, "uom": "PCT_VWC", "epoch_ms": 1_790_000_000_000}

    reading = VendorStubSensorAdapter().translate(device, raw)

    assert reading.device_id == device.id
    assert reading.value == pytest.approx(0.41)          # 41.00 % -> 0.41 vwc
    assert reading.unit == "vwc"
    assert reading.source == "vendor"
    assert reading.recorded_at == datetime.fromtimestamp(1_790_000_000, tz=timezone.utc)


@pytest.mark.parametrize("device_type", ["moisture_sensor", "light_sensor"])
def test_simulation_adapter_value_in_range(device_type):
    low, high, unit = SIMULATION_RANGES[device_type]
    adapter = SimulationSensorAdapter()
    for _ in range(200):
        reading = adapter.read(make_device(device_type))
        assert low <= reading.value <= high
        assert reading.unit == unit
        assert reading.source == "simulation"


def test_simulation_and_vendor_give_different_source():
    device = make_device("light_sensor")
    assert SimulationSensorAdapter().read(device).source == "simulation"
    assert VendorStubSensorAdapter().read(device).source == "vendor"


def test_mqtt_adapter_translates_payload(monkeypatch):
    def no_sockets(*args, **kwargs):
        raise AssertionError("MQTT translation must not open a socket")
    monkeypatch.setattr(socket, "socket", no_sockets)

    device = make_device("moisture_sensor")
    reading = MqttSensorAdapter().translate(device, {"value": 0.41, "unit": "vwc"})

    assert reading.device_id == device.id
    assert reading.value == 0.41
    assert reading.unit == "vwc"
    assert reading.source == "mqtt"


def test_simulation_actuator_apply_records_command():
    actuator = SimulationActuatorAdapter()
    device_id = uuid4()
    actuator.apply(device_id, "start", {"duration_seconds": 30})

    assert len(actuator.applied) == 1
    assert actuator.applied[0].command == "start"
```

**`backend/tests/test_simulation_sampler.py`**

```python
"""Sampler tests with a fake clock: no HTTP, no broker, no sleeping."""
from datetime import datetime, timedelta, timezone

from application.readings.sampler import SimulationSampler
from application.readings.service import ReadingIngest
from domain.devices.entity import Device
from infrastructure.adapters.sensors.mqtt import MqttSensorAdapter
from infrastructure.adapters.sensors.selector import select_sensor_adapter
from infrastructure.persistence.device_repository import DeviceRepository
from infrastructure.persistence.reading_repository import ReadingRepository

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


def sensor(protocol: str, name: str) -> Device:
    return Device(
        id=None,
        device_type="moisture_sensor",
        role="sensor",
        device_family="simulation" if protocol == "simulation" else "edge",
        display_name=name,
        default_config={"protocol": protocol},
    )


def build(db_session):
    devices = DeviceRepository(db_session)
    readings = ReadingRepository(db_session)
    ingest = ReadingIngest(devices, readings, select_sensor_adapter)
    sampler = SimulationSampler(devices, readings, ingest, select_sensor_adapter)
    return devices, readings, ingest, sampler


def count(readings, device):
    return len(readings.list_for_device(device.id, limit=100))


def test_sampler_respects_interval_and_tracking(db_session):
    devices, readings, _, sampler = build(db_session)
    sim, disabled, mqtt = devices.save_devices([
        sensor("simulation", "Sim"),
        sensor("simulation", "Sim (tracking off)"),
        sensor("mqtt", "Edge"),
    ])
    devices.update_sampling(sim.id, 60, tracking_enabled=True)
    devices.update_sampling(disabled.id, 60, tracking_enabled=False)

    sampler.run_once(T0)                                    # no previous row -> due
    assert count(readings, sim) == 1

    sampler.run_once(T0 + timedelta(seconds=30))            # inside the 60 s interval
    assert count(readings, sim) == 1

    sampler.run_once(T0 + timedelta(seconds=60))            # interval elapsed
    assert count(readings, sim) == 2

    assert count(readings, disabled) == 0                   # tracking off
    assert count(readings, mqtt) == 0                       # MQTT skipped


def test_record_persists_translated_mqtt_reading(db_session):
    devices, readings, ingest, _ = build(db_session)
    (mqtt,) = devices.save_devices([sensor("mqtt", "Edge")])
    reading = MqttSensorAdapter().translate(mqtt, {"value": 0.33, "unit": "vwc"})

    dto = ingest.record(mqtt.id, reading)

    assert dto.source == "mqtt"
    assert count(readings, mqtt) == 1
```

**`backend/tests/test_readings_api.py`**

```python
"""Integration tests: HTTP -> ReadingIngest -> sensor_readings."""
from uuid import uuid4

from sqlalchemy import create_engine, text


def simulation_sensor_id(client):
    r = client.post("/api/devices/provision", params={"family": "simulation"})
    assert r.status_code == 201, r.text
    return next(d["id"] for d in r.json() if d["role"] == "sensor")


def row_count(migrated_db, device_id):
    engine = create_engine(migrated_db)
    with engine.connect() as conn:
        n = conn.execute(
            text("SELECT count(*) FROM sensor_readings WHERE device_id = :id"), {"id": device_id}
        ).scalar_one()
    engine.dispose()
    return n


def test_read_inserts_sensor_reading(client, migrated_db):
    sensor_id = simulation_sensor_id(client)

    r = client.post(f"/api/sensors/{sensor_id}/read")
    assert r.status_code == 201, r.text
    assert set(r.json()) == {"device_id", "value", "unit", "source", "recorded_at"}
    assert row_count(migrated_db, sensor_id) == 1

    client.post(f"/api/sensors/{sensor_id}/read")
    assert row_count(migrated_db, sensor_id) == 2


def test_read_missing_device_404(client):
    assert client.post(f"/api/sensors/{uuid4()}/read").status_code == 404


def test_patch_sampling_round_trip(client):
    sensor_id = simulation_sensor_id(client)
    r = client.patch(
        f"/api/devices/{sensor_id}/sampling",
        json={"sampling_interval_seconds": 30, "tracking_enabled": False},
    )
    assert r.status_code == 200, r.text

    stored = next(s for s in client.get("/api/sensors").json() if s["id"] == sensor_id)
    assert stored["sampling_interval_seconds"] == 30
    assert stored["tracking_enabled"] is False


def test_patch_sampling_too_small_400(client):
    sensor_id = simulation_sensor_id(client)
    r = client.patch(
        f"/api/devices/{sensor_id}/sampling",
        json={"sampling_interval_seconds": 4, "tracking_enabled": True},
    )
    assert r.status_code == 400
```

Run everything:

```zsh
docker compose exec backend pytest tests -q
```

Expected: **45 passed**. Each new test maps to a line in the brief:

| Test | Requirement |
|------|-------------|
| `test_vendor_adapter_normalizes_raw_payload` | vendor shape → normalized fields |
| `test_simulation_adapter_value_in_range` | simulation stays in range, `source="simulation"` |
| `test_simulation_and_vendor_give_different_source` | "can yield different `source` values" |
| `test_mqtt_adapter_translates_payload` | dict → `Reading(source="mqtt")`, no socket opened |
| `test_simulation_actuator_apply_records_command` | `ActuatorPort` "can be called from a test" |
| `test_sampler_respects_interval_and_tracking` | insert, skip inside interval, insert after; disabled and MQTT get no rows |
| `test_record_persists_translated_mqtt_reading` | "this phase only needs the method and a test" |
| `test_read_inserts_sensor_reading` | read appends a row; repeated reads increase count |
| `test_read_missing_device_404` | missing device → 404 |
| `test_patch_sampling_round_trip` / `_too_small_400` | PATCH persists; interval < 5 → 400 |

---

## Step 8 — Documentation

**`docs/patterns/adapter.md`**

````markdown
# Adapter Pattern — Sensor Readings (Phase 5)

## Problem: incompatible interfaces

Every source of sensor data speaks its own language:

| Source | What it gives us |
|--------|------------------|
| Simulation (in code) | A random float we generate ourselves |
| Vendor SDK (stub "Acme") | `{"channel": "SOIL", "reading_x100": 4100, "uom": "PCT_VWC", "epoch_ms": 1759…}` — integers ×100, moisture as a **percent**, time in **epoch ms** |
| MQTT / ESP32 (Phase 12) | `{"value": 0.41, "unit": "vwc"}` pushed by the device |

If the application read these shapes directly, every service and router would fill up
with `if vendor == …` branches, and adding hardware would mean editing business code.

## Solution: one port, many adapters

The application only knows one interface (the **port**) and one data shape (`Reading`).
Each **adapter** converts one foreign interface into that port.

```text
                ┌──────────────── domain ────────────────┐
ReadingIngest → │ SensorPort.read(device) -> Reading      │
                └─────────────────────────────────────────┘
                     ▲                     ▲
   SimulationSensorAdapter     VendorStubSensorAdapter      MqttSensorAdapter.translate(payload)
   (generates value)           (translates Acme payload)    (translates pushed dict; no broker)
```

`Reading(device_id, value, unit, source, recorded_at)` is the unified shape. `source`
records which adapter produced it: `simulation`, `vendor` or `mqtt`.

The same idea is used for actuators: `ActuatorPort.apply(device_id, command, payload)`
with `SimulationActuatorAdapter`, which only records the command in memory and logs it
(no GPIO). Phase 9 decorators will wrap this port.

## Where in code

| Role | File |
|------|------|
| Target (port) | `backend/src/domain/sensors/ports.py` — `SensorPort` |
| Unified type | `backend/src/domain/sensors/reading.py` — `Reading` |
| Adapters | `backend/src/infrastructure/adapters/sensors/simulation.py`, `vendor_stub.py`, `mqtt.py` |
| Adaptee (fake vendor SDK) | `FakeAcmeClient` in `vendor_stub.py` |
| Selector (only place that names adapter classes) | `backend/src/infrastructure/adapters/sensors/selector.py` |
| Client | `backend/src/application/readings/service.py` — `ReadingIngest` (receives the selector, depends only on `SensorPort`) |
| Actuator port / adapter | `backend/src/domain/actuators/ports.py`, `backend/src/infrastructure/adapters/actuators/simulation.py` |

### Selection rule

1. `default_config.adapter == "vendor_stub"` → `VendorStubSensorAdapter` (checked first, so it never collides with `protocol`)
2. `default_config.protocol == "simulation"` (or no protocol) → `SimulationSensorAdapter`
3. `default_config.protocol == "mqtt"` → no on-demand read (400). MQTT devices push data; the payload goes through `MqttSensorAdapter.translate` and then `ReadingIngest.record`.

The Phase 5 migration renamed the Phase 3 protocol values: `sim` → `simulation`, `gpio-stub` → `mqtt`.

## One write path

`ReadingIngest.record` is the only code that inserts into `sensor_readings`.
`POST /api/sensors/{id}/read`, the `SimulationSampler` (every few seconds, only
`protocol=simulation` sensors with `tracking_enabled`, and only when
`sampling_interval_seconds` has passed since the last row) and, from Phase 12, MQTT/HTTP
ingest all go through it.

## Why Adapter (and not the earlier patterns)

Factory Method, Abstract Factory and Builder are about **creating** objects. Adapter is
structural: the objects already exist (a vendor SDK, a device payload) and have the wrong
interface. The adapter **translates**; it does not decide irrigation policy or state —
that stays in the application/domain (Phase 6 Strategy).

## Extension: adding a third vendor

1. Write `infrastructure/adapters/sensors/<vendor>.py` with a class implementing `SensorPort`
   that calls the vendor SDK and maps its payload to `Reading`.
2. Add one rule to `selector.py` (e.g. `default_config.adapter == "<vendor>"`).
3. Add a unit test that feeds a raw vendor payload and checks the normalized fields.

No change is needed in `ReadingIngest`, the sampler, the API, the database or the frontend.
````

Optionally add a Phase 5 entry to `docs/phases/README.md` (and remove "(current)" from Phase 4).

Final commit and push:

```zsh
git add -A && git commit -m "Phase 5 Steps 6-8: sensor cards, tests, adapter pattern doc"
```

```zsh
git push
```

---

## Definition of done

- [ ] `sensor_readings` with FK + `(device_id, recorded_at DESC)` index
- [ ] `sampling_interval_seconds` + `tracking_enabled` on `devices`, backfilled
- [ ] Simulation + vendor adapters behind `SensorPort`; MQTT `translate` from a dict
- [ ] `ActuatorPort` + `SimulationActuatorAdapter`
- [ ] POST read persists a row and returns `ReadingDto`
- [ ] Sampler records only tracked simulation sensors whose interval elapsed
- [ ] Cards: Read now, value + source from DB, interval + tracking, temporary poll (commented)
- [ ] 45 tests pass
- [ ] `docs/patterns/adapter.md`
