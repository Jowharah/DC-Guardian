"""
DC-Guardian Evidence
Predictive Maintenance Configuration

Frozen development configuration for Maintenance Model v2.
"""

from pathlib import Path


# ============================================================
# Project paths
# ============================================================

MAINTENANCE_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

DATA_DIR = (
    MAINTENANCE_ROOT
    / "data"
)

RAW_DATA_DIR = (
    DATA_DIR
    / "raw"
    / "backblaze"
)

PROCESSED_DATA_DIR = (
    DATA_DIR
    / "processed"
)

FEATURE_DATA_DIR = (
    PROCESSED_DATA_DIR
    / "maintenance_v2_features"
)

MODEL_DIR = (
    MAINTENANCE_ROOT
    / "models"
)

RF_MODEL_DIR = (
    MODEL_DIR
    / "rf"
)


# ============================================================
# Reproducibility
# ============================================================

RANDOM_STATE = 42


# ============================================================
# Prediction task
# ============================================================

FAILURE_HORIZON_DAYS = 7


# ============================================================
# Temporal evaluation split
# ============================================================

TRAIN_PERIODS = [
    "2025_Q2",
    "2025_Q3",
]

VALIDATION_PERIOD = "2025_Q4"

TEST_PERIOD = "2026_Q1"


# ============================================================
# Common SMART telemetry
# ============================================================

BASE_SMART_FEATURES = [
    "smart_5_raw",
    "smart_9_raw",
    "smart_192_raw",
    "smart_193_raw",
    "smart_194_raw",
    "smart_198_raw",
    "smart_4_raw",
    "smart_12_raw",
]


# ============================================================
# Temporal Random Forest feature contract
# ============================================================

TEMPORAL_RF_FEATURES = (
    BASE_SMART_FEATURES
    + [
        "smart_5_nonzero",
        "smart_198_nonzero",
        "smart_5_increased",
        "smart_198_increased",

        "smart_5_raw_delta_1",
        "smart_5_raw_delta_7",

        "smart_9_raw_delta_1",
        "smart_9_raw_delta_7",

        "smart_192_raw_delta_1",
        "smart_192_raw_delta_7",

        "smart_193_raw_delta_1",
        "smart_193_raw_delta_7",

        "smart_194_raw_delta_1",
        "smart_194_raw_delta_7",

        "smart_198_raw_delta_1",
        "smart_198_raw_delta_7",

        "smart_4_raw_delta_1",
        "smart_4_raw_delta_7",

        "smart_12_raw_delta_1",
        "smart_12_raw_delta_7",

        "temperature_7obs_mean",
        "temperature_7obs_max",
        "temperature_7obs_min",
        "temperature_7obs_range",
        "temperature_vs_7obs_mean",
    ]
)


# ============================================================
# Frozen Random Forest candidate
# ============================================================

RF_NEGATIVE_TO_POSITIVE_RATIO = 50

RF_N_ESTIMATORS = 300

RF_MAX_DEPTH = None

RF_MIN_SAMPLES_LEAF = 2

RF_MAX_FEATURES = "sqrt"


# ============================================================
# Candidate operating threshold
# ============================================================

RF_OPERATING_THRESHOLD = 0.45


# ============================================================
# Development reference results
#
# Q4 validation results only.
# These are NOT final 2026 Q1 test results.
# ============================================================

REFERENCE_Q4_PR_AUC = 0.028492

REFERENCE_Q4_ROC_AUC = 0.891983

REFERENCE_Q4_DRIVE_RECALL = 0.507132

REFERENCE_Q4_ALERTS_PER_1000 = 2.013432

REFERENCE_Q4_MEDIAN_LEAD_TIME_DAYS = 6.0

# ============================================================
# Standalone frozen-model Q4 validation reference
# ============================================================

STANDALONE_Q4_PR_AUC = 0.028004

STANDALONE_Q4_ROC_AUC = 0.892056

STANDALONE_Q4_PRECISION = 0.03141027

STANDALONE_Q4_ROW_RECALL = 0.30821545

STANDALONE_Q4_DRIVE_RECALL = 0.49603803

STANDALONE_Q4_ALERTS_PER_1000 = 1.913

STANDALONE_Q4_MEDIAN_LEAD_TIME_DAYS = 6.0

# ============================================================
# Immutable 2026 Q1 final holdout result
#
# Do NOT use these values for model development or tuning.
# ============================================================

FINAL_TEST_PERIOD = "2026_Q1"

FINAL_Q1_ROWS = 17_064_047
FINAL_Q1_POSITIVE_ROWS = 4_285
FINAL_Q1_FAILED_DRIVES = 667

FINAL_Q1_PR_AUC = 0.033474
FINAL_Q1_ROC_AUC = 0.872341
FINAL_Q1_PR_LIFT = 133.30

FINAL_Q1_PRECISION = 0.03382016
FINAL_Q1_ROW_RECALL = 0.33722287
FINAL_Q1_DRIVE_RECALL = 0.48425787

FINAL_Q1_ALERTS_PER_1000 = 2.504
FINAL_Q1_MEDIAN_LEAD_TIME_DAYS = 7.0
FINAL_Q1_MEAN_LEAD_TIME_DAYS = 5.45

FINAL_Q1_DETECTED_FAILED_DRIVES = 323
FINAL_Q1_SEVEN_DAY_WARNINGS = 170