"""
DC-Guardian Phase 1
GRU Development Validation Sample

Creates a fixed Q4 sample for epoch-level model selection.

ALL eligible positive sequences are retained.
Negative sequences are sampled deterministically.

This sample is used only for:
    - early stopping
    - development model selection

Full Q4 evaluation is performed separately after training.

2026 Q1 remains locked.
"""

import pandas as pd

from evidence.predictive_maintenance.src.gru.config import (
    GRU_INDEX_DIR,
    GRU_RANDOM_STATE,
    GRU_VALIDATION_NEGATIVE_RATIO,
    GRU_VALIDATION_PERIOD,
    GRU_VALIDATION_SAMPLE_FILE,
)


def main():

    print(
        "\n============================================"
    )
    print(
        "DC-GUARDIAN GRU VALIDATION SAMPLE"
    )
    print(
        "============================================"
    )

    index_file = (
        GRU_INDEX_DIR
        / f"{GRU_VALIDATION_PERIOD}_sequence_index.parquet"
    )

    if not index_file.exists():

        raise FileNotFoundError(
            f"Q4 sequence index missing: {index_file}"
        )


    index_df = pd.read_parquet(
        index_file
    )


    index_df = index_df[
        [
            "serial_number",
            "endpoint_date",
            "label",
        ]
    ].copy()


    positive = index_df[
        index_df["label"].eq(1)
    ].copy()


    negative = index_df[
        index_df["label"].eq(0)
    ].copy()


    target_negative = (
        len(positive)
        * GRU_VALIDATION_NEGATIVE_RATIO
    )


    sampled_negative = negative.sample(
        n=min(
            target_negative,
            len(negative),
        ),
        random_state=GRU_RANDOM_STATE,
    )


    validation_sample = pd.concat(
        [
            positive,
            sampled_negative,
        ],
        ignore_index=True,
    )


    validation_sample = (
        validation_sample
        .sample(
            frac=1.0,
            random_state=GRU_RANDOM_STATE,
        )
        .reset_index(
            drop=True
        )
    )


    duplicate_count = (
        validation_sample
        .duplicated(
            [
                "serial_number",
                "endpoint_date",
            ]
        )
        .sum()
    )


    if duplicate_count:

        raise AssertionError(
            "Duplicate Q4 validation endpoints."
        )


    validation_sample.to_parquet(
        GRU_VALIDATION_SAMPLE_FILE,
        index=False,
    )


    print(
        "Eligible Q4 positives:",
        f"{len(positive):,}"
    )

    print(
        "Sampled Q4 negatives:",
        f"{len(sampled_negative):,}"
    )

    print(
        "Validation sequences:",
        f"{len(validation_sample):,}"
    )

    print(
        "Positive drives:",
        f"{positive['serial_number'].nunique():,}"
    )

    print(
        "Duplicate endpoints:",
        duplicate_count
    )

    print(
        "Saved:",
        GRU_VALIDATION_SAMPLE_FILE
    )


    print(
        "\n============================================"
    )
    print(
        "GRU VALIDATION SAMPLE PASSED"
    )
    print(
        "============================================"
    )


if __name__ == "__main__":
    main()
