"""
DC-Guardian Phase 1
Predictive Maintenance - Temporal Random Forest Training

Trains the frozen Maintenance v2 Random Forest candidate.

Development contract:
    TRAIN      = 2025 Q2 + Q3
    VALIDATION = 2025 Q4
    FINAL TEST = 2026 Q1 (not accessed by this script)

Training:
    - All positive drive-day observations retained.
    - Normal observations sampled at 50:1.
    - Median imputation fitted on training data only.
    - Random Forest configuration frozen from Q4 development.
"""

import json
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

from phase1.predictive_maintenance.src.config import (
    FEATURE_DATA_DIR,
    RANDOM_STATE,
    RF_MAX_DEPTH,
    RF_MAX_FEATURES,
    RF_MIN_SAMPLES_LEAF,
    RF_MODEL_DIR,
    RF_N_ESTIMATORS,
    RF_NEGATIVE_TO_POSITIVE_RATIO,
    RF_OPERATING_THRESHOLD,
    TEMPORAL_RF_FEATURES,
    TEST_PERIOD,
    TRAIN_PERIODS,
    VALIDATION_PERIOD,
)


MODEL_FILE = (
    RF_MODEL_DIR
    / "temporal_rf_v2.joblib"
)

METADATA_FILE = (
    RF_MODEL_DIR
    / "temporal_rf_v2_metadata.json"
)


def load_training_period(
    period: str,
) -> pd.DataFrame:
    """
    Load predictive rows for one training period.
    """

    file_path = (
        FEATURE_DATA_DIR
        / f"{period}_features.parquet"
    )

    if not file_path.exists():
        raise FileNotFoundError(
            f"Training feature file not found: {file_path}"
        )

    columns = (
        [
            "date",
            "serial_number",
            "fail_within_7_days",
        ]
        + TEMPORAL_RF_FEATURES
    )

    df = pd.read_parquet(
        file_path,
        columns=columns,
    )

    df = df[
        df["fail_within_7_days"]
        .notna()
    ].copy()

    return df


def build_training_sample() -> pd.DataFrame:
    """
    Retain all positive observations and sample normal
    observations using the frozen 50:1 ratio.
    """

    positive_parts = []

    negative_sources = []

    print(
        "\n============================================"
    )
    print(
        "BUILDING MAINTENANCE TRAINING SAMPLE"
    )
    print(
        "============================================"
    )

    for period in TRAIN_PERIODS:

        print(
            f"\nLoading {period}..."
        )

        df = load_training_period(
            period
        )

        positive = df[
            df["fail_within_7_days"]
            .eq(1)
        ].copy()

        negative = df[
            df["fail_within_7_days"]
            .eq(0)
        ].copy()

        print(
            "  Positive:",
            f"{len(positive):,}"
        )

        print(
            "  Negative:",
            f"{len(negative):,}"
        )

        positive_parts.append(
            positive
        )

        negative_sources.append(
            negative
        )

    positives = pd.concat(
        positive_parts,
        ignore_index=True,
    )

    total_positive = len(
        positives
    )

    target_negative = (
        total_positive
        * RF_NEGATIVE_TO_POSITIVE_RATIO
    )

    total_available_negative = sum(
        len(part)
        for part in negative_sources
    )

    sampled_negative_parts = []

    remaining_target = (
        target_negative
    )

    for index, negative in enumerate(
        negative_sources
    ):

        if index == (
            len(negative_sources) - 1
        ):

            sample_size = min(
                remaining_target,
                len(negative),
            )

        else:

            proportion = (
                len(negative)
                / total_available_negative
            )

            sample_size = int(
                round(
                    target_negative
                    * proportion
                )
            )

            sample_size = min(
                sample_size,
                len(negative),
            )

        sampled = negative.sample(
            n=sample_size,
            random_state=(
                RANDOM_STATE
                + index
            ),
        )

        sampled_negative_parts.append(
            sampled
        )

        remaining_target -= (
            sample_size
        )

    negatives = pd.concat(
        sampled_negative_parts,
        ignore_index=True,
    )

    training = pd.concat(
        [
            positives,
            negatives,
        ],
        ignore_index=True,
    )

    training = (
        training
        .sample(
            frac=1.0,
            random_state=RANDOM_STATE,
        )
        .reset_index(
            drop=True
        )
    )

    print(
        "\n--------------------------------------------"
    )

    print(
        "Positive rows:",
        f"{len(positives):,}"
    )

    print(
        "Sampled negative rows:",
        f"{len(negatives):,}"
    )

    print(
        "Training rows:",
        f"{len(training):,}"
    )

    print(
        "Negative : positive ratio:",
        f"{len(negatives) / len(positives):.2f}:1"
    )

    return training


