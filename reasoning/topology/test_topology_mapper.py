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
    .parents[2]
)


TOPOLOGY_MODULE_DIR = (
    PROJECT_ROOT
    / "reasoning"
    / "topology"
)


if str(
    TOPOLOGY_MODULE_DIR
) not in sys.path:

    sys.path.insert(
        0,
        str(
            TOPOLOGY_MODULE_DIR
        )
    )


from topology_mapper import (
    map_ssh_event_to_scenario,
    validate_target_mapping,
    build_server_index,
)


SCHEMA_FILE = (
    PROJECT_ROOT
    / "shared"
    / "schemas"
    / "event_schema.json"
)


TOPOLOGY_FILE = (
    PROJECT_ROOT
    / "shared"
    / "topology"
    / "data_center_topology.json"
)


# ============================================================
# JSON loader
# ============================================================

def load_json(
    file_path
):

    with open(
        file_path,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(
            file
        )


# ============================================================
# Load schema
# ============================================================

schema = load_json(
    SCHEMA_FILE
)


validator = Draft202012Validator(
    schema,
    format_checker=FormatChecker()
)


# ============================================================
# Representative normalized SSH event
#
# This represents output AFTER the SSH adapter but BEFORE
# topology mapping.
# ============================================================

normalized_event = {

    "event_id":
        "EVT-SSH-MAP-TEST-001",

    "schema_version":
        "1.0",

    "timestamp":
        "2000-12-17T02:25:00Z",

    "window": {
        "start":
            "2000-12-17T02:25:00Z",

        "end":
            "2000-12-17T02:30:00Z",
    },

    "domain":
        "CYBERSECURITY",

    "event_type":
        "SSH_BEHAVIOR_ASSESSMENT",

    "source": {
        "component":
            "ssh_detector",

        "component_version":
            "1.0",

        "model_name":
            "SSH_HYBRID_V1",
    },

    "entities": {
        "person_id":
            None,

        "source_ip":
            "203.0.113.20",

        "asset_id":
            None,

        "server_id":
            None,

        "camera_id":
            None,

        "sensor_id":
            None,

        "equipment_id":
            None,
    },

    "location": {
        "data_center_id":
            None,

        "zone_id":
            None,

        "rack_id":
            None,

        "access_point_id":
            None,
    },

    "assessment": {
        "state":
            "HIGH_CONFIDENCE_ANOMALY",

        "confidence":
            "MEDIUM",

        "score":
            None,

        "anomaly_detected":
            True,
    },

    "evidence": {
        "detector_votes":
            2,

        "detector_combination":
            "RULE+AE",
    },

    "provenance": {
        "source_type":
            "CONTROLLED_TEST",

        "dataset_name":
            "DC-Guardian Mapper Test",

        "original_event_id":
            None,

        "synthetic_mapping":
            False,

        "mapping_type":
            "NONE",

        "original_timestamp":
            None,

        "scenario_id":
            None,
    },
}


# ============================================================
# Validate normalized input first
# ============================================================

input_errors = list(
    validator.iter_errors(
        normalized_event
    )
)


if input_errors:

    raise ValueError(
        "Normalized test event is "
        "invalid before mapping."
    )


print(
    "\n============================================"
)

print(
    "DC-GUARDIAN TOPOLOGY MAPPER TEST"
)

print(
    "============================================"
)


# ============================================================
# Test 1 - valid mapping
# ============================================================

original_copy = deepcopy(
    normalized_event
)


mapped_event = (
    map_ssh_event_to_scenario(
        normalized_event,

        scenario_id=
            "SCENARIO-001",

        scenario_timestamp=
            "2026-09-16T14:25:00Z",

        target_name=
            "ZONE_A_SERVER",
    )
)


mapped_errors = sorted(
    validator.iter_errors(
        mapped_event
    ),
    key=lambda error: list(
        error.absolute_path
    )
)


if mapped_errors:

    print(
        "\nFAIL: Mapped event does "
        "not match event schema."
    )

    for error in mapped_errors:

        location = ".".join(
            str(item)
            for item
            in error.absolute_path
        )

        print(
            f"Field: {location}"
        )

        print(
            f"Error: {error.message}"
        )

    raise SystemExit(1)


# ------------------------------------------------------------
# Expected topology
# ------------------------------------------------------------

assert (
    mapped_event[
        "entities"
    ][
        "server_id"
    ]
    == "SRV-A1-01"
)


assert (
    mapped_event[
        "entities"
    ][
        "asset_id"
    ]
    == "SRV-A1-01"
)


assert (
    mapped_event[
        "location"
    ][
        "rack_id"
    ]
    == "RACK-A1"
)


assert (
    mapped_event[
        "location"
    ][
        "zone_id"
    ]
    == "ZONE-A"
)


assert (
    mapped_event[
        "location"
    ][
        "data_center_id"
    ]
    == "DC-01"
)


# ------------------------------------------------------------
# Expected scenario time
# ------------------------------------------------------------

assert (
    mapped_event[
        "timestamp"
    ]
    == "2026-09-16T14:25:00Z"
)


assert (
    mapped_event[
        "window"
    ][
        "end"
    ]
    == "2026-09-16T14:30:00Z"
)


# ------------------------------------------------------------
# Expected provenance
# ------------------------------------------------------------

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
    == "SCENARIO-001"
)


