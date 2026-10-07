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
# Paths
# ============================================================

SCENARIO_DIR = PROJECT_ROOT / "evaluation" / "scenarios"
RESULTS_DIR = PROJECT_ROOT / "evaluation" / "results"

LOG_FILE = (
    SCENARIO_DIR / "labeled_openssh_scenarios.log"
)

MANIFEST_FILE = (
    SCENARIO_DIR / "scenario_manifest.csv"
)

WINDOW_RESULTS_FILE = (
    RESULTS_DIR / "labeled_window_predictions.csv"
)

OVERALL_METRICS_FILE = (
    RESULTS_DIR / "overall_metrics.csv"
)

SCENARIO_METRICS_FILE = (
    RESULTS_DIR / "scenario_family_metrics.csv"
)


# ============================================================
# Detector definitions
# ============================================================

DETECTOR_COLUMNS = {
    "RULE": "rule_anomalous",
    "ISOLATION_FOREST": "if_anomalous",
    "AUTOENCODER": "ae_anomalous",
    "HYBRID_SENSITIVE": "hybrid_sensitive",
    "HYBRID_CONSENSUS": "hybrid_consensus",
}


# ============================================================
# Utility
# ============================================================

def check_files():

    required = [
        LOG_FILE,
        MANIFEST_FILE,
    ]

    missing = [
        str(path)
        for path in required
        if not path.exists()
    ]

    if missing:
        raise FileNotFoundError(
            "Missing evaluation file(s): "
            + ", ".join(missing)
        )


def normalize_datetime_column(series):

    return pd.to_datetime(
        series,
        errors="raise"
    )


# ============================================================
# Parse + feature engineering
# ============================================================

def build_evaluation_features():

    print(
        "\n============================================"
    )
    print(
        "END-TO-END PARSING AND FEATURE ENGINEERING"
    )
    print(
        "============================================"
    )

    parsed = parse_log_file(
        LOG_FILE,
        year=2000
    )

    print(
        f"\nParsed evaluation events: "
        f"{len(parsed)}"
    )

    if parsed.empty:
        raise ValueError(
            "Evaluation parser produced no events."
        )

    events = prepare_events(
        parsed
    )

    features = build_basic_features(
        events
    )

    print(
        f"\nGenerated feature windows: "
        f"{len(features)}"
    )

    print(
        f"Feature source IPs: "
        f"{features['source_ip'].nunique()}"
    )

    return parsed, features


# ============================================================
# Load independent ground truth
# ============================================================

def load_manifest():

    manifest = pd.read_csv(
        MANIFEST_FILE
    )

    manifest["window_start"] = (
        normalize_datetime_column(
            manifest["window_start"]
        )
    )

    manifest["window_end"] = (
        normalize_datetime_column(
            manifest["window_end"]
        )
    )

    valid_labels = {
        "NORMAL",
        "ATTACK",
    }

    observed_labels = set(
        manifest["ground_truth"]
        .dropna()
        .unique()
    )

    if not observed_labels.issubset(
        valid_labels
    ):
        raise ValueError(
            "Unexpected ground-truth labels: "
            f"{observed_labels}"
        )

    return manifest


# ============================================================
# Strict scenario/window matching
# ============================================================

