"""
DC-Guardian Evidence
Environmental Monitoring Configuration

Environmental monitoring is independent from predictive
maintenance.

It accepts environmental evidence originating from:
    1. dedicated environmental sensors
    2. hardware telemetry
"""


# ============================================================
# Component identity
# ============================================================

ENVIRONMENTAL_COMPONENT = (
    "environmental_detector"
)

ENVIRONMENTAL_COMPONENT_VERSION = (
    "1.0"
)

ENVIRONMENTAL_EVENT_TYPE = (
    "ENVIRONMENTAL_CONDITION_ASSESSMENT"
)


# ============================================================
# Evidence source classes
# ============================================================

SOURCE_ENVIRONMENTAL_SENSOR = (
    "ENVIRONMENTAL_SENSOR"
)

SOURCE_HARDWARE_TELEMETRY = (
    "HARDWARE_TELEMETRY"
)


SUPPORTED_SOURCE_CLASSES = {
    SOURCE_ENVIRONMENTAL_SENSOR,
    SOURCE_HARDWARE_TELEMETRY,
}


# ============================================================
# Environmental measurements
# ============================================================

MEASUREMENT_TEMPERATURE = (
    "TEMPERATURE"
)

MEASUREMENT_HUMIDITY = (
    "HUMIDITY"
)

MEASUREMENT_AIRFLOW = (
    "AIRFLOW"
)

MEASUREMENT_SMOKE = (
    "SMOKE"
)

MEASUREMENT_WATER_LEAK = (
    "WATER_LEAK"
)


SUPPORTED_MEASUREMENT_TYPES = {
    MEASUREMENT_TEMPERATURE,
    MEASUREMENT_HUMIDITY,
    MEASUREMENT_AIRFLOW,
    MEASUREMENT_SMOKE,
    MEASUREMENT_WATER_LEAK,
}


# ============================================================
# Assessment states
# ============================================================

STATE_NORMAL = (
    "NORMAL"
)

STATE_HIGH_TEMPERATURE = (
    "HIGH_TEMPERATURE"
)

STATE_HIGH_HUMIDITY = (
    "HIGH_HUMIDITY"
)

STATE_LOW_HUMIDITY = (
    "LOW_HUMIDITY"
)

STATE_AIRFLOW_ANOMALY = (
    "AIRFLOW_ANOMALY"
)

STATE_SMOKE_DETECTED = (
    "SMOKE_DETECTED"
)

STATE_WATER_LEAK_DETECTED = (
    "WATER_LEAK_DETECTED"
)


ABNORMAL_ENVIRONMENTAL_STATES = {
    STATE_HIGH_TEMPERATURE,
    STATE_HIGH_HUMIDITY,
    STATE_LOW_HUMIDITY,
    STATE_AIRFLOW_ANOMALY,
    STATE_SMOKE_DETECTED,
    STATE_WATER_LEAK_DETECTED,
}


# ============================================================
# Initial controlled thresholds
#
# These are detector configuration values, not learned
# machine-learning parameters.
#
# We can revise these once the actual environmental data
# source/specification is selected.
# ============================================================

TEMPERATURE_HIGH_C = 35.0

HUMIDITY_LOW_PCT = 20.0

HUMIDITY_HIGH_PCT = 80.0