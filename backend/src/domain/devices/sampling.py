MIN_SAMPLING_INTERVAL_SECONDS = 5


class InvalidSamplingIntervalError(ValueError):
    pass


def validate_sampling_interval(seconds: int) -> None:
    if seconds < MIN_SAMPLING_INTERVAL_SECONDS:
        raise InvalidSamplingIntervalError(
            f"sampling_interval_seconds must be at least {MIN_SAMPLING_INTERVAL_SECONDS}"
        )