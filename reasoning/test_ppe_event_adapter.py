"""
DC-Guardian Phase 2
PPE Event Adapter Contract Test

Validates frozen Phase 1 PPE assessments against the
DC-Guardian Common Event Schema v1.0.

Contract goals:
- all PPE states map to Common Event Schema v1.0
- PPE is normalized into the SAFETY domain
- person-level evidence is preserved
- required-PPE-not-detected semantics are preserved
- frozen detector/policy provenance is preserved
- no topology, employee identity, or authorization is invented
"""

from copy import deepcopy
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

if str(ADAPTER_DIR) not in sys.path:
    sys.path.insert(
        0,
        str(ADAPTER_DIR)
    )


from ppe_event_adapter import (
    adapt_ppe_assessment,
)


SCHEMA_FILE = (
    PROJECT_ROOT
    / "shared"
    / "schemas"
    / "event_schema.json"
)


# ============================================================
# Load Common Event Schema
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
# Helpers
# ============================================================

def make_assessment(
    status,
    people,
):
    """
    Build a controlled frozen Phase 1 PPE assessment.
    """

    return {
        "domain":
            "PHYSICAL_SECURITY",

        "event_type":
            "PPE_COMPLIANCE_ASSESSMENT",

        "model_family":
            "YOLOv8",

        "architecture":
            "YOLOv8n",

        "model_weights":
            "ppe_yolov8_best.pt",

        "detector_configuration":
            "PPE-v1",

        "detector_configuration_frozen":
            True,

        "policy_version":
            "PPE-POLICY-v1",

        "policy_name":
            "BASELINE_DC_MAINTENANCE",

        "policy_frozen":
            True,

        "policy_source":
            "project_defined_baseline",

        "required_ppe": [
            "helmet",
            "safety-vest",
        ],

        "confidence_threshold":
            0.25,

        "iou_threshold":
            0.70,

        "association_method":
            "object_containment",

        "association_minimum_containment":
            0.50,

        "person_assignment":
            "strongest_eligible_match",

        "person_detected":
            bool(
                people
            ),

        "person_count":
            len(
                people
            ),

        "overall_status":
            status,

        "people":
            people,

        "detections":
            [],

        "unassigned_detections":
            [],

        "latency_ms":
            100.0,
    }


def person(
    index,
    status,
    detected,
    not_detected,
):
    """
    Build controlled person-level PPE evidence.
    """

    return {
        "person_index":
            index,

        "status":
            status,

        "required_ppe": [
            "helmet",
            "safety-vest",
        ],

        "required_ppe_detected":
            detected,

        "required_ppe_not_detected":
            not_detected,

        "optional_ppe_detected":
            [],

        "all_associated_classes":
            list(
                detected
            ),
    }


def validate_common_event(
    event,
    case_name,
):
    """
    Validate one normalized event against Common Event
    Schema v1.0.
    """

    errors = sorted(
        validator.iter_errors(
            event
        ),
        key=lambda error: list(
            error.absolute_path
        ),
    )


    if errors:

        print(
            f"\nFAIL: {case_name}"
        )


        for error in errors:

            location = ".".join(
                str(item)
                for item
                in error.absolute_path
            )


            if not location:
                location = "<root>"


            print(
                f"  Field: {location}"
            )

            print(
                f"  Error: {error.message}"
            )


        raise AssertionError(
            f"{case_name} failed "
            "Common Event Schema v1.0."
        )


# ============================================================
# Controlled cases
# ============================================================

