"""
DC-Guardian Phase 1
GRU Full-Q4 Evaluation

Evaluates the frozen GRU v1 probabilities on the complete
natural-prevalence GRU-eligible Q4 population.

This is the authoritative Q4 GRU ranking evaluation.

2026 Q1 remains locked.
"""

import numpy as np
import pandas as pd

from sklearn.metrics import (
    average_precision_score,
    roc_auc_score,
)

from evidence.predictive_maintenance.src.gru.config import (
    GRU_Q4_EVALUATION_METADATA_FILE,
    GRU_Q4_PROBABILITY_FILE,
    RF_BENCHMARK_PR_AUC,
    RF_BENCHMARK_ROC_AUC,
)


def main():

    print(
        "\n============================================"
    )
    print(
        "DC-GUARDIAN GRU FULL Q4 EVALUATION"
    )
    print(
        "============================================"
    )


    # ========================================================
    # Load full-Q4 results
    # ========================================================

    metadata = pd.read_parquet(
        GRU_Q4_EVALUATION_METADATA_FILE
    )


    probabilities = np.load(
        GRU_Q4_PROBABILITY_FILE,
        mmap_mode="r",
    )


    if len(metadata) != len(
        probabilities
    ):

        raise AssertionError(
            "GRU evaluation metadata/probability "
            "count mismatch."
        )


    y_true = (
        metadata[
            "label"
        ]
        .astype(int)
        .to_numpy()
    )


    # ========================================================
    # Population integrity
    # ========================================================

    rows = len(
        metadata
    )


    positives = int(
        y_true.sum()
    )


    negatives = (
        rows
        - positives
    )


    positive_drives = (
        metadata.loc[
            metadata[
                "label"
            ].eq(1),
            "serial_number",
        ]
        .nunique()
    )


    prevalence = (
        positives
        / rows
    )


    print(
        "Eligible Q4 sequences:",
        f"{rows:,}"
    )

    print(
        "Positive sequences:",
        f"{positives:,}"
    )

    print(
        "Negative sequences:",
        f"{negatives:,}"
    )

    print(
        "Positive drives:",
        f"{positive_drives:,}"
    )

    print(
        "Natural prevalence:",
        f"{prevalence:.6%}"
    )


    # ========================================================
    # Ranking metrics
    # ========================================================

    pr_auc = average_precision_score(
        y_true,
        probabilities,
    )


    roc_auc = roc_auc_score(
        y_true,
        probabilities,
    )


    pr_lift = (
        pr_auc
        / prevalence
    )


    print(
        "\n============================================"
    )
    print(
        "GRU V1 - NATURAL Q4 RESULTS"
    )
    print(
        "============================================"
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
        "PR lift vs prevalence:",
        f"{pr_lift:.2f}x"
    )


    # ========================================================
    # Context only:
    # RF benchmark is full Q4, not yet common-population RF.
    # ========================================================

    print(
        "\n============================================"
    )
    print(
        "REFERENCE CONTEXT"
    )
    print(
        "============================================"
    )


    print(
        "Frozen RF full-Q4 PR-AUC:",
        f"{RF_BENCHMARK_PR_AUC:.6f}"
    )

    print(
        "GRU eligible-Q4 PR-AUC:",
        f"{pr_auc:.6f}"
    )


    print(
        "\nFrozen RF full-Q4 ROC-AUC:",
        f"{RF_BENCHMARK_ROC_AUC:.6f}"
    )

    print(
        "GRU eligible-Q4 ROC-AUC:",
        f"{roc_auc:.6f}"
    )


    print(
        "\nIMPORTANT:"
    )

    print(
        "These RF and GRU values use different "
        "eligible populations."
    )

    print(
        "Do not select a winner from this "
        "comparison alone."
    )


    print(
        "\nPASS: Natural-prevalence GRU "
        "Q4 evaluation completed."
    )

    print(
        "PASS: 2026 Q1 remains untouched."
    )


    print(
        "\n============================================"
    )
    print(
        "GRU FULL Q4 EVALUATION PASSED"
    )
    print(
        "============================================"
    )


if __name__ == "__main__":
    main()
