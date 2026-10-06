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