test_cases = [

    # --------------------------------------------------------
    # 1. COMPLIANT
    # --------------------------------------------------------

    {
        "name":
            "COMPLIANT",

        "event_id":
            "EVT-PPE-STATE-TEST-001",

        "timestamp":
            "2026-09-27T08:00:00Z",

        "assessment":
            make_assessment(
                "COMPLIANT",
                [
                    person(
                        0,
                        "COMPLIANT",
                        [
                            "helmet",
                            "safety-vest",
                        ],
                        [],
                    )
                ],
            ),

        "expected_state":
            "PPE_COMPLIANT",

        "expected_anomaly":
            False,
    },


    # --------------------------------------------------------
    # 2. NON_COMPLIANT
    # --------------------------------------------------------

    {
        "name":
            "NON_COMPLIANT",

        "event_id":
            "EVT-PPE-STATE-TEST-002",

        "timestamp":
            "2026-09-27T08:05:00Z",

        "assessment":
            make_assessment(
                "NON_COMPLIANT",
                [
                    person(
                        0,
                        "NON_COMPLIANT",
                        [
                            "helmet",
                        ],
                        [
                            "safety-vest",
                        ],
                    )
                ],
            ),

        "expected_state":
            "PPE_NON_COMPLIANT",

        "expected_anomaly":
            True,
    },


    # --------------------------------------------------------
    # 3. NO_PERSON
    # --------------------------------------------------------

    {
        "name":
            "NO_PERSON",

        "event_id":
            "EVT-PPE-STATE-TEST-003",

        "timestamp":
            "2026-09-27T08:10:00Z",

        "assessment":
            make_assessment(
                "NO_PERSON",
                [],
            ),

        "expected_state":
            "NO_PERSON_DETECTED",

        "expected_anomaly":
            False,
    },
]


# ============================================================
# Execute tests
# ============================================================

print(
    "\n============================================"
)
print(
    "DC-GUARDIAN PPE PHASE 2 ADAPTER TEST"
)
print(
    "============================================"
)


passed = 0


