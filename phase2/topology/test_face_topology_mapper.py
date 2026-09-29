"""
DC-Guardian Phase 2
Face Recognition Topology Mapper Contract Test
"""

from copy import deepcopy
import json
from pathlib import Path
import sys

from jsonschema import (
    Draft202012Validator,
    FormatChecker,
)


# ============================================================
# Paths
# ============================================================

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)


for directory in [
    PROJECT_ROOT,
    PROJECT_ROOT / "phase2" / "adapters",
    PROJECT_ROOT / "phase2" / "topology",
]:

    if str(directory) not in sys.path:

        sys.path.insert(
            0,
            str(directory)
        )


from face_event_adapter import (
    adapt_face_assessment,
)

from topology_mapper import (
    map_face_event_to_scenario,
)


SCHEMA_FILE = (
    PROJECT_ROOT
    / "shared"
    / "schemas"
    / "event_schema.json"
)


with SCHEMA_FILE.open(
    "r",
    encoding="utf-8",
) as file:

    schema = json.load(file)


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

        messages = [
            (
                ".".join(
                    str(part)
                    for part
                    in error.path
                )
                or "<root>"
            )
            + ": "
            + error.message

            for error
            in errors
        ]


        raise AssertionError(
            "Common Event Schema validation failed:\n"
            +
            "\n".join(
                messages
            )
        )


# ============================================================
# Controlled Phase 1-style assessments
# ============================================================

def make_recognized_assessment(
    person_id,
):

    return {
        "domain":
            "PHYSICAL_SECURITY",

        "event_type":
            "FACE_IDENTIFICATION_ASSESSMENT",

        "image":
            f"{person_id}_controlled.jpg",

        "model_name":
            "ArcFace",

        "detector_backend":
            "retinaface",

        "distance_metric":
            "cosine",

        "threshold":
            0.50,

        "threshold_source":
            "validation_only",

        "configuration_frozen":
            True,

        "person_id":
            person_id,

        "recognition_status":
            "RECOGNIZED",

        "face_detected":
            True,

        "face_count":
            1,

        "distance":
            0.25,

        "similarity":
            0.75,

        "nearest_employee_id":
            person_id,

        "face_confidence":
            1.0,

        "facial_area":
            None,

        "latency_ms":
            100.0,
    }


def make_unknown_assessment():

    return {
        "domain":
            "PHYSICAL_SECURITY",

        "event_type":
            "FACE_IDENTIFICATION_ASSESSMENT",

        "image":
            "unknown_controlled.jpg",

        "model_name":
            "ArcFace",

        "detector_backend":
            "retinaface",

        "distance_metric":
            "cosine",

        "threshold":
            0.50,

        "threshold_source":
            "validation_only",

        "configuration_frozen":
            True,

        "person_id":
            "UNKNOWN",

        "recognition_status":
            "UNKNOWN",

        "face_detected":
            True,

        "face_count":
            1,

        "distance":
            0.80,

        "similarity":
            0.20,

        "nearest_employee_id":
            "P001",

        "face_confidence":
            1.0,

        "facial_area":
            None,

        "latency_ms":
            100.0,
    }


print(
    "\n============================================"
)
print(
    "DC-GUARDIAN FACE TOPOLOGY TEST"
)
print(
    "============================================"
)


# ============================================================
# Scenario 1 - P001 at CAM-B-01
# ============================================================

p001_event = adapt_face_assessment(
    make_recognized_assessment(
        "P001"
    ),

    dataset_name=
        "DC-Guardian Controlled Face Dataset v1",

    source_type=
        "CONTROLLED_TEST",

    event_id=
        "EVT-FACE-TOPO-P001",

    timestamp=
        "2026-09-24T12:00:00Z",
)


p001_original = deepcopy(
    p001_event
)


p001_mapped = (
    map_face_event_to_scenario(
        p001_event,

        scenario_id=
            "SCENARIO-FACE-P001-B",

        scenario_timestamp=
            "2026-09-24T13:00:00Z",

        camera_id=
            "CAM-B-01",
    )
)


