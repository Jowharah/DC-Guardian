"""
DC-Guardian Evidence
Predictive Maintenance GRU Sequence Index Construction

Builds development sequence indexes for:

    TRAIN:
        2025 Q2
        2025 Q3

    VALIDATION:
        2025 Q4

The final test period, 2026 Q1, remains locked and is not
accessed by this script.

This stage creates sequence endpoint indexes only.
It does NOT materialize the 30 x 8 GRU tensors.
"""

import pandas as pd

from evidence.predictive_maintenance.src.config import (
    FEATURE_DATA_DIR,
)

from evidence.predictive_maintenance.src.gru.config import (
    GRU_INDEX_DIR,
    GRU_SMART_FEATURES,
    GRU_TEST_PERIOD,
    GRU_TRAIN_PERIODS,
    GRU_VALIDATION_PERIOD,
)

from evidence.predictive_maintenance.src.gru.sequence_builder import (
    build_sequence_index_fast,
)


# ============================================================
# Development periods only
# ============================================================

ALLOWED_PERIODS = (
    GRU_TRAIN_PERIODS
    + [
        GRU_VALIDATION_PERIOD
    ]
)


# ============================================================
# Load one development period
# ============================================================

def load_period(
    period: str,
) -> pd.DataFrame:
    """
    Load only the columns required for GRU sequence
    construction.

    The final 2026 Q1 test period is explicitly blocked.
    """

    if period == GRU_TEST_PERIOD:

        raise RuntimeError(
            "GRU final-test period is locked."
        )


    if period not in ALLOWED_PERIODS:

        raise ValueError(
            "Unexpected GRU development period: "
            f"{period}"
        )


    file_path = (
        FEATURE_DATA_DIR
        / f"{period}_features.parquet"
    )


    if not file_path.exists():

        raise FileNotFoundError(
            "Feature dataset not found: "
            f"{file_path}"
        )


    columns = (
        [
            "date",
            "serial_number",
            "fail_within_7_days",
        ]
        + GRU_SMART_FEATURES
    )


    df = pd.read_parquet(
        file_path,
        columns=columns,
    )


    return df


# ============================================================
# Main
# ============================================================

def main():

    GRU_INDEX_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(
        "\n============================================"
    )
    print(
        "DC-GUARDIAN GRU SEQUENCE INDEX BUILD"
    )
    print(
        "============================================"
    )

    print(
        "Development periods:",
        ALLOWED_PERIODS
    )

    print(
        "Final test:",
        GRU_TEST_PERIOD,
        "(LOCKED)"
    )


    summary_rows = []

    previous_tail = None


    for period in ALLOWED_PERIODS:

        print(
            "\n============================================"
        )
        print(
            f"BUILDING INDEX: {period}"
        )
        print(
            "============================================"
        )


        # ====================================================
        # Load current quarter
        # ====================================================

        current = load_period(
            period
        )


        current["date"] = pd.to_datetime(
            current["date"],
            errors="raise",
        )


        current_start = (
            current["date"].min()
        )

        current_end = (
            current["date"].max()
        )


        print(
            "Current period:",
            current_start,
            "->",
            current_end
        )

        print(
            "Source rows:",
            f"{len(current):,}"
        )

        print(
            "Source drives:",
            f"{current['serial_number'].nunique():,}"
        )


        # ====================================================
        # Carry previous-quarter history
        # ====================================================

        if previous_tail is not None:

            combined = pd.concat(
                [
                    previous_tail,
                    current,
                ],
                ignore_index=True,
            )

            history_rows = len(
                previous_tail
            )

        else:

            combined = current.copy()

            history_rows = 0


        print(
            "History rows carried:",
            f"{history_rows:,}"
        )


        # ====================================================
        # Build index using combined history
        # ====================================================

        sequence_index = (
            build_sequence_index_fast(
                combined
            )
        )


        # ====================================================
        # IMPORTANT:
        # Keep endpoints belonging to CURRENT quarter only.
        # ====================================================

        sequence_index[
            "endpoint_date"
        ] = pd.to_datetime(
            sequence_index[
                "endpoint_date"
            ]
        )


        sequence_index = (
            sequence_index[
                (
                    sequence_index[
                        "endpoint_date"
                    ]
                    >= current_start
                )
                &
                (
                    sequence_index[
                        "endpoint_date"
                    ]
                    <= current_end
                )
            ]
            .reset_index(
                drop=True
            )
        )


        # ====================================================
        # Statistics
        # ====================================================

        positives = int(
            sequence_index[
                "label"
            ]
            .sum()
        )


        negatives = (
            len(sequence_index)
            - positives
        )


        positive_drives = (
            sequence_index.loc[
                sequence_index[
                    "label"
                ].eq(1),
                "serial_number",
            ]
            .nunique()
        )


        sequence_drives = (
            sequence_index[
                "serial_number"
            ]
            .nunique()
        )


        positive_rate = (
            positives
            / len(sequence_index)
            if len(sequence_index) > 0
            else 0.0
        )


        # ====================================================
        # Save index
        # ====================================================

        output_file = (
            GRU_INDEX_DIR
            / f"{period}_sequence_index.parquet"
        )


        sequence_index.to_parquet(
            output_file,
            index=False,
        )


        summary_rows.append(
            {
                "period":
                    period,

                "source_rows":
                    len(current),

                "source_drives":
                    current[
                        "serial_number"
                    ].nunique(),

                "history_rows":
                    history_rows,

                "valid_sequences":
                    len(sequence_index),

                "sequence_drives":
                    sequence_drives,

                "positive_sequences":
                    positives,

                "negative_sequences":
                    negatives,

                "positive_drives":
                    positive_drives,

                "positive_rate":
                    positive_rate,
            }
        )


        print(
            "Valid sequences:",
            f"{len(sequence_index):,}"
        )

        print(
            "Positive sequences:",
            f"{positives:,}"
        )

        print(
            "Positive drives:",
            f"{positive_drives:,}"
        )


        # ====================================================
        # Retain only 29 calendar days for next quarter
        # ====================================================

        history_start = (
            current_end
            - pd.Timedelta(
                days=28
            )
        )


        previous_tail = (
            current[
                current["date"]
                >= history_start
            ]
            .copy()
        )


        print(
            "History retained for next period:",
            f"{len(previous_tail):,}"
        )


        del current
        del combined
        del sequence_index


    # ========================================================
    # Save summary
    # ========================================================

    summary = pd.DataFrame(
        summary_rows
    )


    summary_file = (
        GRU_INDEX_DIR
        / "development_sequence_summary.csv"
    )


    summary.to_csv(
        summary_file,
        index=False,
    )


    print(
        "\n============================================"
    )
    print(
        "GRU DEVELOPMENT SEQUENCE SUMMARY"
    )
    print(
        "============================================"
    )

    print(
        summary.to_string(
            index=False
        )
    )


    if GRU_TEST_PERIOD in (
        summary[
            "period"
        ].tolist()
    ):

        raise AssertionError(
            "Final-test period was accessed."
        )


    print(
        "\nPASS: Cross-quarter history preserved."
    )

    print(
        "PASS:",
        GRU_TEST_PERIOD,
        "was not accessed."
    )

    print(
        "\n============================================"
    )
    print(
        "GRU SEQUENCE INDEX BUILD PASSED"
    )
    print(
        "============================================"
    )


if __name__ == "__main__":
    main()
