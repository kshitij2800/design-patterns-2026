import pytest

from domain.locations.config_builder import LocationConfigBuilder
from domain.locations.errors import ConfigurationError


def valid_builder() -> LocationConfigBuilder:
    return LocationConfigBuilder().with_location_name("Lab Site A").add_zone(
        "Bench 1", 0.2, 0.45, {"watering": "08:00"}
    )


def test_build_success():
    config = valid_builder().add_zone("Bench 2", 0.1, 0.3).build()

    assert config.location.name == "Lab Site A"
    assert [z.name for z in config.location.zones] == ["Bench 1", "Bench 2"]
    assert config.location.zones[0].schedule == {"watering": "08:00"}
    assert config.location.id is None
    assert all(z.id is None for z in config.location.zones)


def test_build_is_deterministic():
    assert valid_builder().build() == valid_builder().build()


def test_build_requires_name():
    with pytest.raises(ConfigurationError, match="Location name is required"):
        LocationConfigBuilder().add_zone("Bench 1", 0.2, 0.45).build()


def test_build_rejects_blank_name():
    with pytest.raises(ConfigurationError, match="Location name is required"):
        LocationConfigBuilder().with_location_name("   ").add_zone("Bench 1", 0.2, 0.45).build()


def test_build_requires_zones():
    with pytest.raises(ConfigurationError, match="At least one zone is required"):
        LocationConfigBuilder().with_location_name("Lab Site A").build()


@pytest.mark.parametrize(
    "low, high",
    [
        (0.5, 0.2),   # inverted
        (0.3, 0.3),   # equal is not strictly less
        (-0.1, 0.4),  # below range
        (0.2, 1.5),   # above range
    ],
)
def test_build_rejects_invalid_thresholds(low, high):
    with pytest.raises(ConfigurationError):
        LocationConfigBuilder().with_location_name("L").add_zone("Z", low, high).build()


def test_build_rejects_duplicate_zone_names():
    builder = LocationConfigBuilder().with_location_name("L").add_zone("Bench", 0.1, 0.2).add_zone("bench", 0.1, 0.2)
    with pytest.raises(ConfigurationError, match="Duplicate zone name"):
        builder.build()


def test_same_zone_name_allowed_in_different_locations():
    a = LocationConfigBuilder().with_location_name("A").add_zone("Bench 1", 0.1, 0.2).build()
    b = LocationConfigBuilder().with_location_name("B").add_zone("Bench 1", 0.1, 0.2).build()
    assert a.location.zones[0].name == b.location.zones[0].name


def test_builder_has_no_add_device():
    assert not hasattr(LocationConfigBuilder, "add_device")