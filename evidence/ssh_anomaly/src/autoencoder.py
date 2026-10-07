from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.model_selection import GroupShuffleSplit
from sklearn.preprocessing import RobustScaler

import tensorflow as tf

from tensorflow.keras.models import Model
from tensorflow.keras.layers import Input, Dense
from tensorflow.keras.callbacks import EarlyStopping


# ============================================================
# Reproducibility
# ============================================================

RANDOM_STATE = 42

np.random.seed(
    RANDOM_STATE
)

tf.random.set_seed(
    RANDOM_STATE
)


# ============================================================
# Paths
# ============================================================

PROCESSED_DIR = Path(
    "data/processed"
)

COMPARISON_FILE = (
    PROCESSED_DIR
    / "ssh_model_comparison_full.csv"
)

TRAIN_OUTPUT = (
    PROCESSED_DIR
    / "ssh_autoencoder_train.csv"
)

VALIDATION_OUTPUT = (
    PROCESSED_DIR
    / "ssh_autoencoder_validation.csv"
)

TEST_OUTPUT = (
    PROCESSED_DIR
    / "ssh_autoencoder_test_normal.csv"
)

RESULTS_OUTPUT = (
    PROCESSED_DIR
    / "ssh_autoencoder_results_full.csv"
)

MODEL_OUTPUT = (
    PROCESSED_DIR
    / "ssh_autoencoder.keras"
)


# ============================================================
# Model features
# ============================================================
#
# breakin_warning_count is intentionally excluded from
# Autoencoder v1 because it had zero variance in the
# normal-reference training subset.

MODEL_FEATURES = [
    "failed_login_count",
    "invalid_user_count",
    "unique_users",
    "failure_ratio",
    "root_attempt_ratio",
    "disconnect_count",
    "no_identification_count"
]


# ============================================================
# Autoencoder configuration
# ============================================================

EPOCHS = 100

BATCH_SIZE = 32

LEARNING_RATE = 0.001

PATIENCE = 10


# ============================================================
# Load comparison data
# ============================================================

def load_data(file_path):

    df = pd.read_csv(
        file_path,
        parse_dates=[
            "window_start",
            "window_end"
        ]
    )

    print(
        f"Total comparison windows: "
        f"{len(df)}"
    )

    print(
        f"Total source IPs: "
        f"{df['source_ip'].nunique()}"
    )

    return df


# ============================================================
# Select normal-reference pool
# ============================================================

def select_normal_reference(df):

    normal_reference = df[
        df["agreement"]
        == "BOTH_NORMAL"
    ].copy()

    print(
        "\n============================================"
    )

    print(
        "NORMAL-REFERENCE POOL"
    )

    print(
        "============================================"
    )

    print(
        f"Reference-normal windows: "
        f"{len(normal_reference)}"
    )

    print(
        f"Reference-normal source IPs: "
        f"{normal_reference['source_ip'].nunique()}"
    )

    return normal_reference


# ============================================================
# Split normal-reference data by source IP
# ============================================================

def split_by_source_ip(
    normal_reference,
    random_state=RANDOM_STATE
):

    # --------------------------------------------------------
    # First split:
    #
    # ~70% train
    # ~30% temporary
    #
    # Groups are source IPs, not individual rows.
    # --------------------------------------------------------

    first_split = GroupShuffleSplit(
        n_splits=1,
        train_size=0.70,
        random_state=random_state
    )

    train_indices, temp_indices = next(
        first_split.split(
            normal_reference,
            groups=normal_reference[
                "source_ip"
            ]
        )
    )

    train_df = (
        normal_reference
        .iloc[train_indices]
        .copy()
    )

    temp_df = (
        normal_reference
        .iloc[temp_indices]
        .copy()
    )


    # --------------------------------------------------------
    # Second split:
    #
    # Temporary data is divided approximately equally into:
    #
    # validation ~15%
    # test       ~15%
    # --------------------------------------------------------

    second_split = GroupShuffleSplit(
        n_splits=1,
        train_size=0.50,
        random_state=random_state
    )

    validation_indices, test_indices = next(
        second_split.split(
            temp_df,
            groups=temp_df[
                "source_ip"
            ]
        )
    )

    validation_df = (
        temp_df
        .iloc[validation_indices]
        .copy()
    )

    test_df = (
        temp_df
        .iloc[test_indices]
        .copy()
    )

    return (
        train_df,
        validation_df,
        test_df
    )


