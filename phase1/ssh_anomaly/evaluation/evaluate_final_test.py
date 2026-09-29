from pathlib import Path
import sys

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
)

# ============================================================
# Project imports
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from parser import parse_log_file
from feature_engineering import prepare_events, build_basic_features
from ssh_detector import SSHAnomalyDetector


# ============================================================
# Locked Final Evaluation Set B paths
# ============================================================

FINAL_TEST_DIR = (
    PROJECT_ROOT / "evaluation" / "final_test"
)

RESULTS_DIR = (
    FINAL_TEST_DIR / "results"
)

LOG_FILE = (
    FINAL_TEST_DIR / "openssh_final_test.log"
)

MANIFEST_FILE = (
    FINAL_TEST_DIR / "final_test_manifest.csv"
)

WINDOW_RESULTS_FILE = (
    RESULTS_DIR / "final_test_window_predictions.csv"
)

OVERALL_METRICS_FILE = (
    RESULTS_DIR / "final_test_overall_metrics.csv"
)

SCENARIO_METRICS_FILE = (
    RESULTS_DIR / "final_test_scenario_family_metrics.csv"
)


# ============================================================
# Evaluated systems
# ============================================================

DETECTOR_COLUMNS = {
    "RULE": "rule_anomalous",
    "ISOLATION_FOREST": "if_anomalous",
    "AUTOENCODER": "ae_anomalous",
    "HYBRID_SENSITIVE": "hybrid_sensitive",
    "HYBRID_CONSENSUS": "hybrid_consensus",
    "OPERATIONAL_DETECTOR": "operational_detector",
}


# ============================================================
# File / label checks
# ============================================================

def check_files():

    missing = [
        str(path)
        for path in [LOG_FILE, MANIFEST_FILE]
        if not path.exists()
    ]

    if missing:
        raise FileNotFoundError(
            "Missing final-test file(s): "
            + ", ".join(missing)
        )


def load_manifest():

    manifest = pd.read_csv(
        MANIFEST_FILE
    )

    manifest["window_start"] = pd.to_datetime(
        manifest["window_start"],
        errors="raise"
    )

    manifest["window_end"] = pd.to_datetime(
        manifest["window_end"],
        errors="raise"
    )

    valid_labels = {"NORMAL", "ATTACK"}

    observed = set(
        manifest["ground_truth"]
        .dropna()
        .unique()
    )

    if not observed.issubset(valid_labels):
        raise ValueError(
            "Unexpected final-test labels: "
            f"{observed}"
        )

    return manifest


# ============================================================
# Existing parser + feature engineering
# ============================================================

def build_features():

    print(
        "\n============================================"
    )
    print(
        "FINAL TEST: PARSING + FEATURE ENGINEERING"
    )
    print(
        "============================================"
    )

    parsed = parse_log_file(
        LOG_FILE,
        year=2000
    )

    if parsed.empty:
        raise ValueError(
            "Final-test parser produced no events."
        )

    events = prepare_events(
        parsed
    )

    features = build_basic_features(
        events
    )

    print(
        f"\nParsed events:       {len(parsed)}"
    )

    print(
        f"Feature windows:     {len(features)}"
    )

    print(
        f"Unique source IPs:   "
        f"{features['source_ip'].nunique()}"
    )

    return features


# ============================================================
# Strict one-to-one integrity check
# ============================================================

def match_manifest_and_features(
    manifest,
    features
):

    print(
        "\n============================================"
    )
    print(
        "FINAL TEST INTEGRITY CHECK"
    )
    print(
        "============================================"
    )

    keys = [
        "source_ip",
        "window_start",
    ]

    if manifest.duplicated(keys).any():
        raise ValueError(
            "Final-test manifest contains "
            "duplicate source-IP/window keys."
        )

    if features.duplicated(keys).any():
        raise ValueError(
            "Final-test features contain "
            "duplicate source-IP/window keys."
        )

    merged = manifest.merge(
        features,
        on=keys,
        how="outer",
        indicator=True,
        suffixes=(
            "_manifest",
            "_feature",
        ),
        validate="one_to_one",
    )

    manifest_only = merged[
        merged["_merge"] == "left_only"
    ]

    feature_only = merged[
        merged["_merge"] == "right_only"
    ]

    matched = merged[
        merged["_merge"] == "both"
    ].copy()

    print(
        f"Manifest scenarios: {len(manifest)}"
    )

    print(
        f"Feature windows:    {len(features)}"
    )

    print(
        f"Matched windows:    {len(matched)}"
    )

    print(
        f"Manifest only:      {len(manifest_only)}"
    )

    print(
        f"Feature only:       {len(feature_only)}"
    )

    if (
        len(manifest) != 280
        or len(features) != 280
        or len(matched) != 280
        or not manifest_only.empty
        or not feature_only.empty
    ):
        raise ValueError(
            "Locked Final Set B integrity check "
            "failed. No metrics will be calculated."
        )

    print(
        "\nPASS: All 280 locked final-test scenarios "
        "matched exactly one feature window."
    )

    if "window_end_feature" in matched.columns:
        matched["window_end"] = (
            matched["window_end_feature"]
        )
    else:
        matched["window_end"] = (
            matched["window_end_manifest"]
        )

    return matched.drop(
        columns=["_merge"]
    )


