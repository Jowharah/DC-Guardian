"""
DC-Guardian Predictive Maintenance
Detector Negative-Input Contract Test
"""

import pandas as pd

from phase1.predictive_maintenance.src.maintenance_detector import (
    assess_drive_health,
)


print(
    "\n============================================"
)
print(
    "DC-GUARDIAN MAINTENANCE NEGATIVE TEST"
)
print(
    "============================================"
)


def valid_history():

    return pd.DataFrame(
        {
            "date": pd.date_range(
                "2026-01-01",
                periods=8,
                freq="D",
            ),

            "serial_number":
                ["DRV-001"] * 8,

            "smart_5_raw":
                [0] * 8,

            "smart_9_raw":
                list(
                    range(
                        100,
                        108,
                    )
                ),

            "smart_192_raw":
                [1] * 8,

            "smart_193_raw":
                list(
                    range(
                        10,
                        18,
                    )
                ),

            "smart_194_raw":
                [32] * 8,

            "smart_198_raw":
                [0] * 8,

            "smart_4_raw":
                [5] * 8,

            "smart_12_raw":
                [5] * 8,
        }
    )


# ============================================================
# Empty history
# ============================================================

empty = valid_history().iloc[0:0]


try:

    assess_drive_health(
        empty
    )

    raise AssertionError(
        "Empty history was not rejected."
    )

except ValueError as error:

    assert (
        "cannot be empty"
        in str(error)
    )


print(
    "PASS: Empty history rejected."
)


# ============================================================
# Missing SMART feature
# ============================================================

missing_feature = (
    valid_history()
    .drop(
        columns=[
            "smart_198_raw"
        ]
    )
)


try:

    assess_drive_health(
        missing_feature
    )

    raise AssertionError(
        "Missing SMART feature "
        "was not rejected."
    )

except ValueError as error:

    assert (
        "smart_198_raw"
        in str(error)
    )


print(
    "PASS: Missing SMART feature rejected."
)


# ============================================================
# Multiple drives
# ============================================================

multiple_drives = (
    valid_history()
)


multiple_drives.loc[
    multiple_drives.index[-1],
    "serial_number",
] = "DRV-002"


try:

    assess_drive_health(
        multiple_drives
    )

    raise AssertionError(
        "Multiple-drive history "
        "was not rejected."
    )

except ValueError as error:

    assert (
        "exactly one drive"
        in str(error)
    )


print(
    "PASS: Multiple-drive history rejected."
)


# ============================================================
# Invalid date
# ============================================================
# ============================================================
# Invalid date
# ============================================================

invalid_date = (
    valid_history()
)


# Convert date column to object so the test can deliberately
# inject a malformed timestamp.
invalid_date[
    "date"
] = invalid_date[
    "date"
].astype(
    object
)


invalid_date.loc[
    invalid_date.index[-1],
    "date",
] = "NOT-A-DATE"


try:

    assess_drive_health(
        invalid_date
    )

    raise AssertionError(
        "Invalid date was not rejected."
    )

except (
    ValueError,
    TypeError,
):

    pass


print(
    "PASS: Invalid timestamp rejected."
)


print(
    "\n============================================"
)
print(
    "MAINTENANCE NEGATIVE CONTRACT PASSED"
)
print(
    "============================================"
)