"""
DC-Guardian Predictive Maintenance
Frozen Detector Contract Test
"""

import json

import pandas as pd

from phase1.predictive_maintenance.src.config import (
    FAILURE_HORIZON_DAYS,
    RF_OPERATING_THRESHOLD,
)

from phase1.predictive_maintenance.src.maintenance_detector import (
    ASSESSMENT_AT_RISK,
    ASSESSMENT_NORMAL,
    assess_drive_health,
)


print(
    "\n============================================"
)
print(
    "DC-GUARDIAN MAINTENANCE DETECTOR TEST"
)
print(
    "============================================"
)


# ============================================================
# Synthetic 10-day SMART history
# ============================================================

dates = pd.date_range(
    "2026-01-01",
    periods=10,
    freq="D",
)


history = pd.DataFrame(
    {
        "date":
            dates,

        "serial_number":
            ["DRV-CONTRACT-001"] * 10,

        "smart_5_raw":
            [
                0, 0, 0, 0, 0,
                0, 0, 5, 10, 20,
            ],

        "smart_9_raw":
            [
                30000,
                30024,
                30048,
                30072,
                30096,
                30120,
                30144,
                30168,
                30192,
                30216,
            ],

        "smart_192_raw":
            [10] * 10,

        "smart_193_raw":
            [
                1000,
                1001,
                1002,
                1003,
                1004,
                1005,
                1006,
                1007,
                1008,
                1009,
            ],

        "smart_194_raw":
            [
                32, 32, 32, 33, 33,
                33, 34, 34, 35, 35,
            ],

        "smart_198_raw":
            [
                0, 0, 0, 0, 0,
                0, 0, 0, 1, 2,
            ],

        "smart_4_raw":
            [12] * 10,

        "smart_12_raw":
            [12] * 10,
    }
)


assessment = assess_drive_health(
    history
)


# ============================================================
# Contract validation
# ============================================================

required_fields = {
    "domain",
    "event_type",
    "model_name",
    "asset_type",
    "serial_number",
    "observation_timestamp",
    "assessment",
    "failure_probability",
    "operating_threshold",
    "failure_horizon_days",
    "evidence",
}


missing = (
    required_fields
    - set(
        assessment.keys()
    )
)


assert not missing, (
    f"Missing assessment fields: "
    f"{sorted(missing)}"
)


assert (
    assessment["domain"]
    == "MAINTENANCE"
)


assert (
    assessment["event_type"]
    == "STORAGE_FAILURE_RISK_ASSESSMENT"
)


assert (
    assessment["serial_number"]
    == "DRV-CONTRACT-001"
)


assert (
    assessment["failure_horizon_days"]
    == FAILURE_HORIZON_DAYS
)


assert (
    assessment["operating_threshold"]
    == RF_OPERATING_THRESHOLD
)


assert (
    0.0
    <= assessment[
        "failure_probability"
    ]
    <= 1.0
)


assert (
    assessment["assessment"]
    in {
        ASSESSMENT_NORMAL,
        ASSESSMENT_AT_RISK,
    }
)


# Must be JSON serializable.
json.dumps(
    assessment
)


print(
    "PASS: Frozen model loaded."
)

print(
    "PASS: SMART history converted to "
    "Temporal RF features."
)

print(
    "PASS: Failure probability generated."
)

print(
    "PASS: Threshold assessment generated."
)

print(
    "PASS: Phase 1 assessment contract complete."
)

print(
    "PASS: Assessment is JSON serializable."
)


print(
    "\n--------------------------------------------"
)

print(
    "Serial number:",
    assessment[
        "serial_number"
    ]
)

print(
    "Assessment:",
    assessment[
        "assessment"
    ]
)

print(
    "Failure probability:",
    f"{assessment['failure_probability']:.6f}"
)

print(
    "Threshold:",
    assessment[
        "operating_threshold"
    ]
)

print(
    "Horizon:",
    assessment[
        "failure_horizon_days"
    ],
    "days"
)


print(
    "\nEvidence:"
)

for key, value in (
    assessment[
        "evidence"
    ].items()
):

    print(
        f"  {key}: {value}"
    )


print(
    "\n============================================"
)
print(
    "MAINTENANCE DETECTOR CONTRACT PASSED"
)
print(
    "============================================"
)