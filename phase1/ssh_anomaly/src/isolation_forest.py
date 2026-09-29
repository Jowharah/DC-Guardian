from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import RobustScaler

import joblib

# ============================================================
# Paths
# ============================================================

PROCESSED_DIR = Path("data/processed")

# 2k development sample
SAMPLE_FEATURE_FILE = (
    PROCESSED_DIR / "ssh_features_2k_5min.csv"
)

SAMPLE_RAW_OUTPUT = (
    PROCESSED_DIR / "ssh_isolation_forest_raw_results_2k.csv"
)

SAMPLE_LOG_OUTPUT = (
    PROCESSED_DIR / "ssh_isolation_forest_log_results_2k.csv"
)

# Full OpenSSH dataset
FULL_FEATURE_FILE = (
    PROCESSED_DIR / "ssh_features_full_5min.csv"
)

FULL_RAW_OUTPUT = (
    PROCESSED_DIR / "ssh_isolation_forest_raw_results_full.csv"
)

FULL_LOG_OUTPUT = (
    PROCESSED_DIR / "ssh_isolation_forest_log_results_full.csv"
)

MODEL_DIR = Path("models")

IF_MODEL_FILE = (
    MODEL_DIR / "isolation_forest.joblib"
)

IF_SCALER_FILE = (
    MODEL_DIR / "isolation_forest_scaler.joblib"
)

# ============================================================
# Full-data Model v1 features
# ============================================================
#
# Selected after re-running variance/correlation analysis on
# the full 8,256-window dataset.
#
# Excluded:
#   attempt_rate       -> redundant with failed-login volume
#   root_attempt_count -> strongly correlated with failures
#
# successful_login_count and success_after_failures remain in
# the feature CSV as evidence/context, but are not included in
# this first full-data unsupervised model.

MODEL_FEATURES = [
    "failed_login_count",
    "invalid_user_count",
    "unique_users",
    "failure_ratio",
    "root_attempt_ratio",
    "breakin_warning_count",
    "disconnect_count",
    "no_identification_count"
]


# Count features used only in the log1p preprocessing experiment.
COUNT_FEATURES = [
    "failed_login_count",
    "invalid_user_count",
    "unique_users",
    "breakin_warning_count",
    "disconnect_count",
    "no_identification_count"
]


# ============================================================
# Load feature data
# ============================================================

def load_features(file_path):

    df = pd.read_csv(
        file_path,
        parse_dates=[
            "window_start",
            "window_end"
        ]
    )

    print(
        f"Total source-IP windows: {len(df)}"
    )

    print("\nModel features:")

    print(
        df[MODEL_FEATURES]
        .describe()
        .T
        .to_string()
    )

    return df


# ============================================================
# Prepare raw model input
# ============================================================

def prepare_model_input(df):

    X = df[
        MODEL_FEATURES
    ].copy()

    if X.isna().any().any():

        print(
            "\nWARNING: Missing values found:"
        )

        print(
            X.isna().sum()
        )

        raise ValueError(
            "Model features contain missing values."
        )

    return X


# ============================================================
# Prepare log-transformed model input
# ============================================================

def prepare_log_model_input(df):

    X = df[
        MODEL_FEATURES
    ].copy()

    for feature in COUNT_FEATURES:

        if (X[feature] < 0).any():

            raise ValueError(
                f"{feature} contains negative values; "
                "log1p is not appropriate."
            )

        X[feature] = np.log1p(
            X[feature]
        )

    # failure_ratio and root_attempt_ratio are bounded ratios
    # and are intentionally not log-transformed.

    if X.isna().any().any():

        raise ValueError(
            "Log-transformed model features "
            "contain missing values."
        )

    return X


# ============================================================
# Scale features
# ============================================================

def scale_features(X):

    scaler = RobustScaler()

    X_scaled = scaler.fit_transform(
        X
    )

    return X_scaled, scaler


