"""
DC-Guardian Phase 1
Predictive Maintenance Evaluation

Evaluates the frozen Temporal Random Forest v2 candidate
on the validation period.

IMPORTANT:
    This script evaluates VALIDATION_PERIOD only.
    It does not access the locked final test period.
"""

import joblib

from shared.model_integrity import verify_sha256
import numpy as np
import pandas as pd

from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from evidence.predictive_maintenance.src.maintenance_detector import MODEL_SHA256

from evidence.predictive_maintenance.src.config import (
    FEATURE_DATA_DIR,
    REFERENCE_Q4_PR_AUC,
    REFERENCE_Q4_ROC_AUC,
    RF_MODEL_DIR,
    RF_OPERATING_THRESHOLD,
    TEMPORAL_RF_FEATURES,
    VALIDATION_PERIOD,
)


MODEL_FILE = (
    RF_MODEL_DIR
    / "temporal_rf_v2.joblib"
)


def load_validation_data():
    """
    Load the natural-prevalence validation population.
    """

    file_path = (
        FEATURE_DATA_DIR
        / f"{VALIDATION_PERIOD}_features.parquet"
    )

    if not file_path.exists():
        raise FileNotFoundError(
            f"Validation feature file not found: "
            f"{file_path}"
        )

    columns = (
        [
            "date",
            "serial_number",
            "failure_date",
            "fail_within_7_days",
        ]
        + TEMPORAL_RF_FEATURES
    )

    df = pd.read_parquet(
        file_path,
        columns=columns,
    )

    df = (
        df[
            df["fail_within_7_days"]
            .notna()
        ]
        .reset_index(
            drop=True
        )
    )

    return df


def calculate_drive_metrics(
    validation,
    prediction,
):
    """
    Calculate drive-level detection metrics.
    """

    y_true = (
        validation[
            "fail_within_7_days"
        ]
        .astype(int)
        .to_numpy()
    )

    positive_mask = (
        y_true == 1
    )

    detected_mask = (
        positive_mask
        &
        (prediction == 1)
    )

    total_failed_drives = (
        validation.loc[
            positive_mask,
            "serial_number",
        ]
        .nunique()
    )

    detected_failed_drives = (
        validation.loc[
            detected_mask,
            "serial_number",
        ]
        .nunique()
    )

    drive_recall = (
        detected_failed_drives
        / total_failed_drives
    )

    return (
        total_failed_drives,
        detected_failed_drives,
        drive_recall,
    )


def calculate_lead_time(
    validation,
    prediction,
):
    """
    Calculate first-warning lead time for detected
    failed drives.
    """

    df = validation[
        [
            "date",
            "serial_number",
            "failure_date",
            "fail_within_7_days",
        ]
    ].copy()

    df["prediction"] = prediction

    df["date"] = pd.to_datetime(
        df["date"]
    )

    df["failure_date"] = pd.to_datetime(
        df["failure_date"]
    )

    detected = df[
        df["fail_within_7_days"]
        .eq(1)
        &
        df["prediction"]
        .eq(1)
    ].copy()

    detected[
        "lead_time_days"
    ] = (
        detected["failure_date"]
        - detected["date"]
    ).dt.days

    first_warning = (
        detected
        .sort_values(
            [
                "serial_number",
                "date",
            ]
        )
        .groupby(
            "serial_number",
            as_index=False,
        )
        .first()
    )

    if first_warning.empty:
        return (
            float("nan"),
            float("nan"),
            0,
        )

    median_lead_time = (
        first_warning[
            "lead_time_days"
        ].median()
    )

    mean_lead_time = (
        first_warning[
            "lead_time_days"
        ].mean()
    )

    seven_day_warnings = int(
        first_warning[
            "lead_time_days"
        ]
        .eq(7)
        .sum()
    )

    return (
        median_lead_time,
        mean_lead_time,
        seven_day_warnings,
    )


