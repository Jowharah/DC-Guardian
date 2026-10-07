"""
DC-Guardian Evidence
Predictive Maintenance GRU Sequence Builder

Constructs fixed-length chronological SMART sequences.

Each valid sample contains:
    30 consecutive daily observations
    x
    8 common SMART channels

The target belongs to the final observation in the sequence.

No future SMART observations are included in model input.
"""

import numpy as np
import pandas as pd

from evidence.predictive_maintenance.src.gru.config import (
    GRU_REQUIRE_CONSECUTIVE_DAYS,
    GRU_SEQUENCE_LENGTH,
    GRU_SMART_FEATURES,
)


REQUIRED_COLUMNS = {
    "date",
    "serial_number",
    "fail_within_7_days",
    *GRU_SMART_FEATURES,
}


def validate_sequence_input(
    observations: pd.DataFrame,
) -> None:
    """
    Validate the minimum sequence-building contract.
    """

    missing = (
        REQUIRED_COLUMNS
        - set(observations.columns)
    )

    if missing:
        raise ValueError(
            "Sequence input is missing required columns: "
            f"{sorted(missing)}"
        )

    if observations.empty:
        raise ValueError(
            "Sequence input cannot be empty."
        )


def _is_consecutive_daily(
    dates: pd.Series,
) -> bool:
    """
    Return True only when all observations are exactly
    one calendar day apart.
    """

    if len(dates) <= 1:
        return True

    differences = (
        dates
        .diff()
        .dropna()
        .dt.days
    )

    return bool(
        differences.eq(1).all()
    )


def build_sequence_index(
    observations: pd.DataFrame,
) -> pd.DataFrame:
    """
    Identify valid sequence endpoints without materializing
    the full 30 x 8 tensors.

    This keeps the sequence-selection stage lightweight.

    Returns one row per valid sequence with:
        serial_number
        endpoint_date
        label
        start_position
        end_position

    Positions refer to the sorted DataFrame returned by
    prepare_sequence_frame().
    """

    df = prepare_sequence_frame(
        observations
    )

    index_rows = []

    for serial_number, drive in df.groupby(
        "serial_number",
        sort=False,
    ):

        positions = drive.index.to_numpy()

        if len(drive) < GRU_SEQUENCE_LENGTH:
            continue

        for local_end in range(
            GRU_SEQUENCE_LENGTH - 1,
            len(drive),
        ):

            endpoint = drive.iloc[
                local_end
            ]

            # Only predictive rows may become sequence targets.
            if pd.isna(
                endpoint[
                    "fail_within_7_days"
                ]
            ):
                continue

            local_start = (
                local_end
                - GRU_SEQUENCE_LENGTH
                + 1
            )

            window = drive.iloc[
                local_start:
                local_end + 1
            ]

            if (
                GRU_REQUIRE_CONSECUTIVE_DAYS
                and
                not _is_consecutive_daily(
                    window["date"]
                )
            ):
                continue

            index_rows.append(
                {
                    "serial_number":
                        str(serial_number),

                    "endpoint_date":
                        endpoint[
                            "date"
                        ],

                    "label":
                        int(
                            endpoint[
                                "fail_within_7_days"
                            ]
                        ),

                    "start_position":
                        int(
                            positions[
                                local_start
                            ]
                        ),

                    "end_position":
                        int(
                            positions[
                                local_end
                            ]
                        ),
                }
            )

    return pd.DataFrame(
        index_rows,
        columns=[
            "serial_number",
            "endpoint_date",
            "label",
            "start_position",
            "end_position",
        ],
    )