# ============================================================
# Verify source-IP isolation
# ============================================================

def verify_no_ip_leakage(
    train_df,
    validation_df,
    test_df
):

    train_ips = set(
        train_df["source_ip"]
    )

    validation_ips = set(
        validation_df["source_ip"]
    )

    test_ips = set(
        test_df["source_ip"]
    )

    train_validation_overlap = (
        train_ips
        & validation_ips
    )

    train_test_overlap = (
        train_ips
        & test_ips
    )

    validation_test_overlap = (
        validation_ips
        & test_ips
    )


    print(
        "\n============================================"
    )

    print(
        "SOURCE-IP LEAKAGE CHECK"
    )

    print(
        "============================================"
    )

    print(
        "Train / validation overlap:",
        len(train_validation_overlap)
    )

    print(
        "Train / test overlap:",
        len(train_test_overlap)
    )

    print(
        "Validation / test overlap:",
        len(validation_test_overlap)
    )


    if (
        train_validation_overlap
        or train_test_overlap
        or validation_test_overlap
    ):

        raise ValueError(
            "Source-IP leakage detected."
        )


    print(
        "\nPASS: No source IP appears "
        "in more than one split."
    )


# ============================================================
# Display split statistics
# ============================================================

def print_split_statistics(
    train_df,
    validation_df,
    test_df
):

    total = (
        len(train_df)
        + len(validation_df)
        + len(test_df)
    )

    print(
        "\n============================================"
    )

    print(
        "AUTOENCODER DATASET SPLITS"
    )

    print(
        "============================================"
    )


    datasets = {
        "TRAIN": train_df,
        "VALIDATION": validation_df,
        "TEST": test_df
    }


    for name, dataset in datasets.items():

        percentage = (
            len(dataset)
            / total
            * 100
        )

        print(
            f"\n{name}"
        )

        print(
            f"  Windows: "
            f"{len(dataset)} "
            f"({percentage:.2f}%)"
        )

        print(
            f"  Source IPs: "
            f"{dataset['source_ip'].nunique()}"
        )


# ============================================================
# Validate model features
# ============================================================

def validate_features(
    train_df,
    validation_df,
    test_df
):

    print(
        "\n============================================"
    )

    print(
        "FEATURE VALIDATION"
    )

    print(
        "============================================"
    )


    for name, dataset in [
        ("TRAIN", train_df),
        ("VALIDATION", validation_df),
        ("TEST", test_df)
    ]:

        X = dataset[
            MODEL_FEATURES
        ]

        missing_values = (
            X.isna()
            .sum()
            .sum()
        )

        print(
            f"{name}: "
            f"missing values = "
            f"{missing_values}"
        )

        if missing_values > 0:

            raise ValueError(
                f"{name} contains "
                f"missing feature values."
            )


# ============================================================
# Check training feature variance
# ============================================================

def check_training_variance(
    train_df
):

    print(
        "\n============================================"
    )

    print(
        "TRAINING FEATURE VARIANCE CHECK"
    )

    print(
        "============================================"
    )


    zero_variance_features = []


    for feature in MODEL_FEATURES:

        unique_values = (
            train_df[feature]
            .nunique()
        )

        print(
            f"{feature:<30} "
            f"unique values = "
            f"{unique_values}"
        )

        if unique_values <= 1:

            zero_variance_features.append(
                feature
            )


    if zero_variance_features:

        raise ValueError(
            "Zero-variance training features "
            f"detected: {zero_variance_features}"
        )


    print(
        "\nPASS: All model features "
        "vary in training data."
    )


# ============================================================
# Fit preprocessing on TRAINING DATA ONLY
# ============================================================

def fit_scaler(
    train_df
):

    X_train = train_df[
        MODEL_FEATURES
    ].copy()

    scaler = RobustScaler()

    scaler.fit(
        X_train
    )

    return scaler


# ============================================================
# Transform features
# ============================================================

def transform_features(
    dataset,
    scaler
):

    X = dataset[
        MODEL_FEATURES
    ].copy()

    X_scaled = scaler.transform(
        X
    )

    return X_scaled.astype(
        np.float32
    )


# ============================================================
# Build Dense Autoencoder
# ============================================================