def build_pipeline() -> Pipeline:
    """
    Build the frozen preprocessing + Random Forest pipeline.
    """

    return Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(
                    strategy="median",
                ),
            ),
            (
                "model",
                RandomForestClassifier(
                    n_estimators=
                        RF_N_ESTIMATORS,

                    max_depth=
                        RF_MAX_DEPTH,

                    min_samples_leaf=
                        RF_MIN_SAMPLES_LEAF,

                    max_features=
                        RF_MAX_FEATURES,

                    random_state=
                        RANDOM_STATE,

                    n_jobs=-1,
                ),
            ),
        ]
    )


def save_model_metadata(
    training: pd.DataFrame,
) -> None:
    """
    Save the frozen training contract alongside the model.
    """

    class_counts = (
        training[
            "fail_within_7_days"
        ]
        .astype(int)
        .value_counts()
        .to_dict()
    )

    metadata = {
        "model_name":
            "DC_Guardian_Temporal_RF_v2",

        "model_family":
            "RandomForestClassifier",

        "created_utc":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "train_periods":
            TRAIN_PERIODS,

        "validation_period":
            VALIDATION_PERIOD,

        "final_test_period":
            TEST_PERIOD,

        "final_test_used_during_training":
            False,

        "feature_count":
            len(
                TEMPORAL_RF_FEATURES
            ),

        "features":
            TEMPORAL_RF_FEATURES,

        "negative_to_positive_ratio":
            RF_NEGATIVE_TO_POSITIVE_RATIO,

        "training_rows":
            len(training),

        "training_positive_rows":
            int(
                class_counts.get(
                    1,
                    0,
                )
            ),

        "training_negative_rows":
            int(
                class_counts.get(
                    0,
                    0,
                )
            ),

        "random_state":
            RANDOM_STATE,

        "rf_parameters": {
            "n_estimators":
                RF_N_ESTIMATORS,

            "max_depth":
                RF_MAX_DEPTH,

            "min_samples_leaf":
                RF_MIN_SAMPLES_LEAF,

            "max_features":
                RF_MAX_FEATURES,
        },

        "candidate_operating_threshold":
            RF_OPERATING_THRESHOLD,

        "prediction_target":
            "explicit failure within next 7 days",
    }

    with open(
        METADATA_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            metadata,
            file,
            indent=2,
        )


def main():

    np.random.seed(
        RANDOM_STATE
    )

    RF_MODEL_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(
        "\n============================================"
    )
    print(
        "DC-GUARDIAN TEMPORAL RF V2 TRAINING"
    )
    print(
        "============================================"
    )

    print(
        "Training periods:",
        TRAIN_PERIODS
    )

    print(
        "Validation period:",
        VALIDATION_PERIOD
    )

    print(
        "Final test period:",
        TEST_PERIOD,
        "(LOCKED)"
    )

    print(
        "Features:",
        len(
            TEMPORAL_RF_FEATURES
        )
    )

    print(
        "Sampling ratio:",
        f"{RF_NEGATIVE_TO_POSITIVE_RATIO}:1"
    )

    training = (
        build_training_sample()
    )

    X_train = training[
        TEMPORAL_RF_FEATURES
    ]

    y_train = (
        training[
            "fail_within_7_days"
        ]
        .astype(int)
    )

    pipeline = build_pipeline()

    print(
        "\n============================================"
    )
    print(
        "TRAINING RANDOM FOREST"
    )
    print(
        "============================================"
    )

    pipeline.fit(
        X_train,
        y_train,
    )

    print(
        "PASS: Random Forest trained."
    )

    joblib.dump(
        pipeline,
        MODEL_FILE,
    )

    save_model_metadata(
        training
    )

    print(
        "PASS: Model pipeline saved."
    )

    print(
        "PASS: Training metadata saved."
    )

    print(
        "\nModel:"
    )

    print(
        MODEL_FILE
    )

    print(
        "\nMetadata:"
    )

    print(
        METADATA_FILE
    )

    print(
        "\n============================================"
    )
    print(
        "TEMPORAL RF V2 TRAINING PASSED"
    )
    print(
        "============================================"
    )


if __name__ == "__main__":
    main()