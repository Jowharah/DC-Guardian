"""
DC-Guardian Phase 2
PPE Topology Mapper Contract Test
"""

from copy import deepcopy
from pathlib import Path
import json
import sys


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

ADAPTER_DIR = (
    PROJECT_ROOT
    / "reasoning"
    / "adapters"
)

TOPOLOGY_DIR = (
    PROJECT_ROOT
    / "reasoning"
    / "topology"
)


for directory in [
    ADAPTER_DIR,
    TOPOLOGY_DIR,
]:

    if str(directory) not in sys.path:

        sys.path.insert(
            0,
            str(directory)
        )


from ppe_event_adapter import (
    adapt_ppe_assessment,
)

from topology_mapper import (
    map_ppe_event_to_scenario,
)


# ============================================================
# Controlled Phase 1 PPE assessment
# ============================================================

assessment = {
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
        True,

    "person_count":
        2,

    "overall_status":
        "NON_COMPLIANT",

    "people": [
        {
            "person_index":
                0,

            "status":
                "COMPLIANT",

            "required_ppe": [
                "helmet",
                "safety-vest",
            ],

            "required_ppe_detected": [
                "helmet",
                "safety-vest",
            ],

            "required_ppe_not_detected":
                [],

            "optional_ppe_detected":
                [],

            "all_associated_classes": [
                "helmet",
                "safety-vest",
            ],
        },

        {
            "person_index":
                1,

            "status":
                "NON_COMPLIANT",

            "required_ppe": [
                "helmet",
                "safety-vest",
            ],

            "required_ppe_detected": [
                "helmet",
            ],

            "required_ppe_not_detected": [
                "safety-vest",
            ],

            "optional_ppe_detected":
                [],

            "all_associated_classes": [
                "helmet",
            ],
        },
    ],

    "detections":
        [],

    "unassigned_detections":
        [],

    "latency_ms":
        100.0,
}


# ============================================================
# Normalize
# ============================================================

common_event = adapt_ppe_assessment(
    assessment,

    dataset_name=
        "DC-Guardian Phase 2 Controlled Contract Test",

    source_type=
        "CONTROLLED_TEST",

    event_id=
        "EVT-PPE-TOPOLOGY-001",

    timestamp=
        "2026-09-27T09:00:00Z",
)


original_event = deepcopy(
    common_event
)


# ============================================================
# Map
# ============================================================

mapped_event = map_ppe_event_to_scenario(
    common_event,

    scenario_id=
        "SCENARIO-PPE-TOPOLOGY-001",

    scenario_timestamp=
        "2026-09-27T09:05:00Z",

    camera_id=
        "CAM-B-01",
)


print(
    "\n============================================"
)
print(
    "DC-GUARDIAN PPE TOPOLOGY TEST"
)
print(
    "============================================"
)


# ============================================================
# Camera topology
# ============================================================

assert (
    mapped_event[
        "entities"
    ][
        "camera_id"
    ]
    == "CAM-B-01"
)

assert (
    mapped_event[
        "location"
    ][
        "zone_id"
    ]
    == "ZONE-B"
)

assert (
    mapped_event[
        "location"
    ][
        "access_point_id"
    ]
    == "DOOR-B"
)


print(
    "PASS: PPE -> CAM-B-01 -> "
    "ZONE-B / DOOR-B mapping."
)


# ============================================================
# PPE state preserved
# ============================================================

assert (
    mapped_event[
        "assessment"
    ][
        "state"
    ]
    == "PPE_NON_COMPLIANT"
)

assert (
    mapped_event[
        "assessment"
    ][
        "anomaly_detected"
    ]
    is True
)


print(
    "PASS: PPE non-compliance state preserved."
)


# ============================================================
# Person-level evidence preserved
# ============================================================

assert (
    mapped_event[
        "evidence"
    ][
        "person_count"
    ]
    == 2
)

assert (
    mapped_event[
        "evidence"
    ][
        "people"
    ][0][
        "person_index"
    ]
    == 0
)

assert (
    mapped_event[
        "evidence"
    ][
        "people"
    ][1][
        "person_index"
    ]
    == 1
)

