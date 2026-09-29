"""
DC-Guardian Predictive Maintenance
Seven-Day Labeling Contract Test
"""

import pandas as pd

from phase1.predictive_maintenance.src.labeling import (
    build_failure_registry,
    label_drive_days,
)


print(
    "\n============================================"
)
print(
    "DC-GUARDIAN MAINTENANCE LABELING TEST"
)
print(
    "============================================"
)


# ============================================================
# Synthetic explicit failure events
# ============================================================

failure_events = pd.DataFrame(
    [
        {
            "date": "2026-03-20",
            "serial_number": "DRV-FAIL-001",
            "model": "TEST-DRIVE",
            "failure": 1,
        },

        # Duplicate later failure record.
        # Registry must retain first failure.
        {
            "date": "2026-03-21",
            "serial_number": "DRV-FAIL-001",
            "model": "TEST-DRIVE",
            "failure": 1,
        },
    ]
)


registry = build_failure_registry(
    failure_events
)


assert len(registry) == 1

assert (
    registry.iloc[0]["failure_date"]
    == pd.Timestamp("2026-03-20")
)


print(
    "PASS: First explicit failure date preserved."
)


# ============================================================
# Exercise all five evidence states
# ============================================================

observations = pd.DataFrame(
    [
        # More than seven days before failure.
        {
            "date": "2026-03-10",
            "serial_number": "DRV-FAIL-001",
        },

        # Exactly seven days before failure.
        {
            "date": "2026-03-13",
            "serial_number": "DRV-FAIL-001",
        },

        # One day before failure.
        {
            "date": "2026-03-19",
            "serial_number": "DRV-FAIL-001",
        },

        # Failure day.
        {
            "date": "2026-03-20",
            "serial_number": "DRV-FAIL-001",
        },

        # After failure.
        {
            "date": "2026-03-21",
            "serial_number": "DRV-FAIL-001",
        },

        # No failure and complete future horizon.
        {
            "date": "2026-03-20",
            "serial_number": "DRV-HEALTHY-001",
        },

        # No failure but insufficient future horizon.
        {
            "date": "2026-03-28",
            "serial_number": "DRV-HEALTHY-001",
        },
    ]
)


labeled = label_drive_days(
    observations=observations,
    failure_registry=registry,
    dataset_end_date="2026-03-31",
)


def state_for(
    serial_number,
    date,
):

    row = labeled[
        labeled["serial_number"].eq(
            serial_number
        )
        &
        labeled["date"].eq(
            pd.Timestamp(date)
        )
    ]

    assert len(row) == 1

    return row.iloc[0]


# NORMAL
row = state_for(
    "DRV-FAIL-001",
    "2026-03-10",
)

assert row["label_state"] == "NORMAL"
assert row["fail_within_7_days"] == 0

print(
    "PASS: NORMAL state."
)


# AT_RISK exactly seven days before failure
row = state_for(
    "DRV-FAIL-001",
    "2026-03-13",
)

assert row["label_state"] == "AT_RISK"
assert row["days_until_failure"] == 7
assert row["fail_within_7_days"] == 1

print(
    "PASS: AT_RISK at seven-day boundary."
)


# AT_RISK one day before failure
row = state_for(
    "DRV-FAIL-001",
    "2026-03-19",
)

assert row["label_state"] == "AT_RISK"
assert row["days_until_failure"] == 1
assert row["fail_within_7_days"] == 1

print(
    "PASS: AT_RISK one day before failure."
)


# FAILURE_DAY
row = state_for(
    "DRV-FAIL-001",
    "2026-03-20",
)

assert row["label_state"] == "FAILURE_DAY"
assert pd.isna(
    row["fail_within_7_days"]
)

print(
    "PASS: FAILURE_DAY excluded."
)


# POST_FAILURE
row = state_for(
    "DRV-FAIL-001",
    "2026-03-21",
)

assert row["label_state"] == "POST_FAILURE"
assert pd.isna(
    row["fail_within_7_days"]
)

print(
    "PASS: POST_FAILURE excluded."
)


# Healthy observation with complete horizon
row = state_for(
    "DRV-HEALTHY-001",
    "2026-03-20",
)

assert row["label_state"] == "NORMAL"
assert row["fail_within_7_days"] == 0

print(
    "PASS: Healthy complete-horizon observation."
)


# Right-censored healthy observation
row = state_for(
    "DRV-HEALTHY-001",
    "2026-03-28",
)

assert row["label_state"] == "CENSORED"
assert pd.isna(
    row["fail_within_7_days"]
)

print(
    "PASS: Right-censored observation excluded."
)


print(
    "\n============================================"
)
print(
    "MAINTENANCE LABELING CONTRACT PASSED"
)
print(
    "============================================"
)