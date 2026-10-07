from pathlib import Path
import json
import sys

from jsonschema import (
    Draft202012Validator,
    FormatChecker,
)


# ============================================================
# Project paths
# ============================================================

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)


ADAPTER_DIR = (
    PROJECT_ROOT
    / "reasoning"
    / "adapters"
)


if str(
    ADAPTER_DIR
) not in sys.path:

    sys.path.insert(
        0,
        str(
            ADAPTER_DIR
        )
    )


from maintenance_event_adapter import (
    adapt_maintenance_assessment,
)


SCHEMA_FILE = (
    PROJECT_ROOT
    / "shared"
    / "schemas"
    / "event_schema.json"
)


# ============================================================
# Schema
# ============================================================

with open(
    SCHEMA_FILE,
    "r",
    encoding="utf-8",
) as file:

    schema = json.load(
        file
    )


validator = Draft202012Validator(
    schema,
    format_checker=FormatChecker(),
)


# ============================================================
# Representative Evidence layer assessment
# ============================================================

def build_maintenance_assessment(
    *,
    serial_number,
    timestamp,
    assessment,
    probability,
):

    return {
        "domain":
            "MAINTENANCE",

        "event_type":
            "STORAGE_FAILURE_RISK_ASSESSMENT",

        "model_name":
            "DC_Guardian_Temporal_RF_v2",

        "asset_type":
            "HARD_DRIVE",

        "serial_number":
            serial_number,

        "observation_timestamp":
            timestamp,

        "assessment":
            assessment,

        "failure_probability":
            probability,

        "operating_threshold":
            0.45,

        "failure_horizon_days":
            7,

        "evidence": {
            "smart_5_raw":
                20.0,

            "smart_198_raw":
                2.0,

            "smart_194_raw":
                35.0,

            "smart_5_delta_7":
                20.0,

            "smart_198_delta_7":
                2.0,

            "temperature_7obs_mean":
                33.8571428571,
        },
    }


# ============================================================
# Cases
# ============================================================

test_cases = [
    {
        "name":
            "AT_RISK",

        "assessment":
            build_maintenance_assessment(
                serial_number=
                    "DRV-MAINT-001",

                timestamp=
                    "2026-09-16T14:00:00Z",

                assessment=
                    "AT_RISK",

                probability=
                    0.714008,
            ),

        "expected_anomaly":
            True,
    },

    {
        "name":
            "NORMAL",

        "assessment":
            build_maintenance_assessment(
                serial_number=
                    "DRV-MAINT-002",

                timestamp=
                    "2026-09-16T14:05:00Z",

                assessment=
                    "NORMAL",

                probability=
                    0.120000,
            ),

        "expected_anomaly":
            False,
    },
]


# ============================================================
# Execute
# ============================================================

print(
    "\n============================================"
)

print(
    "MAINTENANCE REASONING LAYER ADAPTER TEST"
)

print(
    "============================================"
)


passed = 0


for index, test_case in enumerate(
    test_cases,
    start=1,
):

    assessment = (
        test_case[
            "assessment"
        ]
    )


    event_id = (
        f"EVT-MAINT-STATE-TEST-{index:03d}"
    )


    common_event = (
        adapt_maintenance_assessment(
            assessment,

            dataset_name=
                "DC-Guardian Reasoning layer "
                "Controlled Contract Test",

            source_type=
                "CONTROLLED_TEST",

            event_id=
                event_id,
        )
    )


    # ========================================================
    # JSON Schema
    # ========================================================

    errors = sorted(
        validator.iter_errors(
            common_event
        ),
        key=lambda error: list(
            error.absolute_path
        ),
    )


    if errors:

        print(
            f"\nFAIL: "
            f"{test_case['name']}"
        )

        for error in errors:

            location = ".".join(
                str(item)
                for item
                in error.absolute_path
            )

            if not location:

                location = (
                    "<root>"
                )

            print(
                f"  Field: {location}"
            )

            print(
                f"  Error: {error.message}"
            )

        continue


    # ========================================================
    # Semantic contract
    # ========================================================

    assert (
        common_event[
            "domain"
        ]
        == "MAINTENANCE"
    )


    assert (
        common_event[
            "event_type"
        ]
        == "STORAGE_FAILURE_RISK_ASSESSMENT"
    )


    assert (
        common_event[
            "assessment"
        ][
            "state"
        ]
        == test_case[
            "name"
        ]
    )


    assert (
        common_event[
            "assessment"
        ][
            "score"
        ]
        == assessment[
            "failure_probability"
        ]
    )


    assert (
        common_event[
            "assessment"
        ][
            "anomaly_detected"
        ]
        is test_case[
            "expected_anomaly"
        ]
    )


    assert (
        common_event[
            "entities"
        ][
            "asset_id"
        ]
        == assessment[
            "serial_number"
        ]
    )


    assert (
        common_event[
            "evidence"
        ][
            "failure_horizon_days"
        ]
        == 7
    )


    assert (
        common_event[
            "evidence"
        ][
            "operating_threshold"
        ]
        == 0.45
    )


    # ========================================================
    # No invented topology
    # ========================================================

    assert (
        common_event[
            "entities"
        ][
            "server_id"
        ]
        is None
    )


    assert (
        common_event[
            "entities"
        ][
            "equipment_id"
        ]
        is None
    )


    assert (
        common_event[
            "location"
        ][
            "data_center_id"
        ]
        is None
    )


    assert (
        common_event[
            "location"
        ][
            "zone_id"
        ]
        is None
    )


    assert (
        common_event[
            "location"
        ][
            "rack_id"
        ]
        is None
    )


    assert (
        common_event[
            "provenance"
        ][
            "synthetic_mapping"
        ]
        is False
    )


    print(
        f"\nPASS: "
        f"{test_case['name']}"
    )


    print(
        "  Event ID:",
        common_event[
            "event_id"
        ]
    )


    print(
        "  Asset:",
        common_event[
            "entities"
        ][
            "asset_id"
        ]
    )


    print(
        "  Score:",
        common_event[
            "assessment"
        ][
            "score"
        ]
    )


    print(
        "  Anomaly detected:",
        common_event[
            "assessment"
        ][
            "anomaly_detected"
        ]
    )


    passed += 1


# ============================================================
# Final
# ============================================================

print(
    "\n============================================"
)

print(
    "TEST SUMMARY"
)

print(
    "============================================"
)


print(
    f"Passed: "
    f"{passed}/{len(test_cases)}"
)


if passed != len(
    test_cases
):

    raise SystemExit(
        "One or more maintenance adapter "
        "tests failed."
    )


print(
    "\nPASS: Maintenance states map "
    "to DC-Guardian schema v1.0."
)


print(
    "PASS: Drive serial preserved "
    "as asset identity."
)


print(
    "PASS: Adapter introduced no "
    "synthetic topology."
)


print(
    "\n============================================"
)

print(
    "MAINTENANCE REASONING LAYER ADAPTER CONTRACT PASSED"
)

print(
    "============================================"
)
