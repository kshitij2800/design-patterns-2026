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