# ============================================================
# Train Isolation Forest
# ============================================================

def train_isolation_forest(
    X_scaled,
    contamination=0.15
):

    model = IsolationForest(
        contamination=contamination,
        random_state=42,
        n_estimators=200,
        n_jobs=-1
    )

    model.fit(
        X_scaled
    )

    return model


# ============================================================
# Generate predictions
# ============================================================

def generate_predictions(
    model,
    X_scaled
):

    raw_predictions = model.predict(
        X_scaled
    )

    decision_scores = model.decision_function(
        X_scaled
    )

    predictions = np.where(
        raw_predictions == -1,
        "ANOMALOUS",
        "NORMAL"
    )

    return (
        predictions,
        decision_scores
    )


# ============================================================
# Run one experiment
# ============================================================

def run_experiment(
    df,
    X,
    experiment_name,
    contamination=0.15
):

    print(
        f"\n{'=' * 60}"
        f"\n{experiment_name}"
        f"\n{'=' * 60}"
    )

    X_scaled, scaler = scale_features(
        X
    )

    model = train_isolation_forest(
        X_scaled,
        contamination=contamination
    )

    predictions, decision_scores = (
        generate_predictions(
            model,
            X_scaled
        )
    )

    results = df.copy()

    results["if_prediction"] = predictions
    results["if_decision_score"] = decision_scores

    # Higher score = more anomalous.
    # This is not a probability.
    results["if_anomaly_score"] = (
        -decision_scores
    )

    print("\nPredictions:")

    prediction_counts = (
        results["if_prediction"]
        .value_counts()
    )

    print(
        prediction_counts
    )

    print("\nPrediction percentages:")

    print(
        (
            prediction_counts
            / len(results)
            * 100
        )
        .round(2)
    )

    print("\nMost anomalous windows:")

    ranked = (
        results
        .sort_values(
            "if_anomaly_score",
            ascending=False
        )
    )

    print(
        ranked[
            [
                "source_ip",
                "window_start",
                "failed_login_count",
                "invalid_user_count",
                "unique_users",
                "failure_ratio",
                "root_attempt_ratio",
                "breakin_warning_count",
                "disconnect_count",
                "no_identification_count",
                "if_prediction",
                "if_anomaly_score"
            ]
        ]
        .head(25)
        .to_string(index=False)
    )

    return results


# ============================================================
# Contamination sensitivity
# ============================================================

def test_contamination_sensitivity(X):

    contamination_values = [
        0.05,
        0.10,
        0.15,
        0.20
    ]

    print(
        "\n============================================"
    )
    print(
        "CONTAMINATION SENSITIVITY"
    )
    print(
        "============================================"
    )

    X_scaled, _ = scale_features(
        X
    )

    for contamination in contamination_values:

        model = train_isolation_forest(
            X_scaled,
            contamination=contamination
        )

        predictions, _ = (
            generate_predictions(
                model,
                X_scaled
            )
        )

        anomaly_count = (
            predictions == "ANOMALOUS"
        ).sum()

        normal_count = (
            predictions == "NORMAL"
        ).sum()

        print(
            f"\nContamination = {contamination:.2f}"
        )

        print(
            f"  NORMAL:     {normal_count}"
        )

        print(
            f"  ANOMALOUS:  {anomaly_count} "
            f"({anomaly_count / len(X) * 100:.2f}%)"
        )


# ============================================================
# Compare raw vs log1p preprocessing
# ============================================================

