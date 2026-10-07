from evidence.environmental_monitoring.src.config import (
    SOURCE_ENVIRONMENTAL_SENSOR,
    SOURCE_HARDWARE_TELEMETRY,
)

from evidence.environmental_monitoring.src.environmental_detector import (
    assess_environmental_condition,
)


print(
    "\n============================================"
)
print(
    "DC-GUARDIAN ENVIRONMENTAL DETECTOR TEST"
)
print(
    "============================================"
)


# ============================================================
# 1. Normal dedicated sensor
# ============================================================

normal = assess_environmental_condition(
    source_class=
        SOURCE_ENVIRONMENTAL_SENSOR,

    source_id=
        "SEN-B-01",

    observation_timestamp=
        "2026-09-18T12:00:00Z",

    temperature_c=
        24.0,

    humidity_pct=
        45.0,

    source_asset_type=
        "ENVIRONMENTAL_SENSOR",
)


assert (
    normal[
        "assessment"
    ]
    == "NORMAL"
)

assert (
    normal[
        "anomaly_detected"
    ]
    is False
)

print(
    "PASS: Normal sensor condition."
)


# ============================================================
# 2. High-temperature dedicated sensor
# ============================================================

hot_sensor = assess_environmental_condition(
    source_class=
        SOURCE_ENVIRONMENTAL_SENSOR,

    source_id=
        "SEN-B-01",

    observation_timestamp=
        "2026-09-18T12:03:00Z",

    temperature_c=
        42.5,

    humidity_pct=
        48.0,

    source_asset_type=
        "ENVIRONMENTAL_SENSOR",
)


assert (
    hot_sensor[
        "assessment"
    ]
    == "HIGH_TEMPERATURE"
)

assert (
    hot_sensor[
        "anomaly_detected"
    ]
    is True
)

assert (
    "HIGH_TEMPERATURE"
    in hot_sensor[
        "evidence"
    ][
        "triggered_conditions"
    ]
)

print(
    "PASS: High-temperature sensor condition."
)


# ============================================================
# 3. Hardware-origin temperature
# ============================================================

hot_hardware = assess_environmental_condition(
    source_class=
        SOURCE_HARDWARE_TELEMETRY,

    source_id=
        "DRV-HW-001",

    observation_timestamp=
        "2026-09-18T12:04:00Z",

    temperature_c=
        41.0,

    source_asset_type=
        "HARD_DRIVE",
)


assert (
    hot_hardware[
        "assessment"
    ]
    == "HIGH_TEMPERATURE"
)

assert (
    hot_hardware[
        "source_class"
    ]
    == "HARDWARE_TELEMETRY"
)

assert (
    hot_hardware[
        "source_asset_type"
    ]
    == "HARD_DRIVE"
)

print(
    "PASS: Hardware telemetry condition."
)


# ============================================================
# 4. High humidity
# ============================================================

humid = assess_environmental_condition(
    source_class=
        SOURCE_ENVIRONMENTAL_SENSOR,

    source_id=
        "SEN-A-01",

    observation_timestamp=
        "2026-09-18T12:05:00Z",

    humidity_pct=
        90.0,
)


assert (
    humid[
        "assessment"
    ]
    == "HIGH_HUMIDITY"
)

print(
    "PASS: High-humidity condition."
)


# ============================================================
# 5. Multiple conditions preserved
# ============================================================

multiple = assess_environmental_condition(
    source_class=
        SOURCE_ENVIRONMENTAL_SENSOR,

    source_id=
        "SEN-B-01",

    observation_timestamp=
        "2026-09-18T12:06:00Z",

    temperature_c=
        42.0,

    humidity_pct=
        90.0,
)


assert (
    multiple[
        "assessment"
    ]
    == "HIGH_TEMPERATURE"
)

assert set(
    multiple[
        "evidence"
    ][
        "triggered_conditions"
    ]
) == {
    "HIGH_TEMPERATURE",
    "HIGH_HUMIDITY",
}


print(
    "PASS: Multiple environmental "
    "conditions preserved."
)


# ============================================================
# 6. Invalid input
# ============================================================

invalid_rejected = False


try:

    assess_environmental_condition(
        source_class=
            SOURCE_ENVIRONMENTAL_SENSOR,

        source_id=
            "SEN-B-01",

        observation_timestamp=
            "2026-09-18T12:07:00Z",

        humidity_pct=
            120.0,
    )

except ValueError:

    invalid_rejected = True


assert invalid_rejected


print(
    "PASS: Invalid measurement rejected."
)


# ============================================================
# Final
# ============================================================

print(
    "\n============================================"
)
print(
    "ENVIRONMENTAL DETECTOR CONTRACT PASSED"
)
print(
    "============================================"
)
