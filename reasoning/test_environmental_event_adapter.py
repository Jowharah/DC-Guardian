from pathlib import Path
import json
import sys

from jsonschema import (
    Draft202012Validator,
    FormatChecker,
)


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


if str(ADAPTER_DIR) not in sys.path:

    sys.path.insert(
        0,
        str(ADAPTER_DIR)
    )


from environmental_event_adapter import (
    adapt_environmental_assessment,
)


SCHEMA_FILE = (
    PROJECT_ROOT
    / "shared"
    / "schemas"
    / "event_schema.json"
)


with open(
    SCHEMA_FILE,
    "r",
    encoding="utf-8",
) as file:

    schema = json.load(file)


validator = Draft202012Validator(
    schema,
    format_checker=FormatChecker(),
)


def build_assessment(
    *,
    source_class,
    source_id,
    source_asset_type,
):

    return {
        "domain":
            "ENVIRONMENTAL",

        "event_type":
            "ENVIRONMENTAL_CONDITION_ASSESSMENT",

        "component":
            "environmental_detector",

        "component_version":
            "1.0",

        "source_class":
            source_class,

        "source_id":
            source_id,

        "source_asset_type":
            source_asset_type,

        "observation_timestamp":
            "2026-09-18T12:03:00Z",

        "assessment":
            "HIGH_TEMPERATURE",

        "anomaly_detected":
            True,

        "measurements": {
            "temperature_c":
                42.5,

            "humidity_pct":
                48.0,
        },

        "evidence": {
            "triggered_conditions": [
                "HIGH_TEMPERATURE"
            ],

            "measurements": {
                "temperature_c":
                    42.5,

                "humidity_pct":
                    48.0,
            },

            "thresholds": {
                "temperature_high_c":
                    35.0,
            },
        },
    }


cases = [
    (
        "SENSOR",
        build_assessment(
            source_class=
                "ENVIRONMENTAL_SENSOR",

            source_id=
                "SEN-B-01",

            source_asset_type=
                "ENVIRONMENTAL_SENSOR",
        ),
    ),

    (
        "HARD_DRIVE",
        build_assessment(
            source_class=
                "HARDWARE_TELEMETRY",

            source_id=
                "DRV-ENV-001",

            source_asset_type=
                "HARD_DRIVE",
        ),
    ),

    (
        "SERVER",
        build_assessment(
            source_class=
                "HARDWARE_TELEMETRY",

            source_id=
                "SRV-B1-01",

            source_asset_type=
                "SERVER",
        ),
    ),

    (
        "COOLING_SYSTEM",
        build_assessment(
            source_class=
                "HARDWARE_TELEMETRY",

            source_id=
                "CHILLER-C1",

            source_asset_type=
                "COOLING_SYSTEM",
        ),
    ),
]


print(
    "\n============================================"
)
print(
    "DC-GUARDIAN ENVIRONMENTAL ADAPTER TEST"
)
print(
    "============================================"
)


passed = 0


for index, (
    name,
    assessment,
) in enumerate(
    cases,
    start=1,
):

    event = adapt_environmental_assessment(
        assessment,

        dataset_name=
            "DC-Guardian Environmental "
            "Contract Test",

        source_type=
            "CONTROLLED_TEST",

        event_id=
            f"EVT-ENV-TEST-{index:03d}",
    )


    errors = list(
        validator.iter_errors(
            event
        )
    )


    if errors:

        print(
            f"\nFAIL: {name}"
        )

        for error in errors:
            print(
                error.message
            )

        continue


    assert (
        event["domain"]
        == "ENVIRONMENTAL"
    )

    assert (
        event[
            "assessment"
        ][
            "state"
        ]
        == "HIGH_TEMPERATURE"
    )

    assert (
        event[
            "provenance"
        ][
            "synthetic_mapping"
        ]
        is False
    )


    if name == "SENSOR":

        assert (
            event[
                "entities"
            ][
                "sensor_id"
            ]
            == "SEN-B-01"
        )

        assert (
            event[
                "entities"
            ][
                "asset_id"
            ]
            is None
        )


    elif name == "HARD_DRIVE":

        assert (
            event[
                "entities"
            ][
                "asset_id"
            ]
            == "DRV-ENV-001"
        )

        assert (
            event[
                "entities"
            ][
                "server_id"
            ]
            is None
        )


    elif name == "SERVER":

        assert (
            event[
                "entities"
            ][
                "asset_id"
            ]
            == "SRV-B1-01"
        )

        assert (
            event[
                "entities"
            ][
                "server_id"
            ]
            == "SRV-B1-01"
        )


    elif name == "COOLING_SYSTEM":

        assert (
            event[
                "entities"
            ][
                "equipment_id"
            ]
            == "CHILLER-C1"
        )


    print(
        f"PASS: {name}"
    )


    passed += 1


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
    f"Passed: {passed}/{len(cases)}"
)


if passed != len(cases):

    raise SystemExit(
        "Environmental adapter "
        "contract failed."
    )


print(
    "\nPASS: Sensor identity preserved."
)

print(
    "PASS: Hardware identity preserved."
)

print(
    "PASS: Source provenance preserved."
)

print(
    "PASS: No synthetic topology introduced."
)


print(
    "\n============================================"
)
print(
    "ENVIRONMENTAL REASONING LAYER ADAPTER "
    "CONTRACT PASSED"
)
print(
    "============================================"
)
