"""
DC-Guardian Evidence
Dedicated Environmental Sensor Monitor
"""

from evidence.environmental_monitoring.src.config import (
    SOURCE_ENVIRONMENTAL_SENSOR,
)

from evidence.environmental_monitoring.src.environmental_detector import (
    assess_environmental_condition,
)


def assess_sensor_reading(
    *,
    sensor_id,
    observation_timestamp,
    temperature_c=None,
    humidity_pct=None,
):
    """
    Assess one reading from a dedicated environmental sensor.
    """

    if (
        not isinstance(sensor_id, str)
        or not sensor_id.strip()
    ):
        raise ValueError(
            "sensor_id must be a non-empty string."
        )

    return assess_environmental_condition(
        source_class=
            SOURCE_ENVIRONMENTAL_SENSOR,

        source_id=
            sensor_id,

        observation_timestamp=
            observation_timestamp,

        temperature_c=
            temperature_c,

        humidity_pct=
            humidity_pct,

        source_asset_type=
            "ENVIRONMENTAL_SENSOR",
    )
