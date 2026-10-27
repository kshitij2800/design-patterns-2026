from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from sqlalchemy.orm import Session

from application.automation.service import AutomationService
from application.locations.dto import LocationSummaryDto
from application.overview.dto import (
    DeviceCountsDto,
    LocationOverviewDto,
    OverviewDeviceDto,
    OverviewReadingDto,
    OverviewRecommendationDto,
    OverviewZoneDto,
)
from application.overview.errors import LocationNotFoundError
from domain.devices.entity import Device
from domain.sensors.reading import Reading
from infrastructure.persistence.automation_repository import AutomationRepository
from infrastructure.persistence.device_repository import DeviceRepository
from infrastructure.persistence.location_repository import LocationRepository
from infrastructure.persistence.reading_repository import ReadingRepository


class LocationOverviewFacade:
    """Facade: one entry point that hides locations, assigned devices, readings
    and the saved strategy behind get_overview(location_id)."""

    def __init__(
        self,
        locations: LocationRepository,
        devices: DeviceRepository,
        readings: ReadingRepository,
        automation_repo: AutomationRepository,
        automation: AutomationService,
    ) -> None:
        self._locations = locations
        self._devices = devices
        self._readings = readings
        self._automation_repo = automation_repo
        self._automation = automation

    @classmethod
    def from_session(cls, session: Session) -> LocationOverviewFacade:
        """Wire every subsystem from one DB session, so the router only knows the facade."""
        automation_repo = AutomationRepository(session)
        return cls(
            LocationRepository(session),
            DeviceRepository(session),
            ReadingRepository(session),
            automation_repo,
            AutomationService(automation_repo),
        )

    def get_overview(self, location_id: UUID) -> LocationOverviewDto:
        # 1. Location + every zone (also zones with no devices)
        config = self._locations.get_config(location_id)
        if config is None:
            raise LocationNotFoundError(str(location_id))
        location_row, zone_rows = config
        zone_ids = {UUID(z.id) for z in zone_rows}

        assigned = [
            d for d in self._devices.list_assigned_in_location(location_id)
            if d.zone_id in zone_ids
        ]

        latest = self._readings.latest_for_devices([d.id for d in assigned])

        strategy_key = self._automation_repo.get_strategy_key(location_id)
        last_recommendation = None
        if strategy_key is not None:
            rec = self._automation.evaluate(location_id)   # the service calls decide()
            last_recommendation = OverviewRecommendationDto(action=rec.action, reason=rec.reason)

        by_zone: dict[UUID, list[Device]] = defaultdict(list)
        for device in assigned:
            by_zone[device.zone_id].append(device)

        return LocationOverviewDto(
            location=LocationSummaryDto(id=UUID(location_row.id), name=location_row.name),
            device_counts=DeviceCountsDto(
                sensor=sum(1 for d in assigned if d.role == "sensor"),
                actuator=sum(1 for d in assigned if d.role == "actuator"),
            ),
            zones=[
                OverviewZoneDto(
                    id=UUID(z.id),
                    name=z.name,
                    moisture_threshold_low=float(z.moisture_threshold_low),
                    moisture_threshold_high=float(z.moisture_threshold_high),
                    devices=[_device_dto(d) for d in by_zone[UUID(z.id)]],
                    latest_readings=[
                        _reading_dto(d, latest[d.id])
                        for d in by_zone[UUID(z.id)]
                        if d.id in latest           
                    ],
                )
                for z in zone_rows
            ],
            strategy_key=strategy_key,
            last_recommendation=last_recommendation,
        )


def _device_dto(device: Device) -> OverviewDeviceDto:
    return OverviewDeviceDto(
        id=device.id,
        device_type=device.device_type,
        role=device.role,
        display_name=device.display_name,
    )


def _reading_dto(device: Device, reading: Reading) -> OverviewReadingDto:
    return OverviewReadingDto(
        device_id=device.id,
        value=reading.value,
        unit=reading.unit,
        recorded_at=reading.recorded_at,
        tracking_enabled=device.tracking_enabled,                   
        sampling_interval_seconds=device.sampling_interval_seconds, 
    )