def match_features_to_manifest(
    manifest,
    features
):

    print(
        "\n============================================"
    )
    print(
        "GROUND-TRUTH MATCHING CHECK"
    )
    print(
        "============================================"
    )

    keys = [
        "source_ip",
        "window_start",
    ]

    if manifest.duplicated(
        keys
    ).any():
        raise ValueError(
            "Manifest contains duplicate "
            "source_ip/window_start keys."
        )

    if features.duplicated(
        keys
    ).any():
        raise ValueError(
            "Feature table contains duplicate "
            "source_ip/window_start keys."
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
        f"Manifest scenarios: "
        f"{len(manifest)}"
    )

    print(
        f"Feature windows:    "
        f"{len(features)}"
    )

    print(
        f"Matched windows:    "
        f"{len(matched)}"
    )

    print(
        f"Manifest only:      "
        f"{len(manifest_only)}"
    )

    print(
        f"Feature only:       "
        f"{len(feature_only)}"
    )

    if (
        len(manifest_only) > 0
        or len(feature_only) > 0
        or len(matched) != len(manifest)
    ):
        raise ValueError(
            "Evaluation scenario/window matching "
            "failed. Metrics will not be calculated."
        )

    if len(matched) != 330:
        print(
            "\nWARNING: Expected 330 scenarios "
            f"from the current generator, got "
            f"{len(matched)}."
        )

    print(
        "\nPASS: Every labeled scenario matched "
        "exactly one feature window."
    )

    # Resolve window_end after merge.
    if "window_end_feature" in matched.columns:
        matched["window_end"] = (
            matched["window_end_feature"]
        )
    elif "window_end" not in matched.columns:
        matched["window_end"] = (
            matched["window_end_manifest"]
        )

    matched = matched.drop(
        columns=["_merge"]
    )

    return matched


# ============================================================
# Frozen detector inference
# ============================================================

def run_detector(
    evaluation_df
):

    print(
        "\n============================================"
    )
    print(
        "FROZEN SSH DETECTOR INFERENCE"
    )
    print(
        "============================================"
    )

    detector = SSHAnomalyDetector()

    outputs = detector.detect(
        evaluation_df
    )

    if len(outputs) != len(
        evaluation_df
    ):
        raise ValueError(
            "Detector output count does not "
            "match evaluation window count."
        )

    rows = []

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

        rows.append(
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
                        rule[
                            "triggered_rules"
                        ]
                    ),

                "if_prediction":
                    isolation[
                        "prediction"
                    ],

                "if_anomalous":
                    bool(
                        isolation[
                            "anomalous"
                        ]
                    ),

                "if_anomaly_score":
                    float(
                        isolation[
                            "anomaly_score"
                        ]
                    ),

                "ae_prediction":
                    autoencoder[
                        "prediction"
                    ],

                "ae_anomalous":
                    bool(
                        autoencoder[
                            "anomalous"
                        ]
                    ),

                "ae_reconstruction_error":
                    float(
                        autoencoder[
                            "reconstruction_error"
                        ]
                    ),

                "ae_threshold":
                    float(
                        autoencoder[
                            "threshold"
                        ]
                    ),

                "detector_votes":
                    votes,

                "detector_combination":
                    output[
                        "detector_combination"
                    ],

                # Sensitive policy:
                # at least one strong anomaly vote.
                "hybrid_sensitive":
                    votes >= 1,

                # Consensus policy:
                # at least two independent votes.
                "hybrid_consensus":
                    votes >= 2,
            }
        )

    detector_df = pd.DataFrame(
        rows,
        index=evaluation_df.index
    )

    results = pd.concat(
        [
            evaluation_df.reset_index(
                drop=True
            ),
            detector_df.reset_index(
                drop=True
            ),
        ],
        axis=1,
    )

    print(
        f"Assessed windows: "
        f"{len(results)}"
    )

    return results


# ============================================================
# Binary metric calculation
# ============================================================

