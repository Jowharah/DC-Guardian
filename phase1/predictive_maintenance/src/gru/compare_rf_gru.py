"""
DC-Guardian Phase 1
Predictive Maintenance

Fair RF vs GRU comparison on the exact same
GRU-eligible Q4 population.

No retraining is performed.
2026 Q1 remains locked.
"""

import joblib
import numpy as np
import pandas as pd

from sklearn.metrics import (
    average_precision_score,
    roc_auc_score,
)

from phase1.predictive_maintenance.src.config import (
    FEATURE_DATA_DIR,
    RF_MODEL_DIR,
    TEMPORAL_RF_FEATURES,
)

from phase1.predictive_maintenance.src.gru.config import (
    GRU_Q4_EVALUATION_METADATA_FILE,
    GRU_Q4_PROBABILITY_FILE,
)


RF_MODEL_FILE = (
    RF_MODEL_DIR
    / "temporal_rf_v2.joblib"
)


def main():

    print(
        "\n============================================"
    )
    print(
        "DC-GUARDIAN RF vs GRU"
    )
    print(
        "COMMON Q4 POPULATION"
    )
    print(
        "============================================"
    )


    # ========================================================
    # Load GRU evaluation population
    # ========================================================

    metadata = pd.read_parquet(
        GRU_Q4_EVALUATION_METADATA_FILE
    )


    metadata["endpoint_date"] = pd.to_datetime(
        metadata["endpoint_date"]
    )


    metadata["serial_number"] = (
        metadata["serial_number"]
        .astype(str)
    )


    gru_probability = np.load(
        GRU_Q4_PROBABILITY_FILE,
        mmap_mode="r",
    )


    if len(metadata) != len(
        gru_probability
    ):

        raise AssertionError(
            "GRU metadata/probability mismatch."
        )


    y_true = (
        metadata[
            "label"
        ]
        .astype(int)
        .to_numpy()
    )


    print(
        "Common endpoints:",
        f"{len(metadata):,}"
    )

    print(
        "Positive rows:",
        f"{int(y_true.sum()):,}"
    )

    print(
        "Positive drives:",
        f"{metadata.loc[metadata['label'].eq(1), 'serial_number'].nunique():,}"
    )


    # ========================================================
    # Load frozen RF
    # ========================================================

    rf_pipeline = joblib.load(
        RF_MODEL_FILE
    )


    # ========================================================
    # Load Q4 RF features
    # ========================================================

    q4_file = (
        FEATURE_DATA_DIR
        / "2025_Q4_features.parquet"
    )


    columns = (
        [
            "date",
            "serial_number",
            "fail_within_7_days",
        ]
        + TEMPORAL_RF_FEATURES
    )


    q4 = pd.read_parquet(
        q4_file,
        columns=columns,
    )


    q4 = (
        q4[
            q4[
                "fail_within_7_days"
            ]
            .notna()
        ]
        .copy()
    )


    q4["date"] = pd.to_datetime(
        q4["date"]
    )


    q4["serial_number"] = (
        q4["serial_number"]
        .astype(str)
    )


    # ========================================================
    # Restrict RF to exact GRU endpoint population
    # ========================================================

    common_keys = metadata[
        [
            "serial_number",
            "endpoint_date",
            "label",
            "evaluation_position",
        ]
    ].rename(
        columns={
            "endpoint_date":
                "date"
        }
    )


    common = common_keys.merge(
        q4,
        on=[
            "serial_number",
            "date",
        ],
        how="left",
        validate="one_to_one",
    )


    if len(common) != len(
        metadata
    ):

        raise AssertionError(
            "Common-population row count changed."
        )


    missing_features = (
        common[
            TEMPORAL_RF_FEATURES
        ]
        .isna()
        .all(
            axis=1
        )
        .sum()
    )


    if missing_features:

        raise AssertionError(
            "Some GRU endpoints could not be "
            "matched to RF Q4 rows."
        )


    # ========================================================
    # Label integrity
    # ========================================================

    rf_labels = (
        common[
            "fail_within_7_days"
        ]
        .astype(int)
        .to_numpy()
    )


    metadata_labels = (
        common[
            "label"
        ]
        .astype(int)
        .to_numpy()
    )


    if not np.array_equal(
        rf_labels,
        metadata_labels,
    ):

        raise AssertionError(
            "RF/GRU target labels do not match."
        )


    # ========================================================
    # Restore GRU order
    # ========================================================

    common = (
        common
        .sort_values(
            "evaluation_position"
        )
        .reset_index(
            drop=True
        )
    )


    y_common = (
        common[
            "label"
        ]
        .astype(int)
        .to_numpy()
    )


    # ========================================================
    # RF probabilities
    # ========================================================

    print(
        "\nScoring frozen RF on common population..."
    )


    rf_probability = (
        rf_pipeline
        .predict_proba(
            common[
                TEMPORAL_RF_FEATURES
            ]
        )[:, 1]
    )


    # ========================================================
    # Ranking metrics
    # ========================================================

    rf_pr_auc = average_precision_score(
        y_common,
        rf_probability,
    )


    rf_roc_auc = roc_auc_score(
        y_common,
        rf_probability,
    )


    gru_pr_auc = average_precision_score(
        y_common,
        gru_probability,
    )


    gru_roc_auc = roc_auc_score(
        y_common,
        gru_probability,
    )


    prevalence = (
        y_common.mean()
    )


    # ========================================================
    # Comparison
    # ========================================================

    comparison = pd.DataFrame(
        [
            {
                "model":
                    "Temporal RF v2",

                "pr_auc":
                    rf_pr_auc,

                "roc_auc":
                    rf_roc_auc,

                "pr_lift":
                    rf_pr_auc
                    / prevalence,
            },

            {
                "model":
                    "GRU v1",

                "pr_auc":
                    gru_pr_auc,

                "roc_auc":
                    gru_roc_auc,

                "pr_lift":
                    gru_pr_auc
                    / prevalence,
            },
        ]
    )


    print(
        "\n============================================"
    )
    print(
        "COMMON-POPULATION RESULTS"
    )
    print(
        "============================================"
    )


    print(
        comparison.to_string(
            index=False
        )
    )


    print(
        "\nGRU PR-AUC change vs RF:",
        f"{gru_pr_auc - rf_pr_auc:+.6f}"
    )


    print(
        "GRU ROC-AUC change vs RF:",
        f"{gru_roc_auc - rf_roc_auc:+.6f}"
    )


    print(
        "\nPASS: Both models evaluated on "
        "identical Q4 endpoints."
    )

    print(
        "PASS: 2026 Q1 remains untouched."
    )


    print(
        "\n============================================"
    )
    print(
        "RF vs GRU COMPARISON PASSED"
    )
    print(
        "============================================"
    )


if __name__ == "__main__":
    main()