"""
DC-Guardian Evidence
Predictive Maintenance Final Holdout Evaluation

FINAL TEST:
    2026 Q1

The model, feature contract, sampling strategy, and operating
threshold were frozen before this script was created.

This script performs NO:
    - fitting
    - feature selection
    - hyperparameter tuning
    - threshold selection
    - model selection
"""

import json
from datetime import datetime, timezone

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
    FAILURE_HORIZON_DAYS,
    RF_MODEL_DIR,
    RF_OPERATING_THRESHOLD,
    TEMPORAL_RF_FEATURES,
    TEST_PERIOD,
)


MODEL_FILE = (
    RF_MODEL_DIR
    / "temporal_rf_v2.joblib"
)

RESULT_DIR = (
    FEATURE_DATA_DIR
    .parent
    / "results"
)

RESULT_FILE = (
    RESULT_DIR
    / "temporal_rf_v2_final_test.json"
)


# ============================================================
# Load final test population
# ============================================================

def load_final_test():

    if TEST_PERIOD != "2026_Q1":

        raise AssertionError(
            "Unexpected final-test period."
        )

    file_path = (
        FEATURE_DATA_DIR
        / f"{TEST_PERIOD}_features.parquet"
    )

    if not file_path.exists():

        raise FileNotFoundError(
            f"Final-test feature file not found: "
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

    # Predictive rows only:
    # removes failure-day/post-failure/censored observations.
    df = (
        df[
            df[
                "fail_within_7_days"
            ]
            .notna()
        ]
        .reset_index(
            drop=True
        )
    )

    df["date"] = pd.to_datetime(
        df["date"]
    )

    df["failure_date"] = pd.to_datetime(
        df["failure_date"]
    )

    return df


# ============================================================
# Drive-level detection
# ============================================================

def calculate_drive_metrics(
    test,
    prediction,
):

    y_true = (
        test[
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
        test.loc[
            positive_mask,
            "serial_number",
        ]
        .nunique()
    )

    detected_failed_drives = (
        test.loc[
            detected_mask,
            "serial_number",
        ]
        .nunique()
    )

    drive_recall = (
        detected_failed_drives
        / total_failed_drives
        if total_failed_drives
        else float("nan")
    )

    return (
        total_failed_drives,
        detected_failed_drives,
        drive_recall,
    )


# ============================================================
# Warning lead time
# ============================================================

def calculate_lead_time(
    test,
    prediction,
):

    df = test[
        [
            "date",
            "serial_number",
            "failure_date",
            "fail_within_7_days",
        ]
    ].copy()

    df["prediction"] = (
        prediction
    )

    detected = df[
        df[
            "fail_within_7_days"
        ].eq(1)
        &
        df[
            "prediction"
        ].eq(1)
    ].copy()

    detected[
        "lead_time_days"
    ] = (
        detected[
            "failure_date"
        ]
        -
        detected[
            "date"
        ]
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

        return {
            "median":
                float("nan"),

            "mean":
                float("nan"),

            "seven_day_warnings":
                0,

            "distribution":
                {},
        }

    distribution = (
        first_warning[
            "lead_time_days"
        ]
        .value_counts()
        .sort_index(
            ascending=False
        )
        .to_dict()
    )

    return {
        "median":
            float(
                first_warning[
                    "lead_time_days"
                ].median()
            ),

        "mean":
            float(
                first_warning[
                    "lead_time_days"
                ].mean()
            ),

        "seven_day_warnings":
            int(
                first_warning[
                    "lead_time_days"
                ]
                .eq(7)
                .sum()
            ),

        "distribution": {
            str(int(day)):
                int(count)

            for day, count
            in distribution.items()
        },
    }


# ============================================================
# Main
# ============================================================

def main():

    print(
        "\n============================================"
    )
    print(
        "DC-GUARDIAN PREDICTIVE MAINTENANCE"
    )
    print(
        "FINAL HOLDOUT TEST"
    )
    print(
        "============================================"
    )

    print(
        "Model:",
        MODEL_FILE
    )

    print(
        "Final test period:",
        TEST_PERIOD
    )

    print(
        "Operating threshold:",
        RF_OPERATING_THRESHOLD
    )

    print(
        "Failure horizon:",
        FAILURE_HORIZON_DAYS,
        "days"
    )

    print(
        "Features:",
        len(
            TEMPORAL_RF_FEATURES
        )
    )

    print(
        "\nIMPORTANT:"
    )

    print(
        "Model configuration is frozen."
    )

    print(
        "No fitting or threshold selection "
        "will occur."
    )


    # ========================================================
    # Load frozen model
    # ========================================================

    if not MODEL_FILE.exists():

        raise FileNotFoundError(
            f"Frozen model not found: "
            f"{MODEL_FILE}"
        )

    verify_sha256(MODEL_FILE, MODEL_SHA256)

    pipeline = joblib.load(
        MODEL_FILE
    )


    # ========================================================
    # Load untouched Q1
    # ========================================================

    print(
        "\nLoading final holdout..."
    )

    test = load_final_test()


    X_test = test[
        TEMPORAL_RF_FEATURES
    ]

    y_test = (
        test[
            "fail_within_7_days"
        ]
        .astype(int)
    )


    print(
        "Predictive rows:",
        f"{len(test):,}"
    )

    print(
        "Positive rows:",
        f"{int(y_test.sum()):,}"
    )

    print(
        "Failed drives:",
        f"{test.loc[y_test.eq(1), 'serial_number'].nunique():,}"
    )


    # ========================================================
    # Frozen-model inference
    # ========================================================

    print(
        "\nScoring frozen model..."
    )

    probability = (
        pipeline
        .predict_proba(
            X_test
        )[:, 1]
    )

    prediction = (
        probability
        >= RF_OPERATING_THRESHOLD
    ).astype(int)


    # ========================================================
    # Natural-prevalence ranking metrics
    # ========================================================

    prevalence = float(
        y_test.mean()
    )

    pr_auc = float(
        average_precision_score(
            y_test,
            probability,
        )
    )

    roc_auc = float(
        roc_auc_score(
            y_test,
            probability,
        )
    )

    pr_lift = (
        pr_auc
        / prevalence
    )


    # ========================================================
    # Frozen-threshold metrics
    # ========================================================

    accuracy = float(
        accuracy_score(
            y_test,
            prediction,
        )
    )

    balanced_accuracy = float(
        balanced_accuracy_score(
            y_test,
            prediction,
        )
    )

    precision = float(
        precision_score(
            y_test,
            prediction,
            zero_division=0,
        )
    )

    row_recall = float(
        recall_score(
            y_test,
            prediction,
            zero_division=0,
        )
    )

    f1 = float(
        f1_score(
            y_test,
            prediction,
            zero_division=0,
        )
    )


    # ========================================================
    # Alert burden
    # ========================================================

    alerts = int(
        prediction.sum()
    )

    alert_rate = (
        alerts
        / len(test)
    )

    alerts_per_1000 = (
        alert_rate
        * 1000
    )


    # ========================================================
    # Drive metrics
    # ========================================================

    (
        total_failed_drives,
        detected_failed_drives,
        drive_recall,
    ) = calculate_drive_metrics(
        test,
        prediction,
    )


    # ========================================================
    # Lead time
    # ========================================================

    lead_time = calculate_lead_time(
        test,
        prediction,
    )


    # ========================================================
    # Confusion matrix
    # ========================================================

    matrix = confusion_matrix(
        y_test,
        prediction,
    )


    tn, fp, fn, tp = (
        matrix.ravel()
    )


    # ========================================================
    # FINAL RESULTS
    # ========================================================

    print(
        "\n============================================"
    )
    print(
        "FINAL TEST RESULTS â€” 2026 Q1"
    )
    print(
        "============================================"
    )


    print(
        "Natural prevalence:",
        f"{prevalence:.6%}"
    )

    print(
        "\nRanking metrics"
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
        "\nFrozen threshold:",
        RF_OPERATING_THRESHOLD
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
        f"{row_recall:.6%}"
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
        "\nWarning lead time"
    )

    print(
        "Median:",
        f"{lead_time['median']:.1f} days"
    )

    print(
        "Mean:",
        f"{lead_time['mean']:.2f} days"
    )

    print(
        "Seven-day warnings:",
        lead_time[
            "seven_day_warnings"
        ]
    )

    print(
        "Distribution:",
        lead_time[
            "distribution"
        ]
    )


    print(
        "\nConfusion matrix"
    )

    print(
        matrix
    )


    # ========================================================
    # Save immutable final-test result
    # ========================================================

    RESULT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


    result = {
        "result_type":
            "FINAL_HOLDOUT_TEST",

        "created_utc":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "model":
            "DC_Guardian_Temporal_RF_v2",

        "test_period":
            TEST_PERIOD,

        "failure_horizon_days":
            FAILURE_HORIZON_DAYS,

        "feature_count":
            len(
                TEMPORAL_RF_FEATURES
            ),

        "operating_threshold":
            RF_OPERATING_THRESHOLD,

        "model_refit_on_test":
            False,

        "threshold_selected_on_test":
            False,

        "test_rows":
            len(test),

        "positive_rows":
            int(
                y_test.sum()
            ),

        "prevalence":
            prevalence,

        "pr_auc":
            pr_auc,

        "roc_auc":
            roc_auc,

        "pr_lift":
            pr_lift,

        "accuracy":
            accuracy,

        "balanced_accuracy":
            balanced_accuracy,

        "precision":
            precision,

        "row_recall":
            row_recall,

        "f1":
            f1,

        "alerts":
            alerts,

        "alert_rate":
            alert_rate,

        "alerts_per_1000_drive_days":
            alerts_per_1000,

        "total_failed_drives":
            int(
                total_failed_drives
            ),

        "detected_failed_drives":
            int(
                detected_failed_drives
            ),

        "drive_recall":
            float(
                drive_recall
            ),

        "median_first_warning_days":
            lead_time[
                "median"
            ],

        "mean_first_warning_days":
            lead_time[
                "mean"
            ],

        "seven_day_warnings":
            lead_time[
                "seven_day_warnings"
            ],

        "lead_time_distribution":
            lead_time[
                "distribution"
            ],

        "confusion_matrix": {
            "tn":
                int(tn),

            "fp":
                int(fp),

            "fn":
                int(fn),

            "tp":
                int(tp),
        },
    }


    with open(
        RESULT_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            result,
            file,
            indent=2,
        )


    print(
        "\nFinal result saved:"
    )

    print(
        RESULT_FILE
    )


    print(
        "\n============================================"
    )
    print(
        "FINAL HOLDOUT EVALUATION COMPLETE"
    )
    print(
        "============================================"
    )


if __name__ == "__main__":
    main()
