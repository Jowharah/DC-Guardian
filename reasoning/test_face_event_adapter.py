"""
DC-Guardian Reasoning layer
Face Recognition Event Adapter Contract Test
"""

import json
from pathlib import Path
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


for directory in [
    PROJECT_ROOT,
    PROJECT_ROOT / "reasoning" / "adapters",
]:

    if str(directory) not in sys.path:

        sys.path.insert(
            0,
            str(directory)
        )


from evidence.face_recognition.src.config import (
    TEST_KNOWN_DIR,
    TEST_UNKNOWN_DIR,
)

from evidence.face_recognition.src.face_pipeline import (
    FaceRecognitionPipeline,
)

from face_event_adapter import (
    adapt_face_assessment,
)


# ============================================================
# Common Event Schema
# ============================================================

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

    schema = json.load(
        file
    )


validator = Draft202012Validator(
    schema,
    format_checker=FormatChecker(),
)


def validate_common_event(
    event,
):

    errors = sorted(
        validator.iter_errors(
            event
        ),
        key=lambda error:
            list(
                error.path
            ),
    )


    if errors:

        messages = []


        for error in errors:

            path = ".".join(
                str(
                    part
                )
                for part
                in error.path
            )


            messages.append(
                f"{path or '<root>'}: "
                f"{error.message}"
            )


        raise AssertionError(
            "Common Event Schema validation failed:\n"
            +
            "\n".join(
                messages
            )
        )

print(
    "\n============================================"
)

print(
    "DC-GUARDIAN FACE REASONING LAYER ADAPTER TEST"
)

print(
    "============================================"
)


# ============================================================
# Initialize frozen Evidence layer face pipeline
# ============================================================

pipeline = FaceRecognitionPipeline()


assert (
    pipeline.threshold
    == 0.50
)


print(
    "PASS: Frozen Evidence layer face pipeline loaded."
)


# ============================================================
# 1. Recognized person
# ============================================================

known_assessment = pipeline.recognize(
    TEST_KNOWN_DIR
    / "P001"
    / "P001_test_01.jpg"
)


known_event = adapt_face_assessment(
    known_assessment,

    dataset_name=
        "DC-Guardian Controlled Face Dataset v1",

    source_type=
        "CONTROLLED_TEST",

    event_id=
        "EVT-FACE-ADAPTER-001",

    timestamp=
        "2026-09-24T12:00:00Z",
)


validate_common_event(
    known_event
)


assert (
    known_event[
        "domain"
    ]
    == "PHYSICAL_SECURITY"
)

assert (
    known_event[
        "event_type"
    ]
    == "FACE_IDENTIFICATION_ASSESSMENT"
)

assert (
    known_event[
        "entities"
    ][
        "person_id"
    ]
    == "P001"
)

assert (
    known_event[
        "assessment"
    ][
        "state"
    ]
    == "RECOGNIZED_PERSON"
)

assert (
    known_event[
        "assessment"
    ][
        "anomaly_detected"
    ]
    is False
)

assert (
    known_event[
        "entities"
    ][
        "camera_id"
    ]
    is None
)

assert (
    known_event[
        "location"
    ][
        "zone_id"
    ]
    is None
)

assert (
    known_event[
        "evidence"
    ][
        "authorization_evaluated"
    ]
    is False
)


print(
    "PASS: RECOGNIZED face mapped."
)

print(
    "PASS: P001 identity preserved."
)

print(
    "PASS: Recognition does not imply authorization."
)


# ============================================================
# 2. Unknown person
# ============================================================

unknown_assessment = pipeline.recognize(
    TEST_UNKNOWN_DIR
    / "U005"
    / "U005_test_02.jpg"
)


unknown_event = adapt_face_assessment(
    unknown_assessment,

    dataset_name=
        "DC-Guardian Controlled Face Dataset v1",

    source_type=
        "CONTROLLED_TEST",

    event_id=
        "EVT-FACE-ADAPTER-002",

    timestamp=
        "2026-09-24T12:01:00Z",
)


validate_common_event(
    unknown_event
)


assert (
    unknown_event[
        "entities"
    ][
        "person_id"
    ]
    == "UNKNOWN"
)

assert (
    unknown_event[
        "assessment"
    ][
        "state"
    ]
    == "UNKNOWN_PERSON"
)

assert (
    unknown_event[
        "assessment"
    ][
        "anomaly_detected"
    ]
    is True
)

assert (
    unknown_event[
        "evidence"
    ][
        "nearest_employee_id"
    ]
    == "P003"
)

assert (
    unknown_event[
        "evidence"
    ][
        "distance"
    ]
    > 0.50
)


print(
    "PASS: UNKNOWN face mapped."
)

print(
    "PASS: Unknown person marked as "
    "physical-security anomaly evidence."
)


# ============================================================
# 3. No synthetic topology
# ============================================================

for event in [
    known_event,
    unknown_event,
]:

    assert (
        event[
            "provenance"
        ][
            "synthetic_mapping"
        ]
        is False
    )

    assert (
        event[
            "provenance"
        ][
            "mapping_type"
        ]
        == "NONE"
    )

    assert (
        event[
            "provenance"
        ][
            "scenario_id"
        ]
        is None
    )

    assert (
        event[
            "entities"
        ][
            "camera_id"
        ]
        is None
    )


print(
    "PASS: Adapter introduced no synthetic topology."
)


# ============================================================
# Summary
# ============================================================

print(
    "\n============================================"
)

print(
    "FACE ADAPTER CONTRACT SUMMARY"
)

print(
    "============================================"
)

print(
    "PASS: Common Event Schema v1.0."
)

print(
    "PASS: Recognized identity preserved."
)

print(
    "PASS: Unknown identity preserved."
)

print(
    "PASS: Face evidence preserved."
)

print(
    "PASS: Authorization deferred to Reasoning layer."
)

print(
    "PASS: Camera/topology deferred to mapper."
)


print(
    "\n============================================"
)

print(
    "FACE REASONING LAYER ADAPTER CONTRACT PASSED"
)

print(
    "============================================"
)