assert (
    mapped_event[
        "evidence"
    ][
        "people"
    ][1][
        "required_ppe_not_detected"
    ]
    == [
        "safety-vest"
    ]
)


print(
    "PASS: Person-level PPE evidence preserved."
)


# ============================================================
# person_index != employee identity
# ============================================================

assert (
    mapped_event[
        "entities"
    ][
        "person_id"
    ]
    is None
)


print(
    "PASS: person_index not promoted "
    "to employee identity."
)


# ============================================================
# Authorization deferred
# ============================================================

assert (
    mapped_event[
        "evidence"
    ][
        "authorization_evaluated"
    ]
    is False
)


print(
    "PASS: Mapper did not evaluate authorization."
)


# ============================================================
# Point-in-time timestamp
# ============================================================

assert (
    mapped_event[
        "timestamp"
    ]
    == "2026-09-27T09:05:00Z"
)

assert (
    mapped_event[
        "window"
    ][
        "start"
    ]
    == "2026-09-27T09:05:00Z"
)

assert (
    mapped_event[
        "window"
    ][
        "end"
    ]
    == "2026-09-27T09:05:00Z"
)


print(
    "PASS: Point-in-time PPE scenario timestamp applied."
)


# ============================================================
# Topology provenance
# ============================================================

assert (
    mapped_event[
        "evidence"
    ][
        "topology_resolution"
    ][
        "mapping_source"
    ]
    == "DECLARED_TOPOLOGY"
)

assert (
    mapped_event[
        "evidence"
    ][
        "topology_resolution"
    ][
        "camera_id"
    ]
    == "CAM-B-01"
)


print(
    "PASS: Camera monitoring provenance preserved."
)


# ============================================================
# Mapping provenance
# ============================================================

assert (
    mapped_event[
        "provenance"
    ][
        "synthetic_mapping"
    ]
    is True
)

assert (
    mapped_event[
        "provenance"
    ][
        "mapping_type"
    ]
    == "SYNTHETIC_SCENARIO"
)

assert (
    mapped_event[
        "provenance"
    ][
        "scenario_id"
    ]
    == "SCENARIO-PPE-TOPOLOGY-001"
)

assert (
    mapped_event[
        "provenance"
    ][
        "original_event_id"
    ]
    == "EVT-PPE-TOPOLOGY-001"
)


print(
    "PASS: PPE mapping provenance preserved."
)


# ============================================================
# Original event immutable
# ============================================================

assert (
    common_event
    == original_event
)


print(
    "PASS: Original normalized event unchanged."
)


# ============================================================
# Remapping protection
# ============================================================

try:

    map_ppe_event_to_scenario(
        mapped_event,

        scenario_id=
            "SCENARIO-PPE-TOPOLOGY-002",

        scenario_timestamp=
            "2026-09-27T09:10:00Z",

        camera_id=
            "CAM-B-01",
    )

except ValueError:

    print(
        "PASS: PPE remapping rejected."
    )

else:

    raise AssertionError(
        "Mapped PPE event was remapped."
    )


# ============================================================
# Unknown camera protection
# ============================================================

try:

    map_ppe_event_to_scenario(
        common_event,

        scenario_id=
            "SCENARIO-PPE-TOPOLOGY-BAD-CAMERA",

        scenario_timestamp=
            "2026-09-27T09:10:00Z",

        camera_id=
            "CAM-DOES-NOT-EXIST",
    )

except ValueError:

    print(
        "PASS: Unknown PPE camera rejected."
    )

else:

    raise AssertionError(
        "Unknown PPE camera was accepted."
    )


# ============================================================
# Summary
# ============================================================

print(
    "\n============================================"
)
print(
    "PPE TOPOLOGY CONTRACT SUMMARY"
)
print(
    "============================================"
)

print(
    "PASS: SAFETY event mapping."
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
    "PASS: PPE state preserved."
)

print(
    "PASS: Person-level evidence preserved."
)

print(
    "PASS: No synthetic employee identity."
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
    "PPE TOPOLOGY CONTRACT PASSED"
)
print(
    "============================================"
)
