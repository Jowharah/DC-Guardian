"""
DC-Guardian Evidence
Environmental Monitoring Detector

Creates a common environmental assessment from measurements
originating from either:

    - dedicated environmental sensors
    - hardware telemetry

This component performs deterministic environmental assessment.
"""

from datetime import datetime, timezone
import math

from evidence.environmental_monitoring.src.config import (
    ENVIRONMENTAL_COMPONENT,
    ENVIRONMENTAL_COMPONENT_VERSION,
    ENVIRONMENTAL_EVENT_TYPE,
    HUMIDITY_HIGH_PCT,
    HUMIDITY_LOW_PCT,
    SOURCE_ENVIRONMENTAL_SENSOR,
    SOURCE_HARDWARE_TELEMETRY,
    STATE_HIGH_HUMIDITY,
    STATE_HIGH_TEMPERATURE,
    STATE_LOW_HUMIDITY,
    STATE_NORMAL,
    SUPPORTED_SOURCE_CLASSES,
    TEMPERATURE_HIGH_C,
)


# ============================================================
# Timestamp normalization
# ============================================================

def normalize_timestamp(
    value,
):

    if isinstance(
        value,
        datetime,
    ):

        if value.tzinfo is None:

            return (
                value
                .replace(
                    tzinfo=timezone.utc
                )
                .isoformat()
                .replace(
                    "+00:00",
                    "Z",
                )
            )

        return (
            value
            .astimezone(
                timezone.utc
            )
            .isoformat()
            .replace(
                "+00:00",
                "Z",
            )
        )


    if not isinstance(
        value,
        str,
    ):

        raise TypeError(
            "observation_timestamp must be "
            "a datetime or ISO-8601 string."
        )


    try:

        parsed = datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00",
            )
        )

    except ValueError as error:

        raise ValueError(
            "Invalid observation timestamp."
        ) from error


    if parsed.tzinfo is None:

        parsed = parsed.replace(
            tzinfo=timezone.utc
        )


    return (
        parsed
        .astimezone(
            timezone.utc
        )
        .isoformat()
        .replace(
            "+00:00",
            "Z",
        )
    )


# ============================================================
# Numeric validation
# ============================================================

def validate_measurement(
    name,
    value,
):

    if value is None:

        return None


    try:

        value = float(
            value
        )

    except (
        TypeError,
        ValueError,
    ) as error:

        raise ValueError(
            f"{name} must be numeric."
        ) from error


    if not math.isfinite(
        value
    ):

        raise ValueError(
            f"{name} must be finite."
        )


    return value


# ============================================================
# Environmental assessment
# ============================================================

def assess_environmental_condition(
    *,
    source_class,
    source_id,
    observation_timestamp,
    temperature_c=None,
    humidity_pct=None,
    source_asset_type=None,
):
    """
    Produce one normalized environmental assessment.

    At least one supported environmental measurement must
    be supplied.

    This initial contract supports temperature and humidity.
    Airflow, smoke, and leak measurements can be added through
    the same contract later.
    """

    # ========================================================
    # Source contract
    # ========================================================

    if (
        source_class
        not in SUPPORTED_SOURCE_CLASSES
    ):

        raise ValueError(
            "Unsupported environmental "
            f"source class: {source_class}"
        )


    if (
        not isinstance(
            source_id,
            str,
        )
        or
        not source_id.strip()
    ):

        raise ValueError(
            "source_id must be "
            "a non-empty string."
        )


    timestamp = normalize_timestamp(
        observation_timestamp
    )


    # ========================================================
    # Measurements
    # ========================================================

    temperature_c = (
        validate_measurement(
            "temperature_c",
            temperature_c,
        )
    )


    humidity_pct = (
        validate_measurement(
            "humidity_pct",
            humidity_pct,
        )
    )


    if (
        temperature_c is None
        and
        humidity_pct is None
    ):

        raise ValueError(
            "At least one environmental "
            "measurement is required."
        )


    if (
        humidity_pct is not None
        and not (
            0.0
            <= humidity_pct
            <= 100.0
        )
    ):

        raise ValueError(
            "humidity_pct must be "
            "between 0 and 100."
        )


    # ========================================================
    # Deterministic rules
    # ========================================================

    triggered_conditions = []


    if (
        temperature_c is not None
        and
        temperature_c
        > TEMPERATURE_HIGH_C
    ):

        triggered_conditions.append(
            STATE_HIGH_TEMPERATURE
        )


    if humidity_pct is not None:

        if (
            humidity_pct
            > HUMIDITY_HIGH_PCT
        ):

            triggered_conditions.append(
                STATE_HIGH_HUMIDITY
            )

        elif (
            humidity_pct
            < HUMIDITY_LOW_PCT
        ):

            triggered_conditions.append(
                STATE_LOW_HUMIDITY
            )


    # ========================================================
    # Primary state
    #
    # Initial deterministic priority:
    #
    # temperature
    # > high humidity
    # > low humidity
    # > normal
    #
    # All conditions remain preserved in evidence.
    # ========================================================

    priority = [
        STATE_HIGH_TEMPERATURE,
        STATE_HIGH_HUMIDITY,
        STATE_LOW_HUMIDITY,
    ]


    state = STATE_NORMAL


    for candidate in priority:

        if candidate in (
            triggered_conditions
        ):

            state = candidate
            break


    anomaly_detected = (
        state != STATE_NORMAL
    )


    # ========================================================
    # Evidence
    # ========================================================

    evidence = {
        "triggered_conditions":
            triggered_conditions,

        "measurements": {
            "temperature_c":
                temperature_c,

            "humidity_pct":
                humidity_pct,
        },

        "thresholds": {
            "temperature_high_c":
                TEMPERATURE_HIGH_C,

            "humidity_low_pct":
                HUMIDITY_LOW_PCT,

            "humidity_high_pct":
                HUMIDITY_HIGH_PCT,
        },
    }


    # ========================================================
    # Common Evidence layer environmental contract
    # ========================================================

    return {
        "domain":
            "ENVIRONMENTAL",

        "event_type":
            ENVIRONMENTAL_EVENT_TYPE,

        "component":
            ENVIRONMENTAL_COMPONENT,

        "component_version":
            ENVIRONMENTAL_COMPONENT_VERSION,

        "source_class":
            source_class,

        "source_id":
            source_id,

        "source_asset_type":
            source_asset_type,

        "observation_timestamp":
            timestamp,

        "assessment":
            state,

        "anomaly_detected":
            anomaly_detected,

        "measurements": {
            "temperature_c":
                temperature_c,

            "humidity_pct":
                humidity_pct,
        },

        "evidence":
            evidence,
    }
