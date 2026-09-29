from domain.locations.entity import Location, LocationConfig, Zone
from domain.locations.errors import ConfigurationError
from domain.locations.validation import validate_zone_fields


class LocationConfigBuilder:
    def __init__(self) -> None:
        self._name: str | None = None
        self._zones: list[Zone] = []

    def with_location_name(self, name: str) -> "LocationConfigBuilder":
        self._name = name
        return self

    def add_zone(
        self,
        name: str,
        moisture_threshold_low: float,
        moisture_threshold_high: float,
        schedule: dict | None = None,
    ) -> "LocationConfigBuilder":
        self._zones.append(
            Zone(name, moisture_threshold_low, moisture_threshold_high, dict(schedule or {}))
        )
        return self

    def build(self) -> LocationConfig:
        location_name = (self._name or "").strip()
        if not location_name:
            raise ConfigurationError("Location name is required")
        if not self._zones:
            raise ConfigurationError("At least one zone is required")

        seen: set[str] = set()
        checked: list[Zone] = []
        for z in self._zones:
            clean = validate_zone_fields(
                z.name, z.moisture_threshold_low, z.moisture_threshold_high
            )
            key = clean.casefold()
            if key in seen:
                raise ConfigurationError(f"Duplicate zone name: '{clean}'")
            seen.add(key)
            checked.append(
                Zone(clean, z.moisture_threshold_low, z.moisture_threshold_high, dict(z.schedule))
            )

        return LocationConfig(Location(name=location_name, zones=tuple(checked)))