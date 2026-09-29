"""
DC-Guardian Predictive Maintenance
Frozen Model Artifact Contract Test
"""

import json

import joblib

from phase1.predictive_maintenance.src.config import (
    FAILURE_HORIZON_DAYS,
    RANDOM_STATE,
    RF_MODEL_DIR,
    RF_NEGATIVE_TO_POSITIVE_RATIO,
    RF_OPERATING_THRESHOLD,
    TEMPORAL_RF_FEATURES,
    TEST_PERIOD,
    TRAIN_PERIODS,
    VALIDATION_PERIOD,
)


MODEL_FILE = (
    RF_MODEL_DIR
    / "temporal_rf_v2.joblib"
)

METADATA_FILE = (
    RF_MODEL_DIR
    / "temporal_rf_v2_metadata.json"
)


print(
    "\n============================================"
)
print(
    "DC-GUARDIAN MAINTENANCE ARTIFACT TEST"
)
print(
    "============================================"
)


assert MODEL_FILE.exists()

assert METADATA_FILE.exists()


print(
    "PASS: Frozen model artifacts exist."
)


pipeline = joblib.load(
    MODEL_FILE
)


assert "imputer" in (
    pipeline.named_steps
)

assert "model" in (
    pipeline.named_steps
)


print(
    "PASS: Frozen preprocessing/model "
    "pipeline loads."
)


with open(
    METADATA_FILE,
    "r",
    encoding="utf-8",
) as file:

    metadata = json.load(
        file
    )


assert (
    metadata["model_name"]
    == "DC_Guardian_Temporal_RF_v2"
)

assert (
    metadata["train_periods"]
    == TRAIN_PERIODS
)

assert (
    metadata["validation_period"]
    == VALIDATION_PERIOD
)

assert (
    metadata["final_test_period"]
    == TEST_PERIOD
)

assert (
    metadata[
        "final_test_used_during_training"
    ]
    is False
)

assert (
    metadata["feature_count"]
    == 33
)

assert (
    metadata["features"]
    == TEMPORAL_RF_FEATURES
)

assert (
    metadata[
        "negative_to_positive_ratio"
    ]
    == RF_NEGATIVE_TO_POSITIVE_RATIO
)

assert (
    metadata[
        "candidate_operating_threshold"
    ]
    == RF_OPERATING_THRESHOLD
)

assert (
    metadata[
        "random_state"
    ]
    == RANDOM_STATE
)


print(
    "PASS: Training metadata matches "
    "frozen configuration."
)


assert (
    metadata[
        "prediction_target"
    ]
    == "explicit failure within next 7 days"
)

assert (
    FAILURE_HORIZON_DAYS
    == 7
)


print(
    "PASS: Seven-day prediction "
    "contract preserved."
)


print(
    "PASS: 2026 Q1 remains marked "
    "as untouched final test."
)


print(
    "\n============================================"
)
print(
    "MAINTENANCE MODEL ARTIFACT CONTRACT PASSED"
)
print(
    "============================================"
)