assert (
    mapped_event[
        "provenance"
    ][
        "original_event_id"
    ]
    == "EVT-SSH-MAP-TEST-001"
)


assert (
    mapped_event[
        "provenance"
    ][
        "original_timestamp"
    ]
    == "2000-12-17T02:25:00Z"
)


# ------------------------------------------------------------
# Critical:
# original normalized event must remain unchanged.
# ------------------------------------------------------------

assert (
    normalized_event
    == original_copy
)


print(
    "\nPASS: Valid SSH scenario "
    "mapping accepted."
)

print(
    "PASS: Server -> rack -> zone -> "
    "data center relationship verified."
)

print(
    "PASS: 2026 synthetic scenario "
    "timestamp applied."
)

print(
    "PASS: Original event timestamp "
    "and event ID preserved."
)

print(
    "PASS: Original normalized event "
    "was not modified."
)

print(
    "PASS: Mapped event matches "
    "Common Event Schema v1.0."
)


# ============================================================
# Test 2 - invalid topology relationship
# ============================================================

topology = load_json(
    TOPOLOGY_FILE
)


server_index = (
    build_server_index(
        topology
    )
)


invalid_target = {
    "server_id":
        "SRV-A1-01",

    "rack_id":
        "RACK-B1",

    "zone_id":
        "ZONE-B",
}


invalid_rejected = False


try:

    validate_target_mapping(
        invalid_target,
        server_index,
        "DC-01"
    )

except ValueError as error:

    invalid_rejected = True

    print(
        "\nPASS: Invalid topology "
        "mapping rejected."
    )

    print(
        "  Rejection reason:"
    )

    print(
        f"  {error}"
    )


if not invalid_rejected:

    raise AssertionError(
        "Invalid topology mapping "
        "was incorrectly accepted."
    )


# ============================================================
# Test 3 - prevent accidental remapping
# ============================================================

remapping_rejected = False


try:

    map_ssh_event_to_scenario(
        mapped_event,

        scenario_id=
            "SCENARIO-002",

        scenario_timestamp=
            "2026-09-16T15:00:00Z",

        target_name=
            "ZONE_B_CRITICAL_SERVER",
    )

except ValueError as error:

    remapping_rejected = True

    print(
        "\nPASS: Already mapped event "
        "cannot be remapped."
    )

    print(
        f"  Rejection reason: {error}"
    )


if not remapping_rejected:

    raise AssertionError(
        "Already mapped event "
        "was incorrectly remapped."
    )


# ============================================================
# Final result
# ============================================================

print(
    "\n============================================"
)

print(
    "TOPOLOGY MAPPER TEST SUMMARY"
)

print(
    "============================================"
)


print(
    "PASS: Valid topology mapping"
)

print(
    "PASS: Invalid topology rejection"
)

print(
    "PASS: Remapping protection"
)

print(
    "PASS: Provenance preservation"
)

print(
    "PASS: Common-schema validation"
)


print(
    "\n============================================"
)

print(
    "DC-GUARDIAN TOPOLOGY MAPPER PASSED"
)

print(
    "============================================"
)
