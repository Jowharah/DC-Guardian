"""
DC-Guardian Evidence
Hardware Environmental Telemetry Monitor
"""

from evidence.environmental_monitoring.src.config import (
    SOURCE_HARDWARE_TELEMETRY,
)

from evidence.environmental_monitoring.src.environmental_detector import (
    assess_environmental_condition,
)


SUPPORTED_HARDWARE_ASSET_TYPES = {
    "HARD_DRIVE",
    "SERVER",
    "COOLING_SYSTEM",
}


def assess_hardware_environment(
    *,
    asset_id,
    asset_type,
    observation_timestamp,
    temperature_c=None,
    humidity_pct=None,
):
    """
    Assess environmental telemetry originating from hardware.

    This does not perform predictive maintenance. It describes
    the observed environmental/thermal condition of the asset.
    """

    if (
        not isinstance(asset_id, str)
        or not asset_id.strip()
    ):
        raise ValueError(
            "asset_id must be a non-empty string."
        )

    if (
        asset_type
        not in SUPPORTED_HARDWARE_ASSET_TYPES
    ):
        raise ValueError(
            "Unsupported hardware asset type: "
            f"{asset_type}"
        )

    return assess_environmental_condition(
        source_class=
            SOURCE_HARDWARE_TELEMETRY,

        source_id=
            asset_id,

        observation_timestamp=
            observation_timestamp,

        temperature_c=
            temperature_c,

        humidity_pct=
            humidity_pct,

        source_asset_type=
            asset_type,
    )
