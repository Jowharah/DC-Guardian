"""
DC-Guardian Phase 1
Predictive Maintenance Labeling

Creates the forward-looking seven-day failure-risk target.

States:
    NORMAL
    AT_RISK
    FAILURE_DAY
    POST_FAILURE
    CENSORED
"""

import pandas as pd

from phase1.predictive_maintenance.src.config import (
    FAILURE_HORIZON_DAYS,
)


VALID_LABEL_STATES = {
    "NORMAL",
    "AT_RISK",
    "FAILURE_DAY",
    "POST_FAILURE",
    "CENSORED",
}


def build_failure_registry(
    events: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build one explicit failure date per drive.

    If a drive has multiple recorded failure rows,
    the first explicit failure date is retained.
    """

    required = {
        "date",
        "serial_number",
        "model",
        "failure",
    }

    missing = (
        required
        - set(events.columns)
    )

    if missing:
        raise ValueError(
            "Missing required columns: "
            f"{sorted(missing)}"
        )

    df = events.copy()

    df["date"] = pd.to_datetime(
        df["date"],
        errors="raise",
    )

    failed = df[
        df["failure"].eq(1)
    ].copy()

    registry = (
        failed
        .sort_values(
            [
                "serial_number",
                "date",
            ]
        )
        .groupby(
            "serial_number",
            as_index=False,
        )
        .agg(
            failure_date=(
                "date",
                "first",
            ),
            drive_model=(
                "model",
                "first",
            ),
        )
    )

    return registry


def label_drive_days(
    observations: pd.DataFrame,
    failure_registry: pd.DataFrame,
    dataset_end_date,
) -> pd.DataFrame:
    """
    Label drive-day observations for forward-looking
    failure prediction.

    AT_RISK:
        Explicit failure occurs 1..FAILURE_HORIZON_DAYS
        after the observation.

    FAILURE_DAY:
        Observation occurs on the explicit failure date.

    POST_FAILURE:
        Observation occurs after the first failure date.

    CENSORED:
        Future observation horizon extends beyond the
        available dataset and no known positive outcome
        occurs within that available horizon.

    NORMAL:
        Valid predictive observation with no explicit
        failure in the next prediction horizon.
    """

    required = {
        "date",
        "serial_number",
    }

    missing = (
        required
        - set(observations.columns)
    )

    if missing:
        raise ValueError(
            "Missing required columns: "
            f"{sorted(missing)}"
        )

    registry_required = {
        "serial_number",
        "failure_date",
    }

    registry_missing = (
        registry_required
        - set(failure_registry.columns)
    )

    if registry_missing:
        raise ValueError(
            "Failure registry missing columns: "
            f"{sorted(registry_missing)}"
        )

    df = observations.copy()

    df["date"] = pd.to_datetime(
        df["date"],
        errors="raise",
    )

    registry = failure_registry[
        [
            "serial_number",
            "failure_date",
        ]
    ].copy()

    registry["failure_date"] = pd.to_datetime(
        registry["failure_date"],
        errors="raise",
    )

    df = df.merge(
        registry,
        on="serial_number",
        how="left",
        validate="many_to_one",
    )

    df["days_until_failure"] = (
        df["failure_date"]
        - df["date"]
    ).dt.days

    dataset_end_date = pd.Timestamp(
        dataset_end_date
    )

    last_full_horizon_date = (
        dataset_end_date
        - pd.Timedelta(
            days=FAILURE_HORIZON_DAYS
        )
    )

    # Default valid predictive state.
    df["label_state"] = "NORMAL"

    # Dataset-end right censoring.
    df.loc[
        df["date"]
        > last_full_horizon_date,
        "label_state",
    ] = "CENSORED"

    # Known positives override censoring.
    at_risk_mask = (
        df["days_until_failure"]
        .between(
            1,
            FAILURE_HORIZON_DAYS,
        )
    )

    df.loc[
        at_risk_mask,
        "label_state",
    ] = "AT_RISK"

    # Failure-day observations are excluded.
    failure_day_mask = (
        df["days_until_failure"]
        .eq(0)
    )

    df.loc[
        failure_day_mask,
        "label_state",
    ] = "FAILURE_DAY"

    # Any observation after first failure is excluded.
    post_failure_mask = (
        df["days_until_failure"]
        .lt(0)
    )

    df.loc[
        post_failure_mask,
        "label_state",
    ] = "POST_FAILURE"

    # Binary target exists only for predictive rows.
    df["fail_within_7_days"] = pd.Series(
        pd.NA,
        index=df.index,
        dtype="Int8",
    )

    df.loc[
        df["label_state"].eq("NORMAL"),
        "fail_within_7_days",
    ] = 0

    df.loc[
        df["label_state"].eq("AT_RISK"),
        "fail_within_7_days",
    ] = 1

    return df