# ============================================================
# Frozen detector inference
# ============================================================

def run_frozen_detector(
    evaluation_df
):

    print(
        "\n============================================"
    )
    print(
        "FROZEN OPERATIONAL DETECTOR INFERENCE"
    )
    print(
        "============================================"
    )

    detector = SSHAnomalyDetector()

    outputs = detector.detect(
        evaluation_df
    )

    if len(outputs) != len(evaluation_df):
        raise ValueError(
            "Detector output count mismatch."
        )

    prediction_rows = []

    for output in outputs:

        rule = output["rule"]
        isolation = output[
            "isolation_forest"
        ]
        autoencoder = output[
            "autoencoder"
        ]

        votes = int(
            output["detector_votes"]
        )

        explicit_signal = bool(
            output.get(
                "explicit_security_signal",
                False
            )
        )

        operational = bool(
            output["anomaly_detected"]
        )

        # Sanity check the revised operational policy.
        expected_operational = (
            votes >= 1
            or explicit_signal
        )

        if operational != expected_operational:
            raise ValueError(
                "Operational detector output does "
                "not match frozen policy."
            )

        prediction_rows.append(
            {
                "rule_prediction":
                    rule["prediction"],

                "rule_anomalous":
                    bool(
                        rule["anomalous"]
                    ),

                "rule_suspicious":
                    bool(
                        rule["suspicious"]
                    ),

                "rule_score":
                    int(
                        rule["score"]
                    ),

                "triggered_rules":
                    "; ".join(
                        rule["triggered_rules"]
                    ),

                "if_prediction":
                    isolation["prediction"],

                "if_anomalous":
                    bool(
                        isolation["anomalous"]
                    ),

                "if_anomaly_score":
                    float(
                        isolation["anomaly_score"]
                    ),

                "ae_prediction":
                    autoencoder["prediction"],

                "ae_anomalous":
                    bool(
                        autoencoder["anomalous"]
                    ),

                "ae_reconstruction_error":
                    float(
                        autoencoder[
                            "reconstruction_error"
                        ]
                    ),

                "ae_threshold":
                    float(
                        autoencoder["threshold"]
                    ),

                "detector_votes":
                    votes,

                "detector_combination":
                    output[
                        "detector_combination"
                    ],

                "explicit_security_signal":
                    explicit_signal,

                "security_signals":
                    "; ".join(
                        output.get(
                            "security_signals",
                            []
                        )
                    ),

                # Three-model policies, kept separate from
                # explicit OpenSSH security signals.
                "hybrid_sensitive":
                    votes >= 1,

                "hybrid_consensus":
                    votes >= 2,

                # Actual frozen operational component.
                "operational_detector":
                    operational,
            }
        )

    predictions = pd.DataFrame(
        prediction_rows
    )

    results = pd.concat(
        [
            evaluation_df.reset_index(
                drop=True
            ),
            predictions.reset_index(
                drop=True
            ),
        ],
        axis=1,
    )

    print(
        f"Assessed final-test windows: "
        f"{len(results)}"
    )

    print(
        f"Explicit security signals:   "
        f"{results['explicit_security_signal'].sum()}"
    )

    return results


# ============================================================
# Metrics
# ============================================================

def binary_metrics(
    y_true,
    y_pred
):

    y_true = np.asarray(
        y_true,
        dtype=int
    )

    y_pred = np.asarray(
        y_pred,
        dtype=int
    )

    tn, fp, fn, tp = (
        confusion_matrix(
            y_true,
            y_pred,
            labels=[0, 1],
        )
        .ravel()
    )

    fpr = (
        fp / (fp + tn)
        if (fp + tn)
        else np.nan
    )

    fnr = (
        fn / (fn + tp)
        if (fn + tp)
        else np.nan
    )

    specificity = (
        tn / (tn + fp)
        if (tn + fp)
        else np.nan
    )

    return {
        "TN": int(tn),
        "FP": int(fp),
        "FN": int(fn),
        "TP": int(tp),
        "accuracy": float(
            accuracy_score(
                y_true,
                y_pred
            )
        ),
        "precision": float(
            precision_score(
                y_true,
                y_pred,
                zero_division=0
            )
        ),
        "recall": float(
            recall_score(
                y_true,
                y_pred,
                zero_division=0
            )
        ),
        "f1": float(
            f1_score(
                y_true,
                y_pred,
                zero_division=0
            )
        ),
        "specificity": float(
            specificity
        ),
        "false_positive_rate": float(
            fpr
        ),
        "false_negative_rate": float(
            fnr
        ),
    }


