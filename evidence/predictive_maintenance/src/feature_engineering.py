"""
DC-Guardian Evidence
Predictive Maintenance Feature Engineering

Builds the frozen Temporal Random Forest v2 feature contract.

All temporal features use current or historical observations only.
No future observations are used.
"""

import pandas as pd

from evidence.predictive_maintenance.src.config import (
    BASE_SMART_FEATURES,
    TEMPORAL_RF_FEATURES,
)


def build_temporal_features(
    observations: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build temporal SMART features for each drive.

    Input rows are sorted by serial_number and date.

    Generated features:
        - Current SMART values
        - 1-observation deltas
        - 7-observation deltas
        - SMART 5 / SMART 198 health indicators
        - 7-observation temperature statistics

    The function preserves all original rows.
    """

    required = {
        "date",
        "serial_number",
        *BASE_SMART_FEATURES,
    }

    missing = (
        required
        - set(observations.columns)
    )

    if missing:
        raise ValueError(
            "Missing required feature columns: "
            f"{sorted(missing)}"
        )

    df = observations.copy()

    df["date"] = pd.to_datetime(
        df["date"],
        errors="raise",
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

    # ========================================================
    # Numeric SMART values
    # ========================================================

    for feature in BASE_SMART_FEATURES:

        df[feature] = pd.to_numeric(
            df[feature],
            errors="coerce",
        )

    grouped = df.groupby(
        "serial_number",
        sort=False,
    )

    # ========================================================
    # Temporal deltas
    # ========================================================

    for feature in BASE_SMART_FEATURES:

        df[
            f"{feature}_delta_1"
        ] = (
            df[feature]
            - grouped[feature].shift(1)
        )

        df[
            f"{feature}_delta_7"
        ] = (
            df[feature]
            - grouped[feature].shift(7)
        )

    # ========================================================
    # Explicit health indicators
    # ========================================================

    df["smart_5_nonzero"] = (
        df["smart_5_raw"]
        .fillna(0)
        .gt(0)
        .astype("int8")
    )

    df["smart_198_nonzero"] = (
        df["smart_198_raw"]
        .fillna(0)
        .gt(0)
        .astype("int8")
    )

    df["smart_5_increased"] = (
        df["smart_5_raw_delta_1"]
        .fillna(0)
        .gt(0)
        .astype("int8")
    )

    df["smart_198_increased"] = (
        df["smart_198_raw_delta_1"]
        .fillna(0)
        .gt(0)
        .astype("int8")
    )

    # ========================================================
    # Temperature history
    # ========================================================

    temperature_grouped = (
        df.groupby(
            "serial_number",
            sort=False,
        )["smart_194_raw"]
    )

    df["temperature_7obs_mean"] = (
        temperature_grouped
        .rolling(
            window=7,
            min_periods=2,
        )
        .mean()
        .reset_index(
            level=0,
            drop=True,
        )
    )

    df["temperature_7obs_max"] = (
        temperature_grouped
        .rolling(
            window=7,
            min_periods=2,
        )
        .max()
        .reset_index(
            level=0,
            drop=True,
        )
    )

    df["temperature_7obs_min"] = (
        temperature_grouped
        .rolling(
            window=7,
            min_periods=2,
        )
        .min()
        .reset_index(
            level=0,
            drop=True,
        )
    )

    df["temperature_7obs_range"] = (
        df["temperature_7obs_max"]
        - df["temperature_7obs_min"]
    )

    df["temperature_vs_7obs_mean"] = (
        df["smart_194_raw"]
        - df["temperature_7obs_mean"]
    )

    # ========================================================
    # Contract validation
    # ========================================================

    missing_output = (
        set(TEMPORAL_RF_FEATURES)
        - set(df.columns)
    )

    if missing_output:
        raise RuntimeError(
            "Feature engineering failed to produce: "
            f"{sorted(missing_output)}"
        )

    return df
