from domain.sensors.creators import MoistureSensorCreator, LightSensorCreator


def test_moisture_creator_defaults():
    sensor = MoistureSensorCreator().create_sensor()
    assert sensor.device_type == "moisture_sensor"
    assert "moisture_threshold_percent" in sensor.default_config


def test_light_creator_defaults():
    sensor = LightSensorCreator().create_sensor()
    assert sensor.device_type == "light_sensor"
    assert sensor.default_config["unit"] == "lux"


def test_creators_have_different_units():
    moisture = MoistureSensorCreator().create_sensor()
    light = LightSensorCreator().create_sensor()
    assert moisture.default_config["unit"] != light.default_config["unit"]