def compare_preprocessing(
    df,
    results_raw,
    results_log
):

    comparison = pd.DataFrame(
        {
            "source_ip":
                df["source_ip"],

            "window_start":
                df["window_start"],

            "failed_login_count":
                df["failed_login_count"],

            "invalid_user_count":
                df["invalid_user_count"],

            "unique_users":
                df["unique_users"],

            "root_attempt_ratio":
                df["root_attempt_ratio"],

            "raw_prediction":
                results_raw["if_prediction"],

            "raw_score":
                results_raw["if_anomaly_score"],

            "log_prediction":
                results_log["if_prediction"],

            "log_score":
                results_log["if_anomaly_score"]
        }
    )

    comparison["same_prediction"] = (
        comparison["raw_prediction"]
        ==
        comparison["log_prediction"]
    )

    print(
        "\n============================================"
    )
    print(
        "PREPROCESSING COMPARISON"
    )
    print(
        "============================================"
    )

    agreement_counts = (
        comparison["same_prediction"]
        .value_counts()
    )

    print("\nPrediction agreement:")

    print(
        agreement_counts
    )

    changed = comparison[
        comparison["same_prediction"] == False
    ]

    print(
        f"\nChanged predictions: "
        f"{len(changed)} / {len(comparison)} "
        f"({len(changed) / len(comparison) * 100:.2f}%)"
    )

    print(
        "\nTop changed windows by raw anomaly score:"
    )

    if changed.empty:

        print(
            "No predictions changed."
        )

    else:

        print(
            changed
            .sort_values(
                "raw_score",
                ascending=False
            )[
                [
                    "source_ip",
                    "window_start",
                    "failed_login_count",
                    "invalid_user_count",
                    "unique_users",
                    "root_attempt_ratio",
                    "raw_prediction",
                    "raw_score",
                    "log_prediction",
                    "log_score"
                ]
            ]
            .head(25)
            .to_string(index=False)
        )


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":

    MODEL_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # ========================================================
    # Select dataset
    # ========================================================
    #
    # "sample" -> 2k development feature table
    # "full"   -> full 8,256-window feature table

    DATASET = "full"

    if DATASET == "sample":

        feature_file = SAMPLE_FEATURE_FILE
        raw_output_file = SAMPLE_RAW_OUTPUT
        log_output_file = SAMPLE_LOG_OUTPUT

    elif DATASET == "full":

        feature_file = FULL_FEATURE_FILE
        raw_output_file = FULL_RAW_OUTPUT
        log_output_file = FULL_LOG_OUTPUT

    else:

        raise ValueError(
            "DATASET must be 'sample' or 'full'."
        )

    if not feature_file.exists():

        raise FileNotFoundError(
            f"Feature file not found: {feature_file}"
        )

    print(f"Dataset: {DATASET}")
    print(f"Input:   {feature_file}")

    # ========================================================
    # Load data
    # ========================================================

    df = load_features(
        feature_file
    )

    # ========================================================
    # Raw-feature experiment
    # ========================================================

    X_raw = prepare_model_input(
        df
    )

    print(
        f"\nRaw model input shape: "
        f"{X_raw.shape}"
    )

    # ========================================================
    # Contamination sensitivity
    # ========================================================

    test_contamination_sensitivity(
        X_raw
    )

    # ========================================================
    # Experiment A: raw features
    # ========================================================

    results_raw = run_experiment(
        df,
        X_raw,
        "EXPERIMENT A: Raw Features + RobustScaler",
        contamination=0.15
    )

    # ========================================================
    # Experiment B: log1p count features
    # ========================================================

    X_log = prepare_log_model_input(
        df
    )

    print(
        f"\nLog-transformed input shape: "
        f"{X_log.shape}"
    )

    results_log = run_experiment(
        df,
        X_log,
        "EXPERIMENT B: log1p Counts + RobustScaler",
        contamination=0.15
    )

    # ========================================================
    # Compare preprocessing
    # ========================================================

    compare_preprocessing(
        df,
        results_raw,
        results_log
    )

    # ========================================================
    # Save complete results
    # ========================================================

    results_raw.to_csv(
        raw_output_file,
        index=False
    )

    results_log.to_csv(
        log_output_file,
        index=False
    )

    print(
        f"\nSaved Experiment A to: "
        f"{raw_output_file}"
    )

    print(
        f"Saved Experiment B to: "
        f"{log_output_file}"
    )
