"""
DC-Guardian Phase 1
Predictive Maintenance Detector

Stable inference boundary for the frozen Temporal Random Forest v2.

The caller supplies chronological SMART history for one drive.
This module:

    SMART history
        -> temporal feature engineering
        -> frozen RF pipeline
        -> structured maintenance assessment

Phase 2 should consume the returned assessment rather than
interacting with the Random Forest directly.
"""

from functools import lru_cache

import joblib
import pandas as pd

from shared.model_integrity import verify_sha256

from phase1.predictive_maintenance.src.config import (
    BASE_SMART_FEATURES,
    FAILURE_HORIZON_DAYS,
    RF_MODEL_DIR,
    RF_OPERATING_THRESHOLD,
    TEMPORAL_RF_FEATURES,
)

from phase1.predictive_maintenance.src.feature_engineering import (
    build_temporal_features,
)


MODEL_FILE = (
    RF_MODEL_DIR
    / "temporal_rf_v2.joblib"
)

MODEL_NAME = (
    "DC_Guardian_Temporal_RF_v2"
)

# Git LFS object SHA-256 for the frozen RF artifact.
MODEL_SHA256 = (
    "40a66de944f76ee5fe5853bfc9fca20d9"
    "cd011cc1781c75ef7e9904bb1e7e88a"
)

ASSESSMENT_NORMAL = "NORMAL"

ASSESSMENT_AT_RISK = "AT_RISK"


@lru_cache(maxsize=1)
def load_model():
    """
    Load and cache the frozen RF pipeline.
    """

    if not MODEL_FILE.exists():

        raise FileNotFoundError(
            f"Maintenance model not found: "
            f"{MODEL_FILE}"
        )

    # joblib uses pickle-compatible deserialization. Verify the
    # frozen repository artifact before loading trusted model bytes.
    verify_sha256(
        MODEL_FILE,
        MODEL_SHA256,
    )

    return joblib.load(
        MODEL_FILE
    )


def validate_drive_history(
    drive_history: pd.DataFrame,
) -> None:
    """
    Validate the minimum inference contract.
    """

    required = {
        "date",
        "serial_number",
        *BASE_SMART_FEATURES,
    }

    missing = (
        required
        - set(drive_history.columns)
    )

    if missing:

        raise ValueError(
            "Drive history is missing required "
            f"columns: {sorted(missing)}"
        )


    if drive_history.empty:

        raise ValueError(
            "Drive history cannot be empty."
        )


    serial_count = (
        drive_history[
            "serial_number"
        ]
        .nunique(
            dropna=True
        )
    )


    if serial_count != 1:

        raise ValueError(
            "Inference requires history for "
            "exactly one drive."
        )


def assess_drive_health(
    drive_history: pd.DataFrame,
) -> dict:
    """
    Assess the most recent observation for one drive.

    Parameters
    ----------
    drive_history:
        Historical SMART observations for exactly one
        drive. The caller may provide more than seven
        observations; the latest observation is scored.

    Returns
    -------
    dict
        Stable Phase 1 maintenance assessment.
    """

    validate_drive_history(
        drive_history
    )


    history = (
        drive_history
        .copy()
    )


    history["date"] = pd.to_datetime(
        history["date"],
        errors="raise",
    )


    history = (
        history
        .sort_values(
            "date"
        )
        .reset_index(
            drop=True
        )
    )


    # ========================================================
    # Feature engineering
    # ========================================================

    featured = (
        build_temporal_features(
            history
        )
    )


    latest = (
        featured
        .iloc[[-1]]
        .copy()
    )


    # ========================================================
    # Frozen model inference
    # ========================================================

    pipeline = load_model()


    probability = float(
        pipeline
        .predict_proba(
            latest[
                TEMPORAL_RF_FEATURES
            ]
        )[0, 1]
    )


    if (
        probability
        >= RF_OPERATING_THRESHOLD
    ):

        assessment = (
            ASSESSMENT_AT_RISK
        )

    else:

        assessment = (
            ASSESSMENT_NORMAL
        )


    # ========================================================
    # Stable evidence payload
    # ========================================================

    serial_number = str(
        latest[
            "serial_number"
        ].iloc[0]
    )


    observation_date = (
        latest[
            "date"
        ]
        .iloc[0]
        .isoformat()
    )


    evidence = {
        "smart_5_raw":
            _safe_number(
                latest[
                    "smart_5_raw"
                ].iloc[0]
            ),

        "smart_198_raw":
            _safe_number(
                latest[
                    "smart_198_raw"
                ].iloc[0]
            ),

        "smart_194_raw":
            _safe_number(
                latest[
                    "smart_194_raw"
                ].iloc[0]
            ),

        "smart_5_delta_7":
            _safe_number(
                latest[
                    "smart_5_raw_delta_7"
                ].iloc[0]
            ),

        "smart_198_delta_7":
            _safe_number(
                latest[
                    "smart_198_raw_delta_7"
                ].iloc[0]
            ),

        "temperature_7obs_mean":
            _safe_number(
                latest[
                    "temperature_7obs_mean"
                ].iloc[0]
            ),
    }


    return {
        "domain":
            "MAINTENANCE",

        "event_type":
            "STORAGE_FAILURE_RISK_ASSESSMENT",

        "model_name":
            MODEL_NAME,

        "asset_type":
            "HARD_DRIVE",

        "serial_number":
            serial_number,

        "observation_timestamp":
            observation_date,

        "assessment":
            assessment,

        "failure_probability":
            probability,

        "operating_threshold":
            RF_OPERATING_THRESHOLD,

        "failure_horizon_days":
            FAILURE_HORIZON_DAYS,

        "evidence":
            evidence,
    }


def _safe_number(
    value,
):
    """
    Convert pandas/numpy numeric values to JSON-safe
    Python numbers while preserving missing values as None.
    """

    if pd.isna(
        value
    ):

        return None


    if isinstance(
        value,
        bool,
    ):

        return bool(
            value
        )


    try:

        return float(
            value
        )

    except (
        TypeError,
        ValueError,
    ):

        return value