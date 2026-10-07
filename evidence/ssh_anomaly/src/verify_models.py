from pathlib import Path
import json

import joblib
import numpy as np
import pandas as pd
import tensorflow as tf

from shared.model_integrity import verify_sha256
from evidence.ssh_anomaly.src.ssh_detector import ARTIFACT_SHA256


# ============================================================
# Paths
# ============================================================

MODEL_DIR = Path("models")
PROCESSED_DIR = Path("data/processed")

IF_MODEL_FILE = (
    MODEL_DIR / "isolation_forest.joblib"
)

IF_SCALER_FILE = (
    MODEL_DIR / "isolation_forest_scaler.joblib"
)

AE_MODEL_FILE = (
    MODEL_DIR / "autoencoder_log.keras"
)

AE_SCALER_FILE = (
    MODEL_DIR / "autoencoder_log_scaler.joblib"
)

AE_CONFIG_FILE = (
    MODEL_DIR / "autoencoder_log_config.json"
)

FEATURE_FILE = (
    PROCESSED_DIR / "ssh_features_full_5min.csv"
)


# ============================================================
# Isolation Forest feature order
# ============================================================
#
# This MUST match the feature order used during IF training.
# ============================================================

IF_FEATURES = [
    "failed_login_count",
    "invalid_user_count",
    "unique_users",
    "failure_ratio",
    "root_attempt_ratio",
    "breakin_warning_count",
    "disconnect_count",
    "no_identification_count"
]


# ============================================================
# Check required files
# ============================================================

def verify_files():

    required_files = [
        IF_MODEL_FILE,
        IF_SCALER_FILE,
        AE_MODEL_FILE,
        AE_SCALER_FILE,
        AE_CONFIG_FILE,
        FEATURE_FILE
    ]

    print(
        "\n============================================"
    )
    print(
        "FILE CHECK"
    )
    print(
        "============================================"
    )

    missing_files = []

    for file_path in required_files:

        if file_path.exists():

            print(
                f"PASS: {file_path}"
            )

        else:

            print(
                f"FAIL: {file_path}"
            )

            missing_files.append(
                file_path
            )

    if missing_files:

        raise FileNotFoundError(
            "Required model/data files are missing."
        )


# ============================================================
# Load Isolation Forest artifacts
# ============================================================

def load_isolation_forest():

    print(
        "\n============================================"
    )
    print(
        "LOADING ISOLATION FOREST"
    )
    print(
        "============================================"
    )

    verify_sha256(
        IF_MODEL_FILE,
        ARTIFACT_SHA256[IF_MODEL_FILE],
    )
    verify_sha256(
        IF_SCALER_FILE,
        ARTIFACT_SHA256[IF_SCALER_FILE],
    )

    model = joblib.load(
        IF_MODEL_FILE
    )

    scaler = joblib.load(
        IF_SCALER_FILE
    )

    print(
        f"Model type: "
        f"{type(model).__name__}"
    )

    print(
        f"Scaler type: "
        f"{type(scaler).__name__}"
    )

    print(
        f"Expected IF features: "
        f"{len(IF_FEATURES)}"
    )

    if hasattr(
        scaler,
        "n_features_in_"
    ):

        print(
            f"Scaler expects: "
            f"{scaler.n_features_in_} features"
        )

        if (
            scaler.n_features_in_
            != len(IF_FEATURES)
        ):

            raise ValueError(
                "Isolation Forest scaler feature "
                "count does not match IF_FEATURES."
            )

    if hasattr(
        model,
        "n_features_in_"
    ):

        print(
            f"Model expects: "
            f"{model.n_features_in_} features"
        )

        if (
            model.n_features_in_
            != len(IF_FEATURES)
        ):

            raise ValueError(
                "Isolation Forest model feature "
                "count does not match IF_FEATURES."
            )

    print(
        "PASS: Isolation Forest artifacts loaded."
    )

    return model, scaler


# ============================================================
# Load Autoencoder artifacts
# ============================================================

