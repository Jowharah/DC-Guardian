"""
DC-Guardian Phase 1
Predictive Maintenance GRU Configuration

Experimental deep-learning challenger to the frozen
Temporal Random Forest v2.

Development boundary:
    TRAIN      = 2025 Q2 + Q3
    VALIDATION = 2025 Q4
    FINAL TEST = 2026 Q1 (LOCKED)

The GRU must not access the final test period during
model development or selection.
"""

from pathlib import Path

from phase1.predictive_maintenance.src.config import (
    BASE_SMART_FEATURES,
    PROCESSED_DATA_DIR,
    RANDOM_STATE,
    TEST_PERIOD,
    TRAIN_PERIODS,
    VALIDATION_PERIOD,
)


# ============================================================
# Model identity
# ============================================================

GRU_MODEL_NAME = (
    "DC_Guardian_GRU_v1"
)


# ============================================================
# Sequence contract
# ============================================================

GRU_SMART_FEATURES = list(
    BASE_SMART_FEATURES
)

GRU_SEQUENCE_LENGTH = 30

GRU_FAILURE_HORIZON_DAYS = 7

GRU_REQUIRE_CONSECUTIVE_DAYS = True


# ============================================================
# Training sampling
# ============================================================

GRU_NEGATIVE_TO_POSITIVE_RATIO = 50


# ============================================================
# Architecture
# ============================================================

GRU_INPUT_SIZE = len(
    GRU_SMART_FEATURES
)

GRU_HIDDEN_SIZE = 64

GRU_NUM_LAYERS = 1

GRU_DROPOUT = 0.0


# ============================================================
# Optimization
# ============================================================

GRU_BATCH_SIZE = 512

GRU_LEARNING_RATE = 1e-3

GRU_WEIGHT_DECAY = 1e-5

GRU_MAX_EPOCHS = 30

GRU_EARLY_STOPPING_PATIENCE = 5


# ============================================================
# Reproducibility
# ============================================================

GRU_RANDOM_STATE = RANDOM_STATE


# ============================================================
# Dataset paths
# ============================================================

GRU_DATA_DIR = (
    PROCESSED_DATA_DIR
    / "maintenance_v2_gru"
)

GRU_INDEX_DIR = (
    GRU_DATA_DIR
    / "sequence_indexes"
)


# ============================================================
# Model output
# ============================================================

GRU_MODEL_DIR = (
    Path(__file__)
    .resolve()
    .parents[2]
    / "models"
    / "gru"
)

GRU_MODEL_FILE = (
    GRU_MODEL_DIR
    / "gru_v1.pt"
)

GRU_METADATA_FILE = (
    GRU_MODEL_DIR
    / "gru_v1_metadata.json"
)


# ============================================================
# Frozen RF challenger benchmark
#
# Standalone Q4 validation result.
# ============================================================

RF_BENCHMARK_PR_AUC = 0.028004

RF_BENCHMARK_ROC_AUC = 0.892056

RF_BENCHMARK_DRIVE_RECALL = 0.49603803

RF_BENCHMARK_ALERTS_PER_1000 = 1.913

RF_BENCHMARK_MEDIAN_LEAD_TIME_DAYS = 6.0


# ============================================================
# Temporal boundary aliases
# ============================================================

GRU_TRAIN_PERIODS = list(
    TRAIN_PERIODS
)

GRU_VALIDATION_PERIOD = (
    VALIDATION_PERIOD
)

GRU_TEST_PERIOD = (
    TEST_PERIOD
)

# ============================================================
# Sequence store
# ============================================================

GRU_SEQUENCE_STORE_DIR = (
    GRU_DATA_DIR
    / "sequence_store"
)

GRU_TRAIN_SEQUENCE_FILE = (
    GRU_SEQUENCE_STORE_DIR
    / "train_sequences.npy"
)

GRU_TRAIN_LABEL_FILE = (
    GRU_SEQUENCE_STORE_DIR
    / "train_labels.npy"
)

GRU_TRAIN_METADATA_FILE = (
    GRU_SEQUENCE_STORE_DIR
    / "train_sequence_metadata.parquet"
)

GRU_NORMALIZATION_FILE = (
    GRU_SEQUENCE_STORE_DIR
    / "training_normalization.npz"
)

# ============================================================
# GRU preprocessing
# ============================================================

GRU_LOG1P_FEATURES = [
    "smart_5_raw",
    "smart_192_raw",
    "smart_193_raw",
    "smart_198_raw",
    "smart_4_raw",
    "smart_12_raw",
]

GRU_CLIP_VALUE = 10.0

# ============================================================
# Development validation sampling
# ============================================================

GRU_VALIDATION_NEGATIVE_RATIO = 100

GRU_VALIDATION_SAMPLE_FILE = (
    GRU_INDEX_DIR
    / "gru_validation_sample.parquet"
)

# ============================================================
# Validation sequence store
# ============================================================

GRU_VALIDATION_SEQUENCE_FILE = (
    GRU_SEQUENCE_STORE_DIR
    / "validation_sequences.npy"
)

GRU_VALIDATION_LABEL_FILE = (
    GRU_SEQUENCE_STORE_DIR
    / "validation_labels.npy"
)

GRU_VALIDATION_METADATA_FILE = (
    GRU_SEQUENCE_STORE_DIR
    / "validation_sequence_metadata.parquet"
)

# ============================================================
# Full Q4 evaluation artifacts
# ============================================================

GRU_EVALUATION_DIR = (
    GRU_DATA_DIR
    / "evaluation"
)

GRU_Q4_PROBABILITY_FILE = (
    GRU_EVALUATION_DIR
    / "q4_gru_probabilities.npy"
)

GRU_Q4_EVALUATION_METADATA_FILE = (
    GRU_EVALUATION_DIR
    / "q4_evaluation_metadata.parquet"
)