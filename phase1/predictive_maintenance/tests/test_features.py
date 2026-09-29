"""
DC-Guardian Predictive Maintenance
Temporal Feature Engineering Contract Test
"""

import pandas as pd

from phase1.predictive_maintenance.src.config import (
    TEMPORAL_RF_FEATURES,
)

from phase1.predictive_maintenance.src.feature_engineering import (
    build_temporal_features,
)


print(
    "\n============================================"
)
print(
    "DC-GUARDIAN MAINTENANCE FEATURE TEST"
)
print(
    "============================================"
)


# ============================================================
# Synthetic 10-day drive history
# ============================================================

dates = pd.date_range(
    "2026-01-01",
    periods=10,
    freq="D",
)


observations = pd.DataFrame(
    {
        "date":
            dates,

        "serial_number":
            ["DRV-001"] * 10,

        # Reallocated sectors increase on day 8.
        "smart_5_raw":
            [
                0, 0, 0, 0, 0,
                0, 0, 5, 5, 5,
            ],

        "smart_9_raw":
            [
                100, 124, 148, 172, 196,
                220, 244, 268, 292, 316,
            ],

        "smart_192_raw":
            [
                1, 1, 1, 1, 1,
                1, 1, 1, 1, 1,
            ],

        "smart_193_raw":
            [
                10, 11, 12, 13, 14,
                15, 16, 17, 18, 19,
            ],

        "smart_194_raw":
            [
                30, 30, 30, 30, 30,
                30, 30, 35, 34, 33,
            ],

        # Offline uncorrectable increases on day 9.
        "smart_198_raw":
            [
                0, 0, 0, 0, 0,
                0, 0, 0, 2, 2,
            ],

        "smart_4_raw":
            [
                5, 5, 5, 5, 5,
                5, 5, 5, 5, 5,
            ],

        "smart_12_raw":
            [
                5, 5, 5, 5, 5,
                5, 5, 5, 5, 5,
            ],
    }
)


featured = build_temporal_features(
    observations
)


# ============================================================
# Contract completeness
# ============================================================

assert len(
    TEMPORAL_RF_FEATURES
) == 33


for feature in TEMPORAL_RF_FEATURES:

    assert feature in featured.columns


print(
    "PASS: All 33 Temporal RF features created."
)


# ============================================================
# Row preservation
# ============================================================

assert len(featured) == len(observations)

print(
    "PASS: Input rows preserved."
)


# ============================================================
# delta_1
# ============================================================

day_8 = featured.iloc[7]

assert (
    day_8["smart_5_raw_delta_1"]
    == 5
)

assert (
    day_8["smart_5_increased"]
    == 1
)

assert (
    day_8["smart_5_nonzero"]
    == 1
)


print(
    "PASS: SMART 5 one-observation change."
)


# ============================================================
# delta_7
#
# Day 8 SMART 5 = 5
# Day 1 SMART 5 = 0
# ============================================================

assert (
    day_8["smart_5_raw_delta_7"]
    == 5
)


print(
    "PASS: SMART 5 seven-observation change."
)


# ============================================================
# SMART 198 indicators
# ============================================================

day_9 = featured.iloc[8]

assert (
    day_9["smart_198_raw_delta_1"]
    == 2
)

assert (
    day_9["smart_198_nonzero"]
    == 1
)

assert (
    day_9["smart_198_increased"]
    == 1
)


print(
    "PASS: SMART 198 health indicators."
)


# ============================================================
# Power-on-hour change
# ============================================================

assert (
    day_8["smart_9_raw_delta_1"]
    == 24
)

assert (
    day_8["smart_9_raw_delta_7"]
    == 168
)


print(
    "PASS: SMART 9 temporal changes."
)


# ============================================================
# Temperature rolling window
#
# Day 8 window:
# 30,30,30,30,30,30,35
#
# mean = 215 / 7
# max = 35
# min = 30
# range = 5
# ============================================================

expected_mean = (
    215 / 7
)


assert abs(
    day_8[
        "temperature_7obs_mean"
    ]
    - expected_mean
) < 1e-9


assert (
    day_8[
        "temperature_7obs_max"
    ]
    == 35
)


assert (
    day_8[
        "temperature_7obs_min"
    ]
    == 30
)


assert (
    day_8[
        "temperature_7obs_range"
    ]
    == 5
)


assert abs(
    day_8[
        "temperature_vs_7obs_mean"
    ]
    - (
        35
        - expected_mean
    )
) < 1e-9


print(
    "PASS: Seven-observation temperature behavior."
)


# ============================================================
# Beginning-of-history behavior
# ============================================================

day_1 = featured.iloc[0]

assert pd.isna(
    day_1[
        "smart_5_raw_delta_1"
    ]
)

assert pd.isna(
    day_1[
        "smart_5_raw_delta_7"
    ]
)

assert pd.isna(
    day_1[
        "temperature_7obs_mean"
    ]
)


print(
    "PASS: Beginning-of-history missing values preserved."
)


print(
    "\n============================================"
)
print(
    "MAINTENANCE FEATURE CONTRACT PASSED"
)
print(
    "============================================"
)