def load_autoencoder():

    print(
        "\n============================================"
    )
    print(
        "LOADING AUTOENCODER"
    )
    print(
        "============================================"
    )

    verify_sha256(
        AE_MODEL_FILE,
        ARTIFACT_SHA256[AE_MODEL_FILE],
    )
    verify_sha256(
        AE_SCALER_FILE,
        ARTIFACT_SHA256[AE_SCALER_FILE],
    )

    model = tf.keras.models.load_model(
        AE_MODEL_FILE
    )

    scaler = joblib.load(
        AE_SCALER_FILE
    )

    with open(
        AE_CONFIG_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        config = json.load(
            file
        )

    required_config_keys = [
        "threshold",
        "model_features",
        "count_features",
        "preprocessing",
        "threshold_method"
    ]

    for key in required_config_keys:

        if key not in config:

            raise KeyError(
                f"Missing Autoencoder config key: "
                f"{key}"
            )

    model_features = (
        config["model_features"]
    )

    count_features = (
        config["count_features"]
    )

    threshold = float(
        config["threshold"]
    )

    print(
        f"Model type: "
        f"{type(model).__name__}"
    )

    print(
        f"Scaler type: "
        f"{type(scaler).__name__}"
    )

    print(
        f"AE feature count: "
        f"{len(model_features)}"
    )

    print(
        f"AE features:"
    )

    for feature in model_features:

        print(
            f"  - {feature}"
        )

    print(
        "\nlog1p count features:"
    )

    for feature in count_features:

        print(
            f"  - {feature}"
        )

    print(
        f"\nPreprocessing: "
        f"{config['preprocessing']}"
    )

    print(
        f"Threshold method: "
        f"{config['threshold_method']}"
    )

    print(
        f"Saved threshold: "
        f"{threshold:.12f}"
    )

    if threshold <= 0:

        raise ValueError(
            "Autoencoder threshold must be positive."
        )

    if hasattr(
        scaler,
        "n_features_in_"
    ):

        if (
            scaler.n_features_in_
            != len(model_features)
        ):

            raise ValueError(
                "Autoencoder scaler feature "
                "count does not match config."
            )

    expected_input_dimension = (
        len(model_features)
    )

    actual_input_dimension = (
        model.input_shape[-1]
    )

    actual_output_dimension = (
        model.output_shape[-1]
    )

    print(
        f"Model input dimension: "
        f"{actual_input_dimension}"
    )

    print(
        f"Model output dimension: "
        f"{actual_output_dimension}"
    )

    if (
        actual_input_dimension
        != expected_input_dimension
    ):

        raise ValueError(
            "Autoencoder input dimension "
            "does not match config."
        )

    if (
        actual_output_dimension
        != expected_input_dimension
    ):

        raise ValueError(
            "Autoencoder output dimension "
            "does not match config."
        )

    print(
        "PASS: Autoencoder artifacts loaded."
    )

    return (
        model,
        scaler,
        config
    )


# ============================================================
# Load test feature rows
# ============================================================

def load_test_rows():

    print(
        "\n============================================"
    )
    print(
        "LOADING TEST FEATURE ROWS"
    )
    print(
        "============================================"
    )

    df = pd.read_csv(
        FEATURE_FILE,
        parse_dates=[
            "window_start",
            "window_end"
        ]
    )

    print(
        f"Available feature windows: "
        f"{len(df)}"
    )

    # --------------------------------------------------------
    # Use a small mixture of behavior for verification.
    #
    # First five:
    # highest failed-login counts.
    #
    # Next five:
    # lowest failed-login counts.
    #
    # This is NOT model evaluation.
    # It is only an inference smoke test.
    # --------------------------------------------------------

    high_activity = (
        df.sort_values(
            "failed_login_count",
            ascending=False
        )
        .head(5)
    )

    low_activity = (
        df.sort_values(
            "failed_login_count",
            ascending=True
        )
        .head(5)
    )

    test_rows = pd.concat(
        [
            high_activity,
            low_activity
        ],
        ignore_index=True
    )

    print(
        f"Verification rows selected: "
        f"{len(test_rows)}"
    )

    return test_rows


# ============================================================
# Validate required columns
# ============================================================

def validate_columns(
    df,
    ae_config
):

    required_features = set(
        IF_FEATURES
    )

    required_features.update(
        ae_config[
            "model_features"
        ]
    )

    missing_features = [
        feature
        for feature
        in required_features
        if feature not in df.columns
    ]

    if missing_features:

        raise ValueError(
            "Feature table is missing: "
            f"{missing_features}"
        )

    print(
        "\nPASS: All required model features exist."
    )


# ============================================================
# Isolation Forest inference
# ============================================================

def verify_isolation_inference(
    df,
    model,
    scaler
):

    print(
        "\n============================================"
    )
    print(
        "ISOLATION FOREST INFERENCE"
    )
    print(
        "============================================"
    )

    X = df[
        IF_FEATURES
    ].copy()

    if X.isna().any().any():

        raise ValueError(
            "Missing values found in IF input."
        )

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # transform(), NOT fit_transform().
    #
    # We are using the scaler learned during training.
    # --------------------------------------------------------

    X_scaled = scaler.transform(
        X
    )

    raw_predictions = model.predict(
        X_scaled
    )

    decision_scores = (
        model.decision_function(
            X_scaled
        )
    )

    predictions = np.where(
        raw_predictions == -1,
        "ANOMALOUS",
        "NORMAL"
    )

    anomaly_scores = (
        -decision_scores
    )

    results = pd.DataFrame(
        {
            "if_prediction":
                predictions,

            "if_anomaly_score":
                anomaly_scores
        }
    )

    print(
        results.to_string(
            index=False
        )
    )

    print(
        "\nPASS: Isolation Forest inference succeeded."
    )

    return results


# ============================================================
# Autoencoder preprocessing
# ============================================================

def prepare_autoencoder_input(
    df,
    scaler,
    config
):

    model_features = (
        config["model_features"]
    )

    count_features = (
        config["count_features"]
    )

    X = df[
        model_features
    ].copy()

    if X.isna().any().any():

        raise ValueError(
            "Missing values found in AE input."
        )

    # --------------------------------------------------------
    # Reproduce training preprocessing exactly:
    #
    # count features
    #       ↓
    # log1p
    #
    # ratio features
    #       ↓
    # unchanged
    #
    # all seven
    #       ↓
    # SAVED RobustScaler.transform()
    # --------------------------------------------------------

    for feature in count_features:

        if (
            X[feature] < 0
        ).any():

            raise ValueError(
                f"{feature} contains negative values."
            )

        X[feature] = np.log1p(
            X[feature]
        )

    X_scaled = scaler.transform(
        X
    )

    return X_scaled.astype(
        np.float32
    )


# ============================================================
# Autoencoder inference
# ============================================================

def verify_autoencoder_inference(
    df,
    model,
    scaler,
    config
):

    print(
        "\n============================================"
    )
    print(
        "AUTOENCODER INFERENCE"
    )
    print(
        "============================================"
    )

    X_scaled = (
        prepare_autoencoder_input(
            df,
            scaler,
            config
        )
    )

    reconstructed = model.predict(
        X_scaled,
        verbose=0
    )

    reconstruction_errors = np.mean(
        np.square(
            X_scaled
            - reconstructed
        ),
        axis=1
    )

    threshold = float(
        config["threshold"]
    )

    predictions = np.where(
        reconstruction_errors
        > threshold,
        "ANOMALOUS",
        "NORMAL"
    )

    results = pd.DataFrame(
        {
            "ae_prediction":
                predictions,

            "ae_reconstruction_error":
                reconstruction_errors
        }
    )

    print(
        results.to_string(
            index=False
        )
    )

    print(
        "\nPASS: Autoencoder inference succeeded."
    )

    return results


# ============================================================
# Combined verification table
# ============================================================

def print_combined_results(
    test_rows,
    if_results,
    ae_results
):

    print(
        "\n============================================"
    )
    print(
        "COMBINED INFERENCE CHECK"
    )
    print(
        "============================================"
    )

    base_columns = [
        "source_ip",
        "window_start",
        "failed_login_count",
        "invalid_user_count",
        "unique_users",
        "root_attempt_ratio",
        "breakin_warning_count",
        "disconnect_count",
        "no_identification_count"
    ]

    combined = pd.concat(
        [
            test_rows[
                base_columns
            ].reset_index(
                drop=True
            ),

            if_results.reset_index(
                drop=True
            ),

            ae_results.reset_index(
                drop=True
            )
        ],
        axis=1
    )

    print(
        combined.to_string(
            index=False
        )
    )


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":

    print(
        "\n============================================"
    )
    print(
        "DC-GUARDIAN SSH MODEL VERIFICATION"
    )
    print(
        "============================================"
    )

    # --------------------------------------------------------
    # 1. Check artifacts
    # --------------------------------------------------------

    verify_files()

    # --------------------------------------------------------
    # 2. Load persisted Isolation Forest
    # --------------------------------------------------------

    (
        if_model,
        if_scaler
    ) = load_isolation_forest()

    # --------------------------------------------------------
    # 3. Load persisted Autoencoder
    # --------------------------------------------------------

    (
        ae_model,
        ae_scaler,
        ae_config
    ) = load_autoencoder()

    # --------------------------------------------------------
    # 4. Load verification rows
    # --------------------------------------------------------

    test_rows = load_test_rows()

    # --------------------------------------------------------
    # 5. Validate feature schema
    # --------------------------------------------------------

    validate_columns(
        test_rows,
        ae_config
    )

    # --------------------------------------------------------
    # 6. Isolation Forest inference
    # --------------------------------------------------------

    if_results = (
        verify_isolation_inference(
            test_rows,
            if_model,
            if_scaler
        )
    )

    # --------------------------------------------------------
    # 7. Autoencoder inference
    # --------------------------------------------------------

    ae_results = (
        verify_autoencoder_inference(
            test_rows,
            ae_model,
            ae_scaler,
            ae_config
        )
    )

    # --------------------------------------------------------
    # 8. Combined results
    # --------------------------------------------------------

    print_combined_results(
        test_rows,
        if_results,
        ae_results
    )

    print(
        "\n============================================"
    )
    print(
        "MODEL PERSISTENCE VERIFICATION PASSED"
    )
    print(
        "============================================"
    )

    print(
        "\nBoth trained models were loaded from disk "
        "and performed inference successfully."
    )

    print(
        "No model or scaler was fitted or retrained "
        "during this verification."
    )