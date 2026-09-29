from phase1.environmental_monitoring.src.hardware_monitor import (
    assess_hardware_environment,
)

from phase1.environmental_monitoring.src.sensor_monitor import (
    assess_sensor_reading,
)


print(
    "\n============================================"
)
print(
    "DC-GUARDIAN ENVIRONMENTAL SOURCE TEST"
)
print(
    "============================================"
)


# ============================================================
# Dedicated environmental sensor
# ============================================================

sensor = assess_sensor_reading(
    sensor_id=
        "SEN-B-01",

    observation_timestamp=
        "2026-09-18T12:03:00Z",

    temperature_c=
        42.5,

    humidity_pct=
        48.0,
)


assert (
    sensor["source_class"]
    == "ENVIRONMENTAL_SENSOR"
)

assert (
    sensor["source_id"]
    == "SEN-B-01"
)

assert (
    sensor["source_asset_type"]
    == "ENVIRONMENTAL_SENSOR"
)

assert (
    sensor["assessment"]
    == "HIGH_TEMPERATURE"
)


print(
    "PASS: Dedicated sensor source contract."
)


# ============================================================
# Hard-drive telemetry
# ============================================================

drive = assess_hardware_environment(
    asset_id=
        "DRV-ENV-001",

    asset_type=
        "HARD_DRIVE",

    observation_timestamp=
        "2026-09-18T12:04:00Z",

    temperature_c=
        41.0,
)


assert (
    drive["source_class"]
    == "HARDWARE_TELEMETRY"
)

assert (
    drive["source_id"]
    == "DRV-ENV-001"
)

assert (
    drive["source_asset_type"]
    == "HARD_DRIVE"
)

assert (
    drive["assessment"]
    == "HIGH_TEMPERATURE"
)


print(
    "PASS: Hard-drive telemetry source contract."
)


# ============================================================
# Server telemetry
# ============================================================

server = assess_hardware_environment(
    asset_id=
        "SRV-B1-01",

    asset_type=
        "SERVER",

    observation_timestamp=
        "2026-09-18T12:04:00Z",

    temperature_c=
        40.0,
)


assert (
    server["source_id"]
    == "SRV-B1-01"
)

assert (
    server["source_asset_type"]
    == "SERVER"
)


print(
    "PASS: Server telemetry source contract."
)


# ============================================================
# Cooling equipment telemetry
# ============================================================

cooling = assess_hardware_environment(
    asset_id=
        "CHILLER-C1",

    asset_type=
        "COOLING_SYSTEM",

    observation_timestamp=
        "2026-09-18T12:04:00Z",

    temperature_c=
        38.0,
)


assert (
    cooling["source_id"]
    == "CHILLER-C1"
)

assert (
    cooling["source_asset_type"]
    == "COOLING_SYSTEM"
)


print(
    "PASS: Cooling-system telemetry source contract."
)


# ============================================================
# Invalid hardware type
# ============================================================

rejected = False


try:

    assess_hardware_environment(
        asset_id=
            "UNKNOWN-001",

        asset_type=
            "UNKNOWN",

        observation_timestamp=
            "2026-09-18T12:05:00Z",

        temperature_c=
            40.0,
    )

except ValueError:

    rejected = True


assert rejected


print(
    "PASS: Unsupported hardware source rejected."
)


# ============================================================
# Source identities remain distinct
# ============================================================

assert (
    sensor["source_class"]
    != drive["source_class"]
)


print(
    "PASS: Sensor and hardware provenance "
    "remain distinguishable."
)


print(
    "\n============================================"
)
print(
    "ENVIRONMENTAL SOURCE CONTRACT PASSED"
)
print(
    "============================================"
)