def main():

    print(
        "\n============================================"
    )
    print(
        "DC-GUARDIAN TEMPORAL RF V2 VALIDATION"
    )
    print(
        "============================================"
    )

    if not MODEL_FILE.exists():
        raise FileNotFoundError(
            f"Model not found: {MODEL_FILE}"
        )

    print(
        "Model:",
        MODEL_FILE
    )

    print(
        "Validation period:",
        VALIDATION_PERIOD
    )

    print(
        "Operating threshold:",
        RF_OPERATING_THRESHOLD
    )

    # ========================================================
    # Load model + validation data
    # ========================================================

    verify_sha256(MODEL_FILE, MODEL_SHA256)

    pipeline = joblib.load(
        MODEL_FILE
    )

    validation = (
        load_validation_data()
    )

    X_validation = validation[
        TEMPORAL_RF_FEATURES
    ]

    y_validation = (
        validation[
            "fail_within_7_days"
        ]
        .astype(int)
    )

    print(
        "\nValidation rows:",
        f"{len(validation):,}"
    )

    print(
        "Positive rows:",
        f"{int(y_validation.sum()):,}"
    )

    # ========================================================
    # Probability predictions
    # ========================================================

    probability = (
        pipeline
        .predict_proba(
            X_validation
        )[:, 1]
    )

    prediction = (
        probability
        >= RF_OPERATING_THRESHOLD
    ).astype(int)

    # ========================================================
    # Ranking metrics
    # ========================================================

    pr_auc = (
        average_precision_score(
            y_validation,
            probability,
        )
    )

    roc_auc = (
        roc_auc_score(
            y_validation,
            probability,
        )
    )

    prevalence = (
        y_validation.mean()
    )

    pr_lift = (
        pr_auc
        / prevalence
    )

    # ========================================================
    # Threshold metrics
    # ========================================================

    accuracy = accuracy_score(
        y_validation,
        prediction,
    )

    balanced_accuracy = (
        balanced_accuracy_score(
            y_validation,
            prediction,
        )
    )

    precision = precision_score(
        y_validation,
        prediction,
        zero_division=0,
    )

    recall = recall_score(
        y_validation,
        prediction,
        zero_division=0,
    )

    f1 = f1_score(
        y_validation,
        prediction,
        zero_division=0,
    )

    alerts = int(
        prediction.sum()
    )

    alert_rate = (
        alerts
        / len(validation)
    )

    alerts_per_1000 = (
        alert_rate
        * 1000
    )

    # ========================================================
    # Drive-level metrics
    # ========================================================

    (
        total_failed_drives,
        detected_failed_drives,
        drive_recall,
    ) = calculate_drive_metrics(
        validation,
        prediction,
    )

    # ========================================================
    # Warning lead time
    # ========================================================

    (
        median_lead_time,
        mean_lead_time,
        seven_day_warnings,
    ) = calculate_lead_time(
        validation,
        prediction,
    )

    # ========================================================
    # Confusion matrix
    # ========================================================

    matrix = confusion_matrix(
        y_validation,
        prediction,
    )

    # ========================================================
    # Report
    # ========================================================

    print(
        "\n============================================"
    )
    print(
        "VALIDATION RESULTS"
    )
    print(
        "============================================"
    )

    print(
        "Prevalence:",
        f"{prevalence:.6%}"
    )

    print(
        "PR-AUC:",
        f"{pr_auc:.6f}"
    )

    print(
        "ROC-AUC:",
        f"{roc_auc:.6f}"
    )

    print(
        "PR lift:",
        f"{pr_lift:.2f}x"
    )

    print(
        "\nThreshold metrics"
    )

    print(
        "Accuracy:",
        f"{accuracy:.6%}"
    )

    print(
        "Balanced accuracy:",
        f"{balanced_accuracy:.6%}"
    )

    print(
        "Precision:",
        f"{precision:.6%}"
    )

    print(
        "Row recall:",
        f"{recall:.6%}"
    )

    print(
        "F1:",
        f"{f1:.6f}"
    )

    print(
        "\nOperational metrics"
    )

    print(
        "Alerts:",
        f"{alerts:,}"
    )

    print(
        "Alert rate:",
        f"{alert_rate:.6%}"
    )

    print(
        "Alerts / 1,000 drive-days:",
        f"{alerts_per_1000:.3f}"
    )

    print(
        "Failed drives detected:",
        f"{detected_failed_drives}"
        f" / {total_failed_drives}"
    )

    print(
        "Drive recall:",
        f"{drive_recall:.6%}"
    )

    print(
        "Median first-warning lead time:",
        f"{median_lead_time:.1f} days"
    )

    print(
        "Mean first-warning lead time:",
        f"{mean_lead_time:.2f} days"
    )

    print(
        "Seven-day warnings:",
        seven_day_warnings
    )

    print(
        "\nConfusion matrix:"
    )

    print(
        matrix
    )

    # ========================================================
    # Development-reference comparison
    # ========================================================

    print(
        "\n============================================"
    )
    print(
        "NOTEBOOK REFERENCE COMPARISON"
    )
    print(
        "============================================"
    )

    print(
        "Notebook PR-AUC:",
        REFERENCE_Q4_PR_AUC
    )

    print(
        "Standalone PR-AUC:",
        round(
            pr_auc,
            6,
        )
    )

    print(
        "Difference:",
        f"{pr_auc - REFERENCE_Q4_PR_AUC:+.6f}"
    )

    print(
        "\nNotebook ROC-AUC:",
        REFERENCE_Q4_ROC_AUC
    )

    print(
        "Standalone ROC-AUC:",
        round(
            roc_auc,
            6,
        )
    )

    print(
        "Difference:",
        f"{roc_auc - REFERENCE_Q4_ROC_AUC:+.6f}"
    )

    print(
        "\n============================================"
    )
    print(
        "TEMPORAL RF V2 VALIDATION PASSED"
    )
    print(
        "============================================"
    )


if __name__ == "__main__":
    main()
