"""
DC-Guardian Predictive Maintenance
Final Holdout Artifact Contract

Protects the immutable 2026 Q1 evaluation artifact.
"""

import json

from evidence.predictive_maintenance.src.config import (
    FINAL_Q1_DETECTED_FAILED_DRIVES,
    FINAL_Q1_DRIVE_RECALL,
    FINAL_Q1_FAILED_DRIVES,
    FINAL_Q1_MEDIAN_LEAD_TIME_DAYS,
    FINAL_Q1_POSITIVE_ROWS,
    FINAL_Q1_PR_AUC,
    FINAL_Q1_ROC_AUC,
    FINAL_Q1_ROWS,
    FINAL_Q1_SEVEN_DAY_WARNINGS,
    FINAL_TEST_PERIOD,
    PROCESSED_DATA_DIR,
    RF_OPERATING_THRESHOLD,
)


RESULT_FILE = (
    PROCESSED_DATA_DIR
    / "results"
    / "temporal_rf_v2_final_test.json"
)


print(
    "\n============================================"
)
print(
    "DC-GUARDIAN FINAL TEST ARTIFACT TEST"
)
print(
    "============================================"
)


assert RESULT_FILE.exists()

with open(
    RESULT_FILE,
    "r",
    encoding="utf-8",
) as file:

    result = json.load(file)


# ============================================================
# Final-test identity
# ============================================================

assert (
    result["result_type"]
    == "FINAL_HOLDOUT_TEST"
)

assert (
    result["test_period"]
    == FINAL_TEST_PERIOD
)

assert (
    result["model"]
    == "DC_Guardian_Temporal_RF_v2"
)


print(
    "PASS: Final holdout identity."
)


# ============================================================
# No test-set adaptation
# ============================================================

assert (
    result["model_refit_on_test"]
    is False
)

assert (
    result["threshold_selected_on_test"]
    is False
)

assert (
    result["operating_threshold"]
    == RF_OPERATING_THRESHOLD
)


print(
    "PASS: No final-test fitting or threshold selection."
)


# ============================================================
# Population
# ============================================================

assert (
    result["test_rows"]
    == FINAL_Q1_ROWS
)

assert (
    result["positive_rows"]
    == FINAL_Q1_POSITIVE_ROWS
)

assert (
    result["total_failed_drives"]
    == FINAL_Q1_FAILED_DRIVES
)


print(
    "PASS: Final-test population preserved."
)


# ============================================================
# Ranking metrics
# ============================================================

assert abs(
    result["pr_auc"]
    - FINAL_Q1_PR_AUC
) < 1e-6

assert abs(
    result["roc_auc"]
    - FINAL_Q1_ROC_AUC
) < 1e-6


print(
    "PASS: Final ranking metrics preserved."
)


# ============================================================
# Operational metrics
# ============================================================

assert (
    result["detected_failed_drives"]
    == FINAL_Q1_DETECTED_FAILED_DRIVES
)

assert abs(
    result["drive_recall"]
    - FINAL_Q1_DRIVE_RECALL
) < 1e-6

assert (
    result["median_first_warning_days"]
    == FINAL_Q1_MEDIAN_LEAD_TIME_DAYS
)

assert (
    result["seven_day_warnings"]
    == FINAL_Q1_SEVEN_DAY_WARNINGS
)


print(
    "PASS: Final operational metrics preserved."
)


# ============================================================
# Confusion-matrix integrity
# ============================================================

matrix = result[
    "confusion_matrix"
]

assert (
    matrix["tn"]
    + matrix["fp"]
    + matrix["fn"]
    + matrix["tp"]
    == FINAL_Q1_ROWS
)

assert (
    matrix["tp"]
    + matrix["fn"]
    == FINAL_Q1_POSITIVE_ROWS
)


print(
    "PASS: Confusion matrix reconciles."
)


print(
    "\n============================================"
)
print(
    "FINAL TEST ARTIFACT CONTRACT PASSED"
)
print(
    "============================================"
)
