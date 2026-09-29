"""
DC-Guardian Phase 1
GRU Training Sequence Store

Materializes only the sampled TRAIN sequences:

    2025 Q2 + Q3

No Q4 validation data are used for training normalization.
2026 Q1 remains locked.

Output:
    train_sequences.npy
    train_labels.npy
    train_sequence_metadata.parquet
"""

import numpy as np
import pandas as pd

from phase1.predictive_maintenance.src.config import (
    FEATURE_DATA_DIR,
)

from phase1.predictive_maintenance.src.gru.config import (
    GRU_INDEX_DIR,
    GRU_SEQUENCE_LENGTH,
    GRU_SEQUENCE_STORE_DIR,
    GRU_SMART_FEATURES,
    GRU_TRAIN_LABEL_FILE,
    GRU_TRAIN_METADATA_FILE,
    GRU_TRAIN_PERIODS,
    GRU_TRAIN_SEQUENCE_FILE,
)


TRAIN_SAMPLE_FILE = (
    GRU_INDEX_DIR
    / "gru_training_sample.parquet"
)


def load_period(period):

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
        "DC-GUARDIAN GRU TRAIN SEQUENCE STORE"
    )
    print(
        "============================================"
    )

    if not TRAIN_SAMPLE_FILE.exists():

        raise FileNotFoundError(
            f"Training sample missing: "
            f"{TRAIN_SAMPLE_FILE}"
        )


    sample = pd.read_parquet(
        TRAIN_SAMPLE_FILE
    )

    sample["endpoint_date"] = pd.to_datetime(
        sample["endpoint_date"]
    )


    sequence_count = len(
        sample
    )


    expected_shape = (
        sequence_count,
        GRU_SEQUENCE_LENGTH,
        len(GRU_SMART_FEATURES),
    )


    print(
        "Training sequences:",
        f"{sequence_count:,}"
    )

    print(
        "Store shape:",
        expected_shape
    )


    GRU_SEQUENCE_STORE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


    # ========================================================
    # Disk-backed arrays
    # ========================================================

    sequences = np.lib.format.open_memmap(
        GRU_TRAIN_SEQUENCE_FILE,
        mode="w+",
        dtype=np.float32,
        shape=expected_shape,
    )


    labels = np.lib.format.open_memmap(
        GRU_TRAIN_LABEL_FILE,
        mode="w+",
        dtype=np.int8,
        shape=(sequence_count,),
    )


    # ========================================================
    # Process period-by-period
    # ========================================================

    written = 0

    previous_tail = None


    metadata_parts = []


    for period in GRU_TRAIN_PERIODS:

        print(
            "\n============================================"
        )
        print(
            f"MATERIALIZING {period}"
        )
        print(
            "============================================"
        )


        current = load_period(
            period
        )


        current_start = (
            current["date"].min()
        )

        current_end = (
            current["date"].max()
        )


        if previous_tail is not None:

            combined = pd.concat(
                [
                    previous_tail,
                    current,
                ],
                ignore_index=True,
            )

        else:

            combined = current.copy()


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


        period_sample = (
            sample[
                sample["period"].eq(
                    period
                )
            ]
            .copy()
        )


        print(
            "Selected endpoints:",
            f"{len(period_sample):,}"
        )


        # ====================================================
        # Stable lookup:
        # serial -> drive history
        # ====================================================

        selected_serials = set(
            period_sample[
                "serial_number"
            ].astype(str)
        )


        combined[
            "serial_number"
        ] = combined[
            "serial_number"
        ].astype(str)


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


        # Preserve sampled/shuffled order within this period.
        for row in period_sample.itertuples(
            index=False
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
                    f"Drive history missing: "
                    f"{serial}"
                )


            endpoint_matches = np.flatnonzero(
                drive[
                    "date"
                ]
                .eq(
                    endpoint
                )
                .to_numpy()
            )


            if len(endpoint_matches) != 1:

                raise RuntimeError(
                    "Expected exactly one endpoint "
                    f"for {serial} at {endpoint}."
                )


            end_position = int(
                endpoint_matches[0]
            )

            start_position = (
                end_position
                - GRU_SEQUENCE_LENGTH
                + 1
            )


            if start_position < 0:

                raise RuntimeError(
                    "Insufficient sequence history "
                    f"for {serial} at {endpoint}."
                )


            window = drive.iloc[
                start_position:
                end_position + 1
            ]


            if len(window) != GRU_SEQUENCE_LENGTH:

                raise RuntimeError(
                    "Unexpected GRU window length."
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
                    "Non-consecutive sequence reached "
                    "training store."
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
                written
            ] = values


            labels[
                written
            ] = int(
                row.label
            )


            metadata_parts.append(
                {
                    "store_position":
                        written,

                    "period":
                        period,

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


            written += 1


        # ====================================================
        # Retain previous-quarter history
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


        del current
        del combined
        del drive_groups


    # ========================================================
    # Integrity
    # ========================================================

    if written != sequence_count:

        raise AssertionError(
            "Sequence-store row count mismatch: "
            f"wrote {written:,}, "
            f"expected {sequence_count:,}."
        )


    sequences.flush()
    labels.flush()


    metadata = pd.DataFrame(
        metadata_parts
    )


    metadata.to_parquet(
        GRU_TRAIN_METADATA_FILE,
        index=False,
    )


    positive_count = int(
        np.asarray(
            labels
        ).sum()
    )


    print(
        "\n============================================"
    )
    print(
        "GRU TRAIN SEQUENCE STORE SUMMARY"
    )
    print(
        "============================================"
    )

    print(
        "Sequences written:",
        f"{written:,}"
    )

    print(
        "Positive sequences:",
        f"{positive_count:,}"
    )

    print(
        "Negative sequences:",
        f"{written - positive_count:,}"
    )

    print(
        "Tensor shape:",
        expected_shape
    )

    print(
        "Sequence file:",
        GRU_TRAIN_SEQUENCE_FILE
    )

    print(
        "Label file:",
        GRU_TRAIN_LABEL_FILE
    )

    print(
        "Metadata file:",
        GRU_TRAIN_METADATA_FILE
    )

    print(
        "\n============================================"
    )
    print(
        "GRU TRAIN SEQUENCE STORE PASSED"
    )
    print(
        "============================================"
    )


if __name__ == "__main__":
    main()