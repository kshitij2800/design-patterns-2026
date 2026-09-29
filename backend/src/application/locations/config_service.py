from uuid import UUID

from application.locations.dto import LocationConfigReadDto, LocationConfigRequestDto
from application.locations.mappers import config_to_dto
from domain.locations.config_builder import LocationConfigBuilder
from infrastructure.persistence.location_repository import LocationRepository


class LocationConfigService:
    def __init__(self, repository: LocationRepository) -> None:
        self._repo = repository

    def build_and_save(self, request: LocationConfigRequestDto) -> LocationConfigReadDto:
        builder = LocationConfigBuilder().with_location_name(request.location_name)
        for z in request.zones:
            builder.add_zone(z.name, z.moisture_threshold_low, z.moisture_threshold_high, z.schedule)
        config = builder.build()

        location_row, zone_rows = self._repo.save_config(config)
        return config_to_dto(location_row, zone_rows)

    def get(self, location_id: UUID) -> LocationConfigReadDto | None:
        result = self._repo.get_config(location_id)
        if result is None:
            return None
        location_row, zone_rows = result
        return config_to_dto(location_row, zone_rows)