def build_autoencoder(
    input_dimension
):

    # --------------------------------------------------------
    # Architecture:
    #
    # 7
    # ↓
    # 6
    # ↓
    # 3  <- bottleneck
    # ↓
    # 6
    # ↓
    # 7
    # --------------------------------------------------------

    inputs = Input(
        shape=(input_dimension,),
        name="input"
    )

    encoded = Dense(
        6,
        activation="relu",
        name="encoder_1"
    )(
        inputs
    )

    bottleneck = Dense(
        3,
        activation="relu",
        name="bottleneck"
    )(
        encoded
    )

    decoded = Dense(
        6,
        activation="relu",
        name="decoder_1"
    )(
        bottleneck
    )

    outputs = Dense(
        input_dimension,
        activation="linear",
        name="reconstruction"
    )(
        decoded
    )


    autoencoder = Model(
        inputs=inputs,
        outputs=outputs,
        name="ssh_dense_autoencoder"
    )


    optimizer = tf.keras.optimizers.Adam(
        learning_rate=LEARNING_RATE
    )


    autoencoder.compile(
        optimizer=optimizer,
        loss="mse"
    )


    return autoencoder


# ============================================================
# Train Autoencoder
# ============================================================

def train_autoencoder(
    model,
    X_train,
    X_validation
):

    early_stopping = EarlyStopping(

        # Monitor validation reconstruction loss.
        monitor="val_loss",

        # Stop when validation loss stops improving.
        patience=PATIENCE,

        # Restore the best model weights rather than
        # keeping the final epoch.
        restore_best_weights=True,

        verbose=1
    )


    history = model.fit(

        # Autoencoder target = its own input.
        X_train,
        X_train,

        validation_data=(
            X_validation,
            X_validation
        ),

        epochs=EPOCHS,

        batch_size=BATCH_SIZE,

        shuffle=True,

        callbacks=[
            early_stopping
        ],

        verbose=1
    )


    return history


# ============================================================
# Reconstruction error
# ============================================================

def calculate_reconstruction_error(
    model,
    X
):

    reconstructed = model.predict(
        X,
        verbose=0
    )


    # --------------------------------------------------------
    # Mean squared reconstruction error PER WINDOW.
    #
    # Each row receives one reconstruction-error value.
    # --------------------------------------------------------

    errors = np.mean(
        np.square(
            X - reconstructed
        ),
        axis=1
    )


    return errors


# ============================================================
# Determine anomaly threshold
# ============================================================

def determine_threshold(
    validation_errors
):

    # --------------------------------------------------------
    # Autoencoder v1 threshold:
    #
    # 99th percentile of reconstruction errors observed in
    # the unseen-IP normal-reference VALIDATION set.
    #
    # This is NOT an attack probability.
    # --------------------------------------------------------

    threshold = np.quantile(
        validation_errors,
        0.99
    )


    return float(
        threshold
    )


# ============================================================
# Print reconstruction-error statistics
# ============================================================

def print_error_statistics(
    name,
    errors
):

    print(
        f"\n{name}"
    )

    print(
        f"  count: "
        f"{len(errors)}"
    )

    print(
        f"  mean: "
        f"{np.mean(errors):.6f}"
    )

    print(
        f"  median: "
        f"{np.median(errors):.6f}"
    )

    print(
        f"  95%: "
        f"{np.quantile(errors, 0.95):.6f}"
    )

    print(
        f"  99%: "
        f"{np.quantile(errors, 0.99):.6f}"
    )

    print(
        f"  max: "
        f"{np.max(errors):.6f}"
    )


# ============================================================
# Apply Autoencoder to complete dataset
# ============================================================

def score_complete_dataset(
    df,
    scaler,
    model,
    threshold
):

    X_all = transform_features(
        df,
        scaler
    )


    errors = calculate_reconstruction_error(
        model,
        X_all
    )


    results = df.copy()


    results[
        "ae_reconstruction_error"
    ] = errors


    results[
        "ae_prediction"
    ] = np.where(
        errors > threshold,
        "ANOMALOUS",
        "NORMAL"
    )


    return results


# ============================================================
# Evaluate by existing comparison category
# ============================================================

