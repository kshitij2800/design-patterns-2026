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