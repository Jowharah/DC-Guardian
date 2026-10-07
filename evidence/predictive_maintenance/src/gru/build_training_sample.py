"""
DC-Guardian Phase 1
GRU Training Endpoint Sampling

Creates the frozen GRU development training sample.

All valid positive sequence endpoints are retained.
Negative endpoints are sampled at 50:1.

Only 2025 Q2 and Q3 are used.
2025 Q4 remains validation.
2026 Q1 remains locked.
"""

import pandas as pd

from evidence.predictive_maintenance.src.gru.config import (
    GRU_INDEX_DIR,
    GRU_NEGATIVE_TO_POSITIVE_RATIO,
    GRU_RANDOM_STATE,
    GRU_TRAIN_PERIODS,
)


OUTPUT_FILE = (
    GRU_INDEX_DIR
    / "gru_training_sample.parquet"
)


def main():

    print(
        "\n============================================"
    )
    print(
        "DC-GUARDIAN GRU TRAINING SAMPLE"
    )
    print(
        "============================================"
    )

    positive_parts = []
    negative_parts = []


    for period in GRU_TRAIN_PERIODS:

        file_path = (
            GRU_INDEX_DIR
            / f"{period}_sequence_index.parquet"
        )

        if not file_path.exists():
            raise FileNotFoundError(
                f"Missing sequence index: {file_path}"
            )

        index_df = pd.read_parquet(
            file_path
        )

        # Stable sequence identity only.
        index_df = index_df[
            [
                "serial_number",
                "endpoint_date",
                "label",
            ]
        ].copy()

        index_df["period"] = period

        positive = index_df[
            index_df["label"].eq(1)
        ].copy()

        negative = index_df[
            index_df["label"].eq(0)
        ].copy()

        positive_parts.append(
            positive
        )

        negative_parts.append(
            negative
        )

        print(
            f"{period}: "
            f"positive={len(positive):,} | "
            f"negative={len(negative):,}"
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
        * GRU_NEGATIVE_TO_POSITIVE_RATIO
    )

    total_available_negative = sum(
        len(part)
        for part in negative_parts
    )


    print(
        "\nPositive endpoints:",
        f"{total_positive:,}"
    )

    print(
        "Target negative endpoints:",
        f"{target_negative:,}"
    )


    # ========================================================
    # Proportional negative sampling by period
    # ========================================================

    sampled_negative_parts = []

    remaining = target_negative


    for index, negative in enumerate(
        negative_parts
    ):

        if index == len(
            negative_parts
        ) - 1:

            sample_size = min(
                remaining,
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
                GRU_RANDOM_STATE
                + index
            ),
        )


        sampled_negative_parts.append(
            sampled
        )

        remaining -= sample_size


    negatives = pd.concat(
        sampled_negative_parts,
        ignore_index=True,
    )


    # ========================================================
    # Combine and shuffle
    # ========================================================

    training_sample = pd.concat(
        [
            positives,
            negatives,
        ],
        ignore_index=True,
    )


    training_sample = (
        training_sample
        .sample(
            frac=1.0,
            random_state=GRU_RANDOM_STATE,
        )
        .reset_index(
            drop=True
        )
    )


    # ========================================================
    # Integrity
    # ========================================================

    duplicate_keys = (
        training_sample
        .duplicated(
            subset=[
                "period",
                "serial_number",
                "endpoint_date",
            ]
        )
        .sum()
    )


    if duplicate_keys != 0:

        raise AssertionError(
            "Duplicate GRU sequence endpoints found."
        )


    actual_positive = int(
        training_sample[
            "label"
        ].sum()
    )

    actual_negative = (
        len(training_sample)
        - actual_positive
    )


    if actual_positive != total_positive:

        raise AssertionError(
            "Not all positive sequences were retained."
        )


    if actual_negative != target_negative:

        raise AssertionError(
            "Negative sampling target was not met."
        )


    # ========================================================
    # Save
    # ========================================================

    training_sample.to_parquet(
        OUTPUT_FILE,
        index=False,
    )


    print(
        "\n============================================"
    )
    print(
        "GRU TRAINING SAMPLE SUMMARY"
    )
    print(
        "============================================"
    )

    print(
        "Positive sequences:",
        f"{actual_positive:,}"
    )

    print(
        "Negative sequences:",
        f"{actual_negative:,}"
    )

    print(
        "Total sequences:",
        f"{len(training_sample):,}"
    )

    print(
        "Negative : positive:",
        f"{actual_negative / actual_positive:.2f}:1"
    )

    print(
        "Duplicate endpoints:",
        duplicate_keys
    )

    print(
        "Saved:",
        OUTPUT_FILE
    )

    print(
        "\n============================================"
    )
    print(
        "GRU TRAINING SAMPLE PASSED"
    )
    print(
        "============================================"
    )


if __name__ == "__main__":
    main()