validate_common_event(
    p001_mapped
)


assert (
    p001_mapped[
        "entities"
    ][
        "person_id"
    ]
    == "P001"
)

assert (
    p001_mapped[
        "entities"
    ][
        "camera_id"
    ]
    == "CAM-B-01"
)

assert (
    p001_mapped[
        "location"
    ][
        "data_center_id"
    ]
    == "DC-01"
)

assert (
    p001_mapped[
        "location"
    ][
        "zone_id"
    ]
    == "ZONE-B"
)

assert (
    p001_mapped[
        "location"
    ][
        "access_point_id"
    ]
    == "DOOR-B"
)

assert (
    p001_mapped[
        "location"
    ][
        "rack_id"
    ]
    is None
)

assert (
    p001_mapped[
        "evidence"
    ][
        "authorization_evaluated"
    ]
    is False
)


print(
    "PASS: P001 -> CAM-B-01 -> "
    "ZONE-B / DOOR-B mapping."
)

print(
    "PASS: Mapper did not evaluate authorization."
)


# ============================================================
# Scenario 2 - P003 at same camera
#
# Mapper behavior must be identical except identity.
# Authorization is NOT evaluated here.
# ============================================================

p003_event = adapt_face_assessment(
    make_recognized_assessment(
        "P003"
    ),

    dataset_name=
        "DC-Guardian Controlled Face Dataset v1",

    source_type=
        "CONTROLLED_TEST",

    event_id=
        "EVT-FACE-TOPO-P003",

    timestamp=
        "2026-09-24T12:01:00Z",
)


p003_mapped = (
    map_face_event_to_scenario(
        p003_event,

        scenario_id=
            "SCENARIO-FACE-P003-B",

        scenario_timestamp=
            "2026-09-24T13:01:00Z",

        camera_id=
            "CAM-B-01",
    )
)


validate_common_event(
    p003_mapped
)


assert (
    p003_mapped[
        "entities"
    ][
        "person_id"
    ]
    == "P003"
)

assert (
    p003_mapped[
        "location"
    ][
        "zone_id"
    ]
    == "ZONE-B"
)

assert (
    p003_mapped[
        "evidence"
    ][
        "authorization_evaluated"
    ]
    is False
)


print(
    "PASS: P003 maps to the same "
    "observation topology."
)

print(
    "PASS: Authorization mismatch not "
    "invented by mapper."
)


# ============================================================
# Scenario 3 - UNKNOWN at CAM-B-01
# ============================================================

unknown_event = adapt_face_assessment(
    make_unknown_assessment(),

    dataset_name=
        "DC-Guardian Controlled Face Dataset v1",

    source_type=
        "CONTROLLED_TEST",

    event_id=
        "EVT-FACE-TOPO-UNKNOWN",

    timestamp=
        "2026-09-24T12:02:00Z",
)


unknown_mapped = (
    map_face_event_to_scenario(
        unknown_event,

        scenario_id=
            "SCENARIO-FACE-UNKNOWN-B",

        scenario_timestamp=
            "2026-09-24T13:02:00Z",

        camera_id=
            "CAM-B-01",
    )
)


validate_common_event(
    unknown_mapped
)


assert (
    unknown_mapped[
        "entities"
    ][
        "person_id"
    ]
    == "UNKNOWN"
)

assert (
    unknown_mapped[
        "entities"
    ][
        "camera_id"
    ]
    == "CAM-B-01"
)

assert (
    unknown_mapped[
        "location"
    ][
        "zone_id"
    ]
    == "ZONE-B"
)

assert (
    unknown_mapped[
        "location"
    ][
        "access_point_id"
    ]
    == "DOOR-B"
)


print(
    "PASS: UNKNOWN identity preserved."
)

print(
    "PASS: UNKNOWN observation receives "
    "camera/location context only."
)


