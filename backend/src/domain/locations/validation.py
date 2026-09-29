from domain.locations.errors import ConfigurationError

MIN_VWC = 0.0
MAX_VWC = 1.0


def validate_zone_fields(name: str, low: float, high: float) -> str:
    """Check the rules every zone must satisfy. Returns the trimmed name."""
    clean = (name or "").strip()
    if not clean:
        raise ConfigurationError("Zone name is required")
    for label, value in (("low", low), ("high", high)):
        if not (MIN_VWC <= value <= MAX_VWC):
            raise ConfigurationError(
                f"Zone '{clean}': {label} threshold must be between {MIN_VWC} and {MAX_VWC}"
            )
    if low >= high:
        raise ConfigurationError(
            f"Zone '{clean}': low threshold must be strictly less than high threshold"
        )
    return clean