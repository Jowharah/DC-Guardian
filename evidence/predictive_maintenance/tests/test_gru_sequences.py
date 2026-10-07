"""
DC-Guardian Predictive Maintenance
GRU Sequence Builder Contract Test
"""

import numpy as np
import pandas as pd

from evidence.predictive_maintenance.src.gru.config import (
    GRU_SEQUENCE_LENGTH,
    GRU_SMART_FEATURES,
)

from evidence.predictive_maintenance.src.gru.sequence_builder import (
    build_sequence_index,
    materialize_sequence,
    prepare_sequence_frame,
)

from evidence.predictive_maintenance.src.gru.sequence_builder import (
    build_sequence_index,
    build_sequence_index_fast,
    materialize_sequence,
    prepare_sequence_frame,
)

print(
    "\n============================================"
)
print(
    "DC-GUARDIAN GRU SEQUENCE TEST"
)
print(
    "============================================"
)


def make_drive(
    serial_number,
    start_date,
    days,
    positive_last=False,
):

    dates = pd.date_range(
        start_date,
        periods=days,
        freq="D",
    )

    df = pd.DataFrame(
        {
            "date":
                dates,

            "serial_number":
                [serial_number] * days,

            "fail_within_7_days":
                [0] * days,

            "smart_5_raw":
                np.arange(
                    days
                ),

            "smart_9_raw":
                (
                    1000
                    +
                    np.arange(days)
                    * 24
                ),

            "smart_192_raw":
                [10] * days,

            "smart_193_raw":
                (
                    100
                    +
                    np.arange(days)
                ),

            "smart_194_raw":
                [32] * days,

            "smart_198_raw":
                [0] * days,

            "smart_4_raw":
                [5] * days,

            "smart_12_raw":
                [5] * days,
        }
    )

    if positive_last:

        df.loc[
            df.index[-1],
            "fail_within_7_days",
        ] = 1

    return df


# ============================================================
# Exactly 30 observations
# ============================================================

drive_30 = make_drive(
    "DRV-30",
    "2025-04-01",
    30,
    positive_last=True,
)


index_30 = build_sequence_index(
    drive_30
)


assert len(index_30) == 1

assert (
    index_30.iloc[0]["label"]
    == 1
)

print(
    "PASS: Exactly 30 observations "
    "produce one sequence."
)


prepared_30 = prepare_sequence_frame(
    drive_30
)


sequence = materialize_sequence(
    prepared_30,
    int(
        index_30.iloc[0][
            "start_position"
        ]
    ),
    int(
        index_30.iloc[0][
            "end_position"
        ]
    ),
)


assert sequence.shape == (
    GRU_SEQUENCE_LENGTH,
    len(GRU_SMART_FEATURES),
)

assert sequence.dtype == np.float32


print(
    "PASS: Sequence shape is 30 x 8."
)


# First SMART 5 = 0
assert sequence[0, 0] == 0

# Final SMART 5 = 29
assert sequence[-1, 0] == 29


print(
    "PASS: Chronological SMART order preserved."
)


# ============================================================
# 31 observations -> two endpoints
# ============================================================

drive_31 = make_drive(
    "DRV-31",
    "2025-05-01",
    31,
)


index_31 = build_sequence_index(
    drive_31
)


assert len(index_31) == 2


print(
    "PASS: Sliding sequence endpoints created."
)


# ============================================================
# Less than 30 observations -> no sequence
# ============================================================

drive_short = make_drive(
    "DRV-SHORT",
    "2025-06-01",
    29,
)


index_short = build_sequence_index(
    drive_short
)


assert len(index_short) == 0


print(
    "PASS: Insufficient history rejected."
)


# ============================================================
# Gap in history
# ============================================================

drive_gap = make_drive(
    "DRV-GAP",
    "2025-07-01",
    30,
)


drive_gap.loc[
    drive_gap.index[15],
    "date",
] = (
    drive_gap.loc[
        drive_gap.index[15],
        "date",
    ]
    + pd.Timedelta(
        days=3
    )
)


index_gap = build_sequence_index(
    drive_gap
)


assert len(index_gap) == 0


print(
    "PASS: Non-consecutive history rejected."
)


# ============================================================
# Never cross drive boundaries
# ============================================================

drive_a = make_drive(
    "DRV-A",
    "2025-08-01",
    20,
)

drive_b = make_drive(
    "DRV-B",
    "2025-08-01",
    20,
)


combined = pd.concat(
    [
        drive_a,
        drive_b,
    ],
    ignore_index=True,
)


combined_index = build_sequence_index(
    combined
)


assert len(combined_index) == 0


print(
    "PASS: Histories never cross drive boundaries."
)


# ============================================================
# Endpoint label contract
# ============================================================

drive_label = make_drive(
    "DRV-LABEL",
    "2025-09-01",
    30,
)


drive_label.loc[
    drive_label.index[-1],
    "fail_within_7_days",
] = 1


label_index = build_sequence_index(
    drive_label
)


assert (
    label_index.iloc[0]["label"]
    == 1
)


print(
    "PASS: Target comes from sequence endpoint."
)

# ============================================================
# Fast builder must reproduce reference builder
# ============================================================

reference_index = build_sequence_index(
    drive_31
).reset_index(
    drop=True
)

fast_index = build_sequence_index_fast(
    drive_31
).reset_index(
    drop=True
)


pd.testing.assert_frame_equal(
    reference_index,
    fast_index,
    check_dtype=False,
)


reference_gap = build_sequence_index(
    drive_gap
)

fast_gap = build_sequence_index_fast(
    drive_gap
)


assert len(reference_gap) == 0
assert len(fast_gap) == 0


print(
    "PASS: Vectorized sequence builder "
    "matches reference implementation."
)

print(
    "\n============================================"
)
print(
    "GRU SEQUENCE CONTRACT PASSED"
)
print(
    "============================================"
)