# ============================================================
# Immutability
# ============================================================

assert (
    p001_event
    == p001_original
)


print(
    "PASS: Original normalized event unchanged."
)


# ============================================================
# Provenance
# ============================================================

assert (
    p001_mapped[
        "provenance"
    ][
        "synthetic_mapping"
    ]
    is True
)

assert (
    p001_mapped[
        "provenance"
    ][
        "mapping_type"
    ]
    == "SYNTHETIC_SCENARIO"
)

assert (
    p001_mapped[
        "provenance"
    ][
        "original_event_id"
    ]
    == "EVT-FACE-TOPO-P001"
)

assert (
    p001_mapped[
        "provenance"
    ][
        "original_timestamp"
    ]
    == "2026-09-24T12:00:00Z"
)

assert (
    p001_mapped[
        "provenance"
    ][
        "scenario_id"
    ]
    == "SCENARIO-FACE-P001-B"
)


print(
    "PASS: Face mapping provenance preserved."
)


# ============================================================
# Point-in-time timestamp
# ============================================================

assert (
    p001_mapped[
        "timestamp"
    ]
    == "2026-09-24T13:00:00Z"
)

assert (
    p001_mapped[
        "window"
    ][
        "start"
    ]
    == "2026-09-24T13:00:00Z"
)

assert (
    p001_mapped[
        "window"
    ][
        "end"
    ]
    == "2026-09-24T13:00:00Z"
)


print(
    "PASS: Point-in-time face scenario "
    "timestamp applied."
)


# ============================================================
# Declared topology provenance
# ============================================================

resolution = (
    p001_mapped[
        "evidence"
    ][
        "topology_resolution"
    ]
)


assert (
    resolution[
        "mapping_source"
    ]
    == "DECLARED_TOPOLOGY"
)

assert (
    resolution[
        "camera_id"
    ]
    == "CAM-B-01"
)

assert set(
    resolution[
        "monitors"
    ]
) == {
    "ZONE-B",
    "DOOR-B",
}


print(
    "PASS: Camera monitoring provenance preserved."
)


# ============================================================
# Remapping protection
# ============================================================

try:

    map_face_event_to_scenario(
        p001_mapped,

        scenario_id=
            "SCENARIO-FACE-SECOND",

        scenario_timestamp=
            "2026-09-24T14:00:00Z",

        camera_id=
            "CAM-A-01",
    )


except ValueError as error:

    assert (
        "already contains"
        in str(
            error
        )
    )


else:

    raise AssertionError(
        "Mapped face event was allowed "
        "to be remapped."
    )


print(
    "PASS: Face remapping rejected."
)


# ============================================================
# Invalid camera protection
# ============================================================

try:

    map_face_event_to_scenario(
        p001_event,

        scenario_id=
            "SCENARIO-FACE-BAD-CAMERA",

        scenario_timestamp=
            "2026-09-24T14:00:00Z",

        camera_id=
            "CAM-NOT-REAL",
    )


except ValueError:

    pass


else:

    raise AssertionError(
        "Unknown camera was accepted."
    )


print(
    "PASS: Unknown camera rejected."
)


# ============================================================
# Summary
# ============================================================

print(
    "\n============================================"
)
print(
    "FACE TOPOLOGY CONTRACT SUMMARY"
)
print(
    "============================================"
)

print(
    "PASS: Declared camera topology."
)

print(
    "PASS: Camera -> Zone context."
)

print(
    "PASS: Camera -> Access Point context."
)

print(
    "PASS: Recognized identity preserved."
)

print(
    "PASS: UNKNOWN identity preserved."
)

print(
    "PASS: Authorization deferred."
)

print(
    "PASS: Mapping provenance preserved."
)

print(
    "PASS: Original event immutable."
)

print(
    "PASS: Remapping protection."
)


print(
    "\n============================================"
)
print(
    "FACE TOPOLOGY CONTRACT PASSED"
)
print(
    "============================================"
)