for test_case in test_cases:

    name = test_case[
        "name"
    ]

    evidence_assessment = test_case[
        "assessment"
    ]


    # Preserve original input for immutability test.
    snapshot = deepcopy(
        evidence_assessment
    )


    # --------------------------------------------------------
    # Phase 1 -> Phase 2
    # --------------------------------------------------------

    common_event = adapt_ppe_assessment(
        evidence_assessment,

        dataset_name=
            "DC-Guardian Phase 2 "
            "Controlled Contract Test",

        source_type=
            "CONTROLLED_TEST",

        event_id=
            test_case[
                "event_id"
            ],

        timestamp=
            test_case[
                "timestamp"
            ],
    )


    # --------------------------------------------------------
    # Common Event Schema v1.0
    # --------------------------------------------------------

    validate_common_event(
        common_event,
        name,
    )


    # --------------------------------------------------------
    # Common schema identity
    # --------------------------------------------------------

    assert (
        common_event[
            "event_id"
        ]
        == test_case[
            "event_id"
        ]
    )


    assert (
        common_event[
            "schema_version"
        ]
        == "1.0"
    )


    assert (
        common_event[
            "timestamp"
        ]
        == test_case[
            "timestamp"
        ]
    )


    assert (
        common_event[
            "window"
        ]
        is None
    )


    # --------------------------------------------------------
    # PPE is normalized into SAFETY
    # --------------------------------------------------------

    assert (
        common_event[
            "domain"
        ]
        == "SAFETY"
    )


    assert (
        common_event[
            "event_type"
        ]
        == "PPE_COMPLIANCE_ASSESSMENT"
    )


    # --------------------------------------------------------
    # Assessment semantics
    # --------------------------------------------------------

    assert (
        common_event[
            "assessment"
        ][
            "state"
        ]
        == test_case[
            "expected_state"
        ]
    )


    assert (
        common_event[
            "assessment"
        ][
            "anomaly_detected"
        ]
        == test_case[
            "expected_anomaly"
        ]
    )


    # PPE is a multi-object assessment.
    # No synthetic single confidence is invented.

    assert (
        common_event[
            "assessment"
        ][
            "confidence"
        ]
        is None
    )


    assert (
        common_event[
            "assessment"
        ][
            "score"
        ]
        is None
    )


    # --------------------------------------------------------
    # Person evidence
    # --------------------------------------------------------

    assert (
        common_event[
            "evidence"
        ][
            "person_count"
        ]
        == evidence_assessment[
            "person_count"
        ]
    )


    assert (
        common_event[
            "evidence"
        ][
            "person_detected"
        ]
        == evidence_assessment[
            "person_detected"
        ]
    )


    assert (
        common_event[
            "evidence"
        ][
            "people"
        ]
        == evidence_assessment[
            "people"
        ]
    )


    assert (
        common_event[
            "evidence"
        ][
            "required_ppe"
        ]
        == [
            "helmet",
            "safety-vest",
        ]
    )


    # --------------------------------------------------------
    # Frozen detector provenance
    # --------------------------------------------------------

    assert (
        common_event[
            "evidence"
        ][
            "detector_configuration"
        ]
        == "PPE-v1"
    )


    assert (
        common_event[
            "evidence"
        ][
            "detector_configuration_frozen"
        ]
        is True
    )


    assert (
        common_event[
            "evidence"
        ][
            "model_family"
        ]
        == "YOLOv8"
    )


    assert (
        common_event[
            "evidence"
        ][
            "architecture"
        ]
        == "YOLOv8n"
    )


    assert (
        common_event[
            "evidence"
        ][
            "model_weights"
        ]
        == "ppe_yolov8_best.pt"
    )


    assert (
        common_event[
            "evidence"
        ][
            "confidence_threshold"
        ]
        == 0.25
    )


    assert (
        common_event[
            "evidence"
        ][
            "iou_threshold"
        ]
        == 0.70
    )


    # --------------------------------------------------------
    # Frozen association provenance
    # --------------------------------------------------------

    assert (
        common_event[
            "evidence"
        ][
            "association_method"
        ]
        == "object_containment"
    )


    assert (
        common_event[
            "evidence"
        ][
            "association_minimum_containment"
        ]
        == 0.50
    )


    assert (
        common_event[
            "evidence"
        ][
            "person_assignment"
        ]
        == "strongest_eligible_match"
    )


    # --------------------------------------------------------
    # Frozen policy provenance
    # --------------------------------------------------------

    assert (
        common_event[
            "evidence"
        ][
            "policy_version"
        ]
        == "PPE-POLICY-v1"
    )


    assert (
        common_event[
            "evidence"
        ][
            "policy_name"
        ]
        == "BASELINE_DC_MAINTENANCE"
    )


    assert (
        common_event[
            "evidence"
        ][
            "policy_frozen"
        ]
        is True
    )


    assert (
        common_event[
            "evidence"
        ][
            "policy_source"
        ]
        == "project_defined_baseline"
    )


    # --------------------------------------------------------
    # Detection-vs-absence semantics
    # --------------------------------------------------------

    semantics = (
        common_event[
            "evidence"
        ][
            "required_ppe_not_detected_semantics"
        ]
    )


    assert (
        "does not prove physical absence"
        in semantics
    )


    # --------------------------------------------------------
    # State-specific checks
    # --------------------------------------------------------

    if name == "COMPLIANT":

        assert (
            common_event[
                "evidence"
            ][
                "people"
            ][0][
                "required_ppe_detected"
            ]
            == [
                "helmet",
                "safety-vest",
            ]
        )


        assert (
            common_event[
                "evidence"
            ][
                "people"
            ][0][
                "required_ppe_not_detected"
            ]
            == []
        )


    elif name == "NON_COMPLIANT":

        assert (
            common_event[
                "evidence"
            ][
                "people"
            ][0][
                "required_ppe_detected"
            ]
            == [
                "helmet",
            ]
        )


        assert (
            common_event[
                "evidence"
            ][
                "people"
            ][0][
                "required_ppe_not_detected"
            ]
            == [
                "safety-vest",
            ]
        )


    elif name == "NO_PERSON":

        assert (
            common_event[
                "evidence"
            ][
                "person_count"
            ]
            == 0
        )


        assert (
            common_event[
                "evidence"
            ][
                "people"
            ]
            == []
        )


    # --------------------------------------------------------
    # Identity deliberately deferred
    # --------------------------------------------------------

    assert (
        common_event[
            "entities"
        ][
            "person_id"
        ]
        is None
    )


    # --------------------------------------------------------
    # Camera/topology deliberately deferred
    # --------------------------------------------------------

    assert (
        common_event[
            "entities"
        ][
            "camera_id"
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
            "location"
        ][
            "access_point_id"
        ]
        is None
    )


    # --------------------------------------------------------
    # Authorization deliberately deferred
    # --------------------------------------------------------

    assert (
        common_event[
            "evidence"
        ][
            "authorization_evaluated"
        ]
        is False
    )


    assert (
        common_event[
            "evidence"
        ][
            "employee_identity_evaluated"
        ]
        is False
    )


    # --------------------------------------------------------
    # Provenance
    # --------------------------------------------------------

    assert (
        common_event[
            "provenance"
        ][
            "source_type"
        ]
        == "CONTROLLED_TEST"
    )


    assert (
        common_event[
            "provenance"
        ][
            "dataset_name"
        ]
        ==
        "DC-Guardian Phase 2 "
        "Controlled Contract Test"
    )


    assert (
        common_event[
            "provenance"
        ][
            "synthetic_mapping"
        ]
        is False
    )


    assert (
        common_event[
            "provenance"
        ][
            "mapping_type"
        ]
        == "NONE"
    )


    assert (
        common_event[
            "provenance"
        ][
            "scenario_id"
        ]
        is None
    )


    # --------------------------------------------------------
    # Input immutability
    # --------------------------------------------------------

    assert (
        evidence_assessment
        == snapshot
    )


    print(
        f"\nPASS: {name}"
    )

    print(
        "  Event ID:",
        common_event[
            "event_id"
        ],
    )

    print(
        "  Domain:",
        common_event[
            "domain"
        ],
    )

    print(
        "  State:",
        common_event[
            "assessment"
        ][
            "state"
        ],
    )

    print(
        "  Persons:",
        common_event[
            "evidence"
        ][
            "person_count"
        ],
    )

    print(
        "  Anomaly:",
        common_event[
            "assessment"
        ][
            "anomaly_detected"
        ],
    )


    passed += 1


