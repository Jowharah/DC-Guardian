from evidence.environmental_monitoring.src.config import (
    ABNORMAL_ENVIRONMENTAL_STATES,
    SOURCE_ENVIRONMENTAL_SENSOR,
    SOURCE_HARDWARE_TELEMETRY,
    STATE_HIGH_TEMPERATURE,
    STATE_NORMAL,
    SUPPORTED_SOURCE_CLASSES,
    TEMPERATURE_HIGH_C,
)


print(
    "\n============================================"
)
print(
    "DC-GUARDIAN ENVIRONMENTAL CONFIG TEST"
)
print(
    "============================================"
)


assert (
    SOURCE_ENVIRONMENTAL_SENSOR
    in SUPPORTED_SOURCE_CLASSES
)

print(
    "PASS: Dedicated environmental "
    "sensor source supported."
)


assert (
    SOURCE_HARDWARE_TELEMETRY
    in SUPPORTED_SOURCE_CLASSES
)

print(
    "PASS: Hardware telemetry "
    "source supported."
)


assert (
    STATE_HIGH_TEMPERATURE
    in ABNORMAL_ENVIRONMENTAL_STATES
)

print(
    "PASS: High-temperature "
    "environmental state."
)


assert (
    STATE_NORMAL
    not in ABNORMAL_ENVIRONMENTAL_STATES
)

print(
    "PASS: NORMAL is not treated "
    "as abnormal."
)


assert (
    TEMPERATURE_HIGH_C
    > 0
)

print(
    "PASS: Controlled temperature "
    "threshold configured."
)


print(
    "\n============================================"
)
print(
    "ENVIRONMENTAL CONFIG CONTRACT PASSED"
)
print(
    "============================================"
)