def prepare_sequence_frame(
    observations: pd.DataFrame,
) -> pd.DataFrame:
    """
    Validate, normalize, and sort observations for
    deterministic sequence construction.
    """

    validate_sequence_input(
        observations
    )

    df = observations.copy()

    df["date"] = pd.to_datetime(
        df["date"],
        errors="raise",
    )

    for feature in GRU_SMART_FEATURES:

        df[feature] = pd.to_numeric(
            df[feature],
            errors="coerce",
        )

    df = (
        df
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

    return df


def materialize_sequence(
    prepared_frame: pd.DataFrame,
    start_position: int,
    end_position: int,
) -> np.ndarray:
    """
    Materialize one sequence as float32.

    Expected output shape:
        (GRU_SEQUENCE_LENGTH, number_of_SMART_features)
    """

    window = prepared_frame.iloc[
        start_position:
        end_position + 1
    ]

    if len(window) != GRU_SEQUENCE_LENGTH:

        raise ValueError(
            "Sequence does not contain exactly "
            f"{GRU_SEQUENCE_LENGTH} observations."
        )

    serial_count = (
        window[
            "serial_number"
        ]
        .nunique()
    )

    if serial_count != 1:

        raise ValueError(
            "Sequence crosses drive boundaries."
        )

    if (
        GRU_REQUIRE_CONSECUTIVE_DAYS
        and
        not _is_consecutive_daily(
            window["date"]
        )
    ):

        raise ValueError(
            "Sequence contains non-consecutive dates."
        )

    sequence = (
        window[
            GRU_SMART_FEATURES
        ]
        .to_numpy(
            dtype=np.float32
        )
    )

    expected_shape = (
        GRU_SEQUENCE_LENGTH,
        len(
            GRU_SMART_FEATURES
        ),
    )

    if sequence.shape != expected_shape:

        raise RuntimeError(
            "Unexpected GRU sequence shape: "
            f"{sequence.shape}; "
            f"expected {expected_shape}."
        )

    return sequence

def build_sequence_index_fast(
    observations: pd.DataFrame,
) -> pd.DataFrame:
    """
    Vectorized sequence-index builder for large datasets.

    A valid sequence endpoint must:
        - have a predictive target
        - have 29 preceding observations for the same drive
        - contain exactly 30 observations
        - have every adjacent observation exactly one day apart

    No future SMART observations are used.
    """

    df = prepare_sequence_frame(
        observations
    )

    grouped = df.groupby(
        "serial_number",
        sort=False,
    )


    # ========================================================
    # Position within each drive
    # ========================================================

    drive_position = (
        grouped
        .cumcount()
    )


    enough_history = (
        drive_position
        >= (
            GRU_SEQUENCE_LENGTH
            - 1
        )
    )


    # ========================================================
    # Daily continuity
    # ========================================================
    #
    # Each row is True only if it is exactly one day after
    # the previous observation for the SAME drive.
    # ========================================================

    previous_date = (
        grouped["date"]
        .shift(1)
    )


    daily_step = (
        (
            df["date"]
            - previous_date
        )
        .dt.days
        .eq(1)
    )


    # ========================================================
    # Require 29 consecutive one-day transitions
    #
    # A 30-observation sequence contains 29 transitions.
    # ========================================================

    consecutive_transition_count = (
        daily_step
        .astype("int8")
        .groupby(
            df["serial_number"],
            sort=False,
        )
        .rolling(
            window=(
                GRU_SEQUENCE_LENGTH
                - 1
            ),
            min_periods=(
                GRU_SEQUENCE_LENGTH
                - 1
            ),
        )
        .sum()
        .reset_index(
            level=0,
            drop=True,
        )
    )


    consecutive_history = (
        consecutive_transition_count
        .eq(
            GRU_SEQUENCE_LENGTH
            - 1
        )
    )


    # ========================================================
    # Endpoint must have a valid predictive target
    # ========================================================

    predictive_target = (
        df[
            "fail_within_7_days"
        ]
        .notna()
    )


    valid = (
        enough_history
        &
        consecutive_history
        &
        predictive_target
    )


    # ========================================================
    # Global row positions
    # ========================================================

    end_positions = np.flatnonzero(
        valid.to_numpy()
    )


    start_positions = (
        end_positions
        - (
            GRU_SEQUENCE_LENGTH
            - 1
        )
    )


    # ========================================================
    # Sequence index
    # ========================================================

    result = pd.DataFrame(
        {
            "serial_number":
                df.loc[
                    valid,
                    "serial_number",
                ]
                .astype(str)
                .to_numpy(),

            "endpoint_date":
                df.loc[
                    valid,
                    "date",
                ]
                .to_numpy(),

            "label":
                df.loc[
                    valid,
                    "fail_within_7_days",
                ]
                .astype(int)
                .to_numpy(),

            "start_position":
                start_positions,

            "end_position":
                end_positions,
        }
    )


    return result