# ============================================================
# Final result
# ============================================================

print(
    "\n============================================"
)
print(
    "PPE ADAPTER CONTRACT SUMMARY"
)
print(
    "============================================"
)

print(
    f"Passed: {passed}/{len(test_cases)}"
)


if passed != len(
    test_cases
):

    raise SystemExit(
        "One or more PPE adapter tests failed."
    )


print(
    "PASS: Common Event Schema v1.0."
)

print(
    "PASS: SAFETY domain normalization."
)

print(
    "PASS: COMPLIANT state preserved."
)

print(
    "PASS: NON_COMPLIANT state preserved."
)

print(
    "PASS: NO_PERSON state preserved."
)

print(
    "PASS: Person-level PPE evidence preserved."
)

print(
    "PASS: Required-PPE-not-detected semantics preserved."
)

print(
    "PASS: Frozen detector provenance preserved."
)

print(
    "PASS: Frozen association provenance preserved."
)

print(
    "PASS: Frozen policy provenance preserved."
)

print(
    "PASS: Camera/topology deferred."
)

print(
    "PASS: Employee identity deferred."
)

print(
    "PASS: Authorization deferred."
)

print(
    "PASS: Original Phase 1 assessments immutable."
)


print(
    "\n============================================"
)
print(
    "PPE PHASE 2 ADAPTER CONTRACT PASSED"
)
print(
    "============================================"
)


