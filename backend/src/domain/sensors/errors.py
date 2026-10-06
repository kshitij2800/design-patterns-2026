class SensorReadError(Exception):
    """An adapter could not produce a valid Reading (bad payload, unsupported device...)."""