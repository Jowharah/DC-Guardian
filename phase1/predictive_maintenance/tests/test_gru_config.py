"""
DC-Guardian Predictive Maintenance
GRU Configuration Contract Test
"""

from phase1.predictive_maintenance.src.gru.config import (
    GRU_BATCH_SIZE,
    GRU_FAILURE_HORIZON_DAYS,
    GRU_HIDDEN_SIZE,
    GRU_INPUT_SIZE,
    GRU_NEGATIVE_TO_POSITIVE_RATIO,
    GRU_NUM_LAYERS,
    GRU_REQUIRE_CONSECUTIVE_DAYS,
    GRU_SEQUENCE_LENGTH,
    GRU_SMART_FEATURES,
    GRU_TEST_PERIOD,
    GRU_TRAIN_PERIODS,
    GRU_VALIDATION_PERIOD,
    RF_BENCHMARK_PR_AUC,
)


print(
    "\n============================================"
)
print(
    "DC-GUARDIAN GRU CONFIG TEST"
)
print(
    "============================================"
)


assert GRU_SEQUENCE_LENGTH == 30

assert GRU_FAILURE_HORIZON_DAYS == 7

assert len(
    GRU_SMART_FEATURES
) == 8

assert GRU_INPUT_SIZE == 8

assert GRU_HIDDEN_SIZE == 64

assert GRU_NUM_LAYERS == 1

assert GRU_BATCH_SIZE == 512

assert (
    GRU_NEGATIVE_TO_POSITIVE_RATIO
    == 50
)

assert (
    GRU_REQUIRE_CONSECUTIVE_DAYS
    is True
)


assert GRU_TRAIN_PERIODS == [
    "2025_Q2",
    "2025_Q3",
]

assert (
    GRU_VALIDATION_PERIOD
    == "2025_Q4"
)

assert (
    GRU_TEST_PERIOD
    == "2026_Q1"
)


assert RF_BENCHMARK_PR_AUC == 0.028004


print(
    "PASS: 30-observation sequence."
)

print(
    "PASS: 8 common SMART channels."
)

print(
    "PASS: 7-day prediction horizon."
)

print(
    "PASS: Consecutive-day requirement enabled."
)

print(
    "PASS: 50:1 training sampling."
)

print(
    "PASS: GRU architecture frozen."
)

print(
    "PASS: Q2/Q3 training boundary."
)

print(
    "PASS: Q4 validation boundary."
)

print(
    "PASS: 2026 Q1 remains locked."
)

print(
    "PASS: Frozen RF benchmark recorded."
)


print(
    "\n============================================"
)
print(
    "GRU CONFIG CONTRACT PASSED"
)
print(
    "============================================"
)