def evaluate_by_category(
    results
):

    print(
        "\n============================================"
    )

    print(
        "AUTOENCODER BY EXISTING CATEGORY"
    )

    print(
        "============================================"
    )


    summary = (
        results
        .groupby(
            "agreement"
        )
        .agg(
            windows=(
                "agreement",
                "size"
            ),

            mean_error=(
                "ae_reconstruction_error",
                "mean"
            ),

            median_error=(
                "ae_reconstruction_error",
                "median"
            ),

            anomalous_windows=(
                "ae_prediction",
                lambda x:
                    (x == "ANOMALOUS").sum()
            )
        )
    )


    summary[
        "ae_flag_rate_pct"
    ] = (
        summary[
            "anomalous_windows"
        ]
        / summary[
            "windows"
        ]
        * 100
    )


    print(
        summary
        .sort_values(
            "mean_error",
            ascending=False
        )
        .round(
            {
                "mean_error": 6,
                "median_error": 6,
                "ae_flag_rate_pct": 2
            }
        )
        .to_string()
    )


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":

    # ========================================================
    # 1. Load complete comparison table
    # ========================================================

    df = load_data(
        COMPARISON_FILE
    )


    # ========================================================
    # 2. Select conservative normal-reference pool
    # ========================================================

    normal_reference = (
        select_normal_reference(
            df
        )
    )


    # ========================================================
    # 3. Split by source IP
    # ========================================================

    (
        train_df,
        validation_df,
        test_df
    ) = split_by_source_ip(
        normal_reference
    )


    # ========================================================
    # 4. Verify no source-IP leakage
    # ========================================================

    verify_no_ip_leakage(
        train_df,
        validation_df,
        test_df
    )


    # ========================================================
    # 5. Display split statistics
    # ========================================================

    print_split_statistics(
        train_df,
        validation_df,
        test_df
    )


    # ========================================================
    # 6. Validate features
    # ========================================================

    validate_features(
        train_df,
        validation_df,
        test_df
    )


    # ========================================================
    # 7. Check feature variance
    # ========================================================

    check_training_variance(
        train_df
    )


    # ========================================================
    # 8. Fit RobustScaler on TRAINING data only
    # ========================================================

    scaler = fit_scaler(
        train_df
    )


    # ========================================================
    # 9. Transform reference-normal splits
    # ========================================================

    X_train = transform_features(
        train_df,
        scaler
    )

    X_validation = transform_features(
        validation_df,
        scaler
    )

    X_test = transform_features(
        test_df,
        scaler
    )


    print(
        "\n============================================"
    )

    print(
        "MODEL INPUT SHAPES"
    )

    print(
        "============================================"
    )


    print(
        f"X_train:      "
        f"{X_train.shape}"
    )

    print(
        f"X_validation: "
        f"{X_validation.shape}"
    )

    print(
        f"X_test:       "
        f"{X_test.shape}"
    )


    # ========================================================
    # 10. Build Autoencoder
    # ========================================================

    autoencoder = build_autoencoder(
        input_dimension=len(
            MODEL_FEATURES
        )
    )


    print(
        "\n============================================"
    )

    print(
        "AUTOENCODER ARCHITECTURE"
    )

    print(
        "============================================"
    )


    autoencoder.summary()


    # ========================================================
    # 11. Train
    # ========================================================

    print(
        "\n============================================"
    )

    print(
        "TRAINING AUTOENCODER"
    )

    print(
        "============================================"
    )


    history = train_autoencoder(
        autoencoder,
        X_train,
        X_validation
    )


    print(
        f"\nEpochs completed: "
        f"{len(history.history['loss'])}"
    )


    print(
        f"Best training loss: "
        f"{min(history.history['loss']):.6f}"
    )


    print(
        f"Best validation loss: "
        f"{min(history.history['val_loss']):.6f}"
    )


    # ========================================================
    # 12. Reconstruction errors
    # ========================================================

    train_errors = (
        calculate_reconstruction_error(
            autoencoder,
            X_train
        )
    )

    validation_errors = (
        calculate_reconstruction_error(
            autoencoder,
            X_validation
        )
    )

    test_errors = (
        calculate_reconstruction_error(
            autoencoder,
            X_test
        )
    )


    print(
        "\n============================================"
    )

    print(
        "RECONSTRUCTION ERROR SUMMARY"
    )

    print(
        "============================================"
    )


    print_error_statistics(
        "TRAIN",
        train_errors
    )

    print_error_statistics(
        "VALIDATION",
        validation_errors
    )

    print_error_statistics(
        "TEST NORMAL-REFERENCE",
        test_errors
    )


    # ========================================================
    # 13. Determine threshold from VALIDATION ONLY
    # ========================================================

    threshold = determine_threshold(
        validation_errors
    )


    print(
        "\n============================================"
    )

    print(
        "AUTOENCODER THRESHOLD"
    )

    print(
        "============================================"
    )


    print(
        "Threshold source: "
        "99th percentile of validation "
        "normal-reference reconstruction errors"
    )


    print(
        f"Threshold: "
        f"{threshold:.6f}"
    )


    # ========================================================
    # 14. Evaluate held-out normal-reference test
    # ========================================================

    test_predictions = np.where(
        test_errors > threshold,
        "ANOMALOUS",
        "NORMAL"
    )


    test_false_alerts = (
        test_predictions
        == "ANOMALOUS"
    ).sum()


    test_false_alert_rate = (
        test_false_alerts
        / len(test_predictions)
        * 100
    )


    print(
        "\n============================================"
    )

    print(
        "HELD-OUT NORMAL-REFERENCE TEST"
    )

    print(
        "============================================"
    )


    print(
        f"Reference-normal test windows: "
        f"{len(test_predictions)}"
    )


    print(
        f"Flagged anomalous: "
        f"{test_false_alerts}"
    )


    print(
        f"Reference false-alert rate: "
        f"{test_false_alert_rate:.2f}%"
    )


    # ========================================================
    # 15. Score all 8,256 windows
    # ========================================================

    results = score_complete_dataset(
        df,
        scaler,
        autoencoder,
        threshold
    )


    print(
        "\n============================================"
    )

    print(
        "FULL-DATA AUTOENCODER PREDICTIONS"
    )

    print(
        "============================================"
    )


    prediction_counts = (
        results[
            "ae_prediction"
        ]
        .value_counts()
    )


    print(
        prediction_counts
    )


    print(
        "\nPrediction percentages:"
    )


    print(
        (
            prediction_counts
            / len(results)
            * 100
        )
        .round(2)
    )


    # ========================================================
    # 16. Compare with Rule / Isolation Forest categories
    # ========================================================

    evaluate_by_category(
        results
    )


    # ========================================================
    # 17. Show highest reconstruction errors
    # ========================================================

    print(
        "\n============================================"
    )

    print(
        "TOP AUTOENCODER ANOMALIES"
    )

    print(
        "============================================"
    )


    top_anomalies = (
        results
        .sort_values(
            "ae_reconstruction_error",
            ascending=False
        )
        .head(25)
    )


    print(
        top_anomalies[
            [
                "source_ip",
                "window_start",
                "failed_login_count",
                "invalid_user_count",
                "unique_users",
                "failure_ratio",
                "root_attempt_ratio",
                "disconnect_count",
                "no_identification_count",
                "prediction",
                "if_prediction",
                "agreement",
                "ae_prediction",
                "ae_reconstruction_error"
            ]
        ]
        .to_string(
            index=False
        )
    )


    # ========================================================
    # 18. Save original reference splits
    # ========================================================

    train_df.to_csv(
        TRAIN_OUTPUT,
        index=False
    )

    validation_df.to_csv(
        VALIDATION_OUTPUT,
        index=False
    )

    test_df.to_csv(
        TEST_OUTPUT,
        index=False
    )


    # ========================================================
    # 19. Save complete Autoencoder results
    # ========================================================

    results.to_csv(
        RESULTS_OUTPUT,
        index=False
    )


    # ========================================================
    # 20. Save trained neural network
    # ========================================================

    autoencoder.save(
        MODEL_OUTPUT
    )


    print(
        f"\nSaved training reference data to: "
        f"{TRAIN_OUTPUT}"
    )

    print(
        f"Saved validation reference data to: "
        f"{VALIDATION_OUTPUT}"
    )

    print(
        f"Saved normal test reference data to: "
        f"{TEST_OUTPUT}"
    )

    print(
        f"Saved complete Autoencoder results to: "
        f"{RESULTS_OUTPUT}"
    )

    print(
        f"Saved trained Autoencoder to: "
        f"{MODEL_OUTPUT}"
    )