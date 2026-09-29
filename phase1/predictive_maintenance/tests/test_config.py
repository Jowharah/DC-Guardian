"""
DC-Guardian Predictive Maintenance
Configuration Contract Test
"""

from phase1.predictive_maintenance.src.config import (
    BASE_SMART_FEATURES,
    FAILURE_HORIZON_DAYS,
    RF_NEGATIVE_TO_POSITIVE_RATIO,
    RF_OPERATING_THRESHOLD,
    TEMPORAL_RF_FEATURES,
    TEST_PERIOD,
    TRAIN_PERIODS,
    VALIDATION_PERIOD,
)


print(
    "\n============================================"
)

print(
    "DC-GUARDIAN MAINTENANCE CONFIG TEST"
)

print(
    "============================================"
)


assert FAILURE_HORIZON_DAYS == 7

assert TRAIN_PERIODS == [
    "2025_Q2",
    "2025_Q3",
]

assert VALIDATION_PERIOD == "2025_Q4"

assert TEST_PERIOD == "2026_Q1"

assert len(
    BASE_SMART_FEATURES
) == 8

assert len(
    TEMPORAL_RF_FEATURES
) == 33

assert (
    RF_NEGATIVE_TO_POSITIVE_RATIO
    == 50
)

assert (
    RF_OPERATING_THRESHOLD
    == 0.45
)


assert len(
    TEMPORAL_RF_FEATURES
) == len(
    set(
        TEMPORAL_RF_FEATURES
    )
)


print(
    "PASS: 7-day prediction horizon."
)

print(
    "PASS: Temporal split frozen."
)

print(
    "PASS: 8 common SMART signals."
)

print(
    "PASS: 33 Temporal RF features."
)

print(
    "PASS: 50:1 training ratio."
)

print(
    "PASS: Candidate threshold = 0.45."
)


print(
    "\n============================================"
)

print(
    "MAINTENANCE CONFIG CONTRACT PASSED"
)

print(
    "============================================"
)