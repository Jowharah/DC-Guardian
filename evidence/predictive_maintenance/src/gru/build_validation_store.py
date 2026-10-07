"""
DC-Guardian Evidence
GRU Development Validation Sequence Store

Materializes the fixed sampled Q4 development-validation
population.

Uses:
    final 29 days of Q3
    +
    Q4

No Q4 information is used to fit normalization statistics.
2026 Q1 remains locked.
"""

import numpy as np
import pandas as pd

from evidence.predictive_maintenance.src.config import (
    FEATURE_DATA_DIR,
)

from evidence.predictive_maintenance.src.gru.config import (
    GRU_SEQUENCE_LENGTH,
    GRU_SEQUENCE_STORE_DIR,
    GRU_SMART_FEATURES,
    GRU_VALIDATION_LABEL_FILE,
    GRU_VALIDATION_METADATA_FILE,
    GRU_VALIDATION_SAMPLE_FILE,
    GRU_VALIDATION_SEQUENCE_FILE,
)


def load_source_period(
    period,
):

    file_path = (
        FEATURE_DATA_DIR
        / f"{period}_features.parquet"
    )

    columns = (
        [
            "date",
            "serial_number",
        ]
        + GRU_SMART_FEATURES
    )

    df = pd.read_parquet(
        file_path,
        columns=columns,
    )

    df["date"] = pd.to_datetime(
        df["date"],
        errors="raise",
    )

    return df


def main():

    print(
        "\n============================================"
    )
    print(
        "DC-GUARDIAN GRU VALIDATION STORE"
    )
    print(
        "============================================"
    )


    sample = pd.read_parquet(
        GRU_VALIDATION_SAMPLE_FILE
    )

    sample["endpoint_date"] = pd.to_datetime(
        sample["endpoint_date"]
    )


    # ========================================================
    # Load Q3 tail + Q4
    # ========================================================

    q3 = load_source_period(
        "2025_Q3"
    )

    q4 = load_source_period(
        "2025_Q4"
    )


    q3_end = q3["date"].max()

    history_start = (
        q3_end
        - pd.Timedelta(
            days=28
        )
    )


    q3_tail = q3[
        q3["date"]
        >= history_start
    ].copy()


    print(
        "Q3 history rows:",
        f"{len(q3_tail):,}"
    )

    print(
        "Q4 rows:",
        f"{len(q4):,}"
    )


    combined = pd.concat(
        [
            q3_tail,
            q4,
        ],
        ignore_index=True,
    )


    combined["serial_number"] = (
        combined[
            "serial_number"
        ]
        .astype(str)
    )


    combined = (
        combined
        .sort_values(
            [
                "serial_number",
                "date",
            ]
        )
        .reset_index(
            drop=True
        )
    )


    # ========================================================
    # Keep only drives needed by sampled validation
    # ========================================================

    sample["serial_number"] = (
        sample[
            "serial_number"
        ]
        .astype(str)
    )


    selected_serials = set(
        sample[
            "serial_number"
        ]
    )


    combined = combined[
        combined[
            "serial_number"
        ].isin(
            selected_serials
        )
    ].copy()


    drive_groups = {
        serial:
            drive.reset_index(
                drop=True
            )

        for serial, drive
        in combined.groupby(
            "serial_number",
            sort=False,
        )
    }


    # ========================================================
    # Create disk-backed arrays
    # ========================================================

    sequence_count = len(
        sample
    )


    shape = (
        sequence_count,
        GRU_SEQUENCE_LENGTH,
        len(
            GRU_SMART_FEATURES
        ),
    )


    GRU_SEQUENCE_STORE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


    sequences = np.lib.format.open_memmap(
        GRU_VALIDATION_SEQUENCE_FILE,
        mode="w+",
        dtype=np.float32,
        shape=shape,
    )


    labels = np.lib.format.open_memmap(
        GRU_VALIDATION_LABEL_FILE,
        mode="w+",
        dtype=np.int8,
        shape=(sequence_count,),
    )


    metadata_rows = []


    # ========================================================
    # Materialize sequences
    # ========================================================

    for position, row in enumerate(
        sample.itertuples(
            index=False
        )
    ):

        serial = str(
            row.serial_number
        )

        endpoint = pd.Timestamp(
            row.endpoint_date
        )


        drive = drive_groups.get(
            serial
        )


        if drive is None:

            raise RuntimeError(
                f"Missing Q4 history for {serial}"
            )


        matches = np.flatnonzero(
            drive[
                "date"
            ]
            .eq(
                endpoint
            )
            .to_numpy()
        )


        if len(matches) != 1:

            raise RuntimeError(
                "Expected exactly one endpoint "
                f"for {serial} at {endpoint}."
            )


        end_position = int(
            matches[0]
        )


        start_position = (
            end_position
            - GRU_SEQUENCE_LENGTH
            + 1
        )


        if start_position < 0:

            raise RuntimeError(
                "Insufficient Q4 sequence history."
            )


        window = drive.iloc[
            start_position:
            end_position + 1
        ]


        if len(window) != GRU_SEQUENCE_LENGTH:

            raise RuntimeError(
                "Incorrect validation sequence length."
            )


        differences = (
            window[
                "date"
            ]
            .diff()
            .dropna()
            .dt.days
        )


        if not differences.eq(1).all():

            raise RuntimeError(
                "Non-consecutive Q4 sequence."
            )


        values = (
            window[
                GRU_SMART_FEATURES
            ]
            .apply(
                pd.to_numeric,
                errors="coerce",
            )
            .to_numpy(
                dtype=np.float32
            )
        )


        sequences[
            position
        ] = values


        labels[
            position
        ] = int(
            row.label
        )


        metadata_rows.append(
            {
                "store_position":
                    position,

                "serial_number":
                    serial,

                "endpoint_date":
                    endpoint,

                "label":
                    int(
                        row.label
                    ),
            }
        )


    sequences.flush()
    labels.flush()


    metadata = pd.DataFrame(
        metadata_rows
    )


    metadata.to_parquet(
        GRU_VALIDATION_METADATA_FILE,
        index=False,
    )


    positive_count = int(
        np.asarray(
            labels
        ).sum()
    )


    if positive_count != 3188:

        raise AssertionError(
            "Q4 positive sequence count changed."
        )


    print(
        "\n============================================"
    )
    print(
        "GRU VALIDATION STORE SUMMARY"
    )
    print(
        "============================================"
    )

    print(
        "Sequences:",
        f"{sequence_count:,}"
    )

    print(
        "Positive:",
        f"{positive_count:,}"
    )

    print(
        "Negative:",
        f"{sequence_count - positive_count:,}"
    )

    print(
        "Shape:",
        shape
    )

    print(
        "\nPASS: Q3 history carryover preserved."
    )

    print(
        "PASS: Q4 validation sequences materialized."
    )

    print(
        "PASS: Training normalization untouched."
    )

    print(
        "PASS: 2026 Q1 not accessed."
    )

    print(
        "\n============================================"
    )
    print(
        "GRU VALIDATION STORE PASSED"
    )
    print(
        "============================================"
    )


if __name__ == "__main__":
    main()