def calculate_metrics(
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

    cm = confusion_matrix(
        y_true,
        y_pred,
        labels=[0, 1],
    )

    tn, fp, fn, tp = (
        cm.ravel()
    )

    accuracy = accuracy_score(
        y_true,
        y_pred
    )

    precision = precision_score(
        y_true,
        y_pred,
        zero_division=0,
    )

    recall = recall_score(
        y_true,
        y_pred,
        zero_division=0,
    )

    f1 = f1_score(
        y_true,
        y_pred,
        zero_division=0,
    )

    fpr = (
        fp / (fp + tn)
        if (fp + tn) > 0
        else np.nan
    )

    fnr = (
        fn / (fn + tp)
        if (fn + tp) > 0
        else np.nan
    )

    specificity = (
        tn / (tn + fp)
        if (tn + fp) > 0
        else np.nan
    )

    return {
        "TN": int(tn),
        "FP": int(fp),
        "FN": int(fn),
        "TP": int(tp),
        "accuracy": float(
            accuracy
        ),
        "precision": float(
            precision
        ),
        "recall": float(
            recall
        ),
        "f1": float(
            f1
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


# ============================================================
# Overall detector metrics
# ============================================================

def calculate_overall_metrics(
    results
):

    y_true = (
        results["ground_truth"]
        .eq("ATTACK")
        .astype(int)
    )

    metric_rows = []

    for detector_name, column in (
        DETECTOR_COLUMNS.items()
    ):

        y_pred = (
            results[column]
            .astype(bool)
            .astype(int)
        )

        metrics = calculate_metrics(
            y_true,
            y_pred
        )

        metrics[
            "detector"
        ] = detector_name

        metric_rows.append(
            metrics
        )

    metrics_df = pd.DataFrame(
        metric_rows
    )

    column_order = [
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

    return metrics_df[
        column_order
    ]


# ============================================================
# Per-scenario-family analysis
# ============================================================

def calculate_scenario_family_metrics(
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

        ground_truth = (
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
                        ground_truth,

                    "detector":
                        detector_name,

                    "windows":
                        total,

                    "flagged":
                        flagged,

                    "flag_rate":
                        (
                            flagged
                            / total
                        ),
                }
            )

    return pd.DataFrame(
        rows
    )


# ============================================================
# Reporting
# ============================================================

def print_overall_metrics(
    metrics_df
):

    print(
        "\n============================================"
    )
    print(
        "OVERALL LABELED EVALUATION METRICS"
    )
    print(
        "============================================"
    )

    display = metrics_df.copy()

    percentage_columns = [
        "accuracy",
        "precision",
        "recall",
        "f1",
        "specificity",
        "false_positive_rate",
        "false_negative_rate",
    ]

    for column in percentage_columns:
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
        "CONFUSION MATRICES"
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


def print_scenario_detection(
    scenario_df
):

    print(
        "\n============================================"
    )
    print(
        "PER-SCENARIO-FAMILY FLAG RATES"
    )
    print(
        "============================================"
    )

    pivot = scenario_df.pivot(
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

    # --------------------------------------------------------
    # 1. Existing parser + existing feature engineering
    # --------------------------------------------------------

    parsed, features = (
        build_evaluation_features()
    )

    # --------------------------------------------------------
    # 2. Independent ground-truth manifest
    # --------------------------------------------------------

    manifest = load_manifest()

    # --------------------------------------------------------
    # 3. Strict one-to-one match
    # --------------------------------------------------------

    evaluation_df = (
        match_features_to_manifest(
            manifest,
            features
        )
    )

    # --------------------------------------------------------
    # 4. Frozen persisted detector inference
    # --------------------------------------------------------

    results = run_detector(
        evaluation_df
    )

    # --------------------------------------------------------
    # 5. Metrics
    # --------------------------------------------------------

    overall_metrics = (
        calculate_overall_metrics(
            results
        )
    )

    scenario_metrics = (
        calculate_scenario_family_metrics(
            results
        )
    )

    # --------------------------------------------------------
    # 6. Reports
    # --------------------------------------------------------

    print_overall_metrics(
        overall_metrics
    )

    print_confusion_matrices(
        overall_metrics
    )

    print_scenario_detection(
        scenario_metrics
    )

    # --------------------------------------------------------
    # 7. Save complete evaluation
    # --------------------------------------------------------

    results.to_csv(
        WINDOW_RESULTS_FILE,
        index=False
    )

    overall_metrics.to_csv(
        OVERALL_METRICS_FILE,
        index=False
    )

    scenario_metrics.to_csv(
        SCENARIO_METRICS_FILE,
        index=False
    )

    print(
        "\n============================================"
    )
    print(
        "LABELED EVALUATION COMPLETE"
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
        "\nNOTE: These metrics measure performance "
        "on the controlled labeled OpenSSH scenarios. "
        "They must not be presented as universal "
        "real-world attack-detection accuracy."
    )