def calculate_overall_metrics(
    results
):

    y_true = (
        results["ground_truth"]
        .eq("ATTACK")
        .astype(int)
    )

    rows = []

    for (
        detector_name,
        column
    ) in DETECTOR_COLUMNS.items():

        metrics = binary_metrics(
            y_true,
            results[column]
            .astype(bool)
            .astype(int)
        )

        metrics["detector"] = (
            detector_name
        )

        rows.append(metrics)

    df = pd.DataFrame(rows)

    return df[
        [
            "detector",
            "TN",
            "FP",
            "FN",
            "TP",
            "accuracy",
            "precision",
            "recall",
            "f1",
            "specificity",
            "false_positive_rate",
            "false_negative_rate",
        ]
    ]


# ============================================================
# Per-family flag rates
# ============================================================

def calculate_family_metrics(
    results
):

    rows = []

    for (
        scenario_type,
        group
    ) in results.groupby(
        "scenario_type",
        sort=True
    ):

        truth = (
            group["ground_truth"]
            .iloc[0]
        )

        for (
            detector_name,
            column
        ) in DETECTOR_COLUMNS.items():

            flagged = int(
                group[column]
                .astype(bool)
                .sum()
            )

            total = len(group)

            rows.append(
                {
                    "scenario_type":
                        scenario_type,
                    "ground_truth":
                        truth,
                    "detector":
                        detector_name,
                    "windows":
                        total,
                    "flagged":
                        flagged,
                    "flag_rate":
                        flagged / total,
                }
            )

    return pd.DataFrame(rows)


# ============================================================
# Reporting
# ============================================================

def print_metrics(
    metrics_df
):

    print(
        "\n============================================"
    )
    print(
        "FINAL CONTROLLED TEST METRICS"
    )
    print(
        "============================================"
    )

    display = metrics_df.copy()

    for column in [
        "accuracy",
        "precision",
        "recall",
        "f1",
        "specificity",
        "false_positive_rate",
        "false_negative_rate",
    ]:
        display[column] = (
            display[column]
            * 100
        ).round(2)

    print(
        display.to_string(
            index=False
        )
    )


def print_confusion_matrices(
    metrics_df
):

    print(
        "\n============================================"
    )
    print(
        "FINAL CONFUSION MATRICES"
    )
    print(
        "============================================"
    )

    for _, row in (
        metrics_df.iterrows()
    ):

        print(
            f"\n{row['detector']}"
        )

        print(
            "                  Pred NORMAL   "
            "Pred ATTACK"
        )

        print(
            f"True NORMAL       "
            f"{int(row['TN']):11d}   "
            f"{int(row['FP']):11d}"
        )

        print(
            f"True ATTACK       "
            f"{int(row['FN']):11d}   "
            f"{int(row['TP']):11d}"
        )


def print_family_rates(
    family_df
):

    print(
        "\n============================================"
    )
    print(
        "FINAL PER-SCENARIO-FAMILY FLAG RATES"
    )
    print(
        "============================================"
    )

    pivot = family_df.pivot(
        index=[
            "scenario_type",
            "ground_truth",
        ],
        columns="detector",
        values="flag_rate",
    )

    pivot = (
        pivot
        * 100
    ).round(2)

    print(
        pivot.to_string()
    )


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":

    check_files()

    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # 1. Independent locked labels.
    manifest = load_manifest()

    # 2. Existing parser + feature engineering.
    features = build_features()

    # 3. Require perfect one-to-one matching.
    evaluation_df = (
        match_manifest_and_features(
            manifest,
            features
        )
    )

    # 4. Frozen operational detector.
    results = run_frozen_detector(
        evaluation_df
    )

    # 5. Final metrics.
    overall_metrics = (
        calculate_overall_metrics(
            results
        )
    )

    family_metrics = (
        calculate_family_metrics(
            results
        )
    )

    # 6. Reports.
    print_metrics(
        overall_metrics
    )

    print_confusion_matrices(
        overall_metrics
    )

    print_family_rates(
        family_metrics
    )

    # 7. Save final-test artifacts separately.
    results.to_csv(
        WINDOW_RESULTS_FILE,
        index=False
    )

    overall_metrics.to_csv(
        OVERALL_METRICS_FILE,
        index=False
    )

    family_metrics.to_csv(
        SCENARIO_METRICS_FILE,
        index=False
    )

    print(
        "\n============================================"
    )
    print(
        "LOCKED FINAL EVALUATION COMPLETE"
    )
    print(
        "============================================"
    )

    print(
        f"\nWindow predictions: "
        f"{WINDOW_RESULTS_FILE}"
    )

    print(
        f"Overall metrics: "
        f"{OVERALL_METRICS_FILE}"
    )

    print(
        f"Scenario metrics: "
        f"{SCENARIO_METRICS_FILE}"
    )

    print(
        "\nThese are controlled Final Set B "
        "metrics for the frozen detector. "
        "They are not universal real-world "
        "SSH attack-detection accuracy."
    )
