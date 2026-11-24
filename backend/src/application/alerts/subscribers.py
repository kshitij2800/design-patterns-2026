from __future__ import annotations
from collections.abc import Callable
from uuid import UUID

from sqlalchemy.orm import Session

from domain.events.bus import EventBus
from domain.events.events import ActuatorStateChanged, CommandFailed, ReadingCreated, ThresholdCrossed
from infrastructure.persistence.alert_repository import AlertRepository
from infrastructure.persistence.models import ZoneRow

# Given a zone id, return that zone's moisture_threshold_low (None if the zone is gone).
ZoneLowLookup = Callable[[UUID], float | None]


class MoistureThresholdSubscriber:
    """Listens for reading.created. Publishes threshold.crossed when:
    unit is vwc, the reading has a zone, and value < zone.moisture_threshold_low (strictly)."""

    def __init__(self, bus: EventBus, zone_low: ZoneLowLookup) -> None:
        self._bus = bus
        self._zone_low = zone_low

    def on_reading(self, event: ReadingCreated) -> None:
        if event.unit != "vwc" or event.zone_id is None:
            return                                   # no zone -> no threshold event
        low = self._zone_low(event.zone_id)
        if low is None or not event.value < low:
            return
        self._bus.publish(
            ThresholdCrossed(
                device_id=event.device_id,
                location_id=event.location_id,
                zone_id=event.zone_id,
                moisture=event.value,
                threshold_low=low,
            )
        )


class AlertPersistenceSubscriber:
    """The only code that inserts alerts rows."""

    def __init__(self, alerts: AlertRepository) -> None:
        self._alerts = alerts

    def on_threshold(self, event: ThresholdCrossed) -> None:
        self._insert(event, "warning", "Moisture below zone low")

    def on_command(self, event: CommandFailed) -> None:
        self._insert(event, "warning", event.message)       # e.g. "Max run time exceeded"

    def on_state(self, event: ActuatorStateChanged) -> None:
        if event.state != "error":
            return                                          # only error is alert-worthy
        self._insert(event, "critical", "Actuator entered error")

    def _insert(self, event, severity: str, message: str) -> None:
        self._alerts.insert(
            event_type=event.event_type,
            severity=severity,
            message=message,
            device_id=event.device_id,
            location_id=event.location_id,
            zone_id=event.zone_id,
        )


def build_event_bus(session: Session) -> EventBus:
    """Composition root: one EventBus with both subscribers attached.
    Routers and the sampler loop call this and inject the bus into the publishers."""
    bus = EventBus()

    def zone_low(zone_id: UUID) -> float | None:
        zone = session.get(ZoneRow, str(zone_id))
        return float(zone.moisture_threshold_low) if zone else None   # NUMERIC -> Decimal -> float

    threshold = MoistureThresholdSubscriber(bus, zone_low)
    persistence = AlertPersistenceSubscriber(AlertRepository(session))

    bus.subscribe(ReadingCreated, threshold.on_reading)
    bus.subscribe(ThresholdCrossed, persistence.on_threshold)
    bus.subscribe(CommandFailed, persistence.on_command)
    bus.subscribe(ActuatorStateChanged, persistence.on_state)
    return bus