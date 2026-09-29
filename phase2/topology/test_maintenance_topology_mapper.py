from copy import deepcopy
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
    .parents[2]
)


TOPOLOGY_MODULE_DIR = (
    PROJECT_ROOT
    / "phase2"
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
    map_maintenance_event_to_scenario,
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

    schema = json.load(
        file
    )


validator = Draft202012Validator(
    schema,
    format_checker=FormatChecker(),
)


# ============================================================
# Normalized maintenance event
# ============================================================

normalized_event = {
    "event_id":
        "EVT-MAINT-MAP-TEST-001",

    "schema_version":
        "1.0",

    "timestamp":
        "2026-03-20T00:00:00",

    "window": {
        "start":
            "2026-03-20T00:00:00",

        "end":
            "2026-03-20T00:00:00",
    },

    "domain":
        "MAINTENANCE",

    "event_type":
        "STORAGE_FAILURE_RISK_ASSESSMENT",

    "source": {
        "component":
            "maintenance_detector",

        "component_version":
            "1.0",

        "model_name":
            "DC_Guardian_Temporal_RF_v2",
    },

    "entities": {
        "person_id":
            None,

        "source_ip":
            None,

        "asset_id":
            "DRV-MAINT-001",

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
            "AT_RISK",

        "confidence":
            None,

        "score":
            0.714008,

        "anomaly_detected":
            True,
    },

    "evidence": {
        "failure_probability":
            0.714008,

        "operating_threshold":
            0.45,

        "failure_horizon_days":
            7,
    },

    "provenance": {
        "source_type":
            "CONTROLLED_TEST",

        "dataset_name":
            "DC-Guardian Maintenance Mapper Test",

        "original_event_id":
            None,

        "synthetic_mapping":
            False,

        "mapping_type":
            "NONE",

        "original_timestamp":
            "2026-03-20T00:00:00",

        "scenario_id":
            None,
    },
}


print(
    "\n============================================"
)

print(
    "DC-GUARDIAN MAINTENANCE TOPOLOGY TEST"
)

print(
    "============================================"
)


original_copy = deepcopy(
    normalized_event
)


mapped = map_maintenance_event_to_scenario(
    normalized_event,

    scenario_id=
        "SCENARIO-MAINT-001",

    scenario_timestamp=
        "2026-09-16T14:25:00Z",

    target_name=
        "ZONE_B_CRITICAL_STORAGE",
)


# ============================================================
# Common schema
# ============================================================

errors = list(
    validator.iter_errors(
        mapped
    )
)


if errors:

    for error in errors:

        print(
            error.message
        )

    raise AssertionError(
        "Mapped maintenance event "
        "failed common schema."
    )


print(
    "PASS: Mapped event matches "
    "Common Event Schema."
)


# ============================================================
# Preserve drive identity
# ============================================================

assert (
    mapped[
        "entities"
    ][
        "asset_id"
    ]
    == "DRV-MAINT-001"
)


print(
    "PASS: Hard-drive asset identity preserved."
)


# ============================================================
# Infrastructure hierarchy
# ============================================================

assert (
    mapped[
        "entities"
    ][
        "server_id"
    ]
    == "SRV-B1-01"
)


assert (
    mapped[
        "location"
    ][
        "rack_id"
    ]
    == "RACK-B1"
)


assert (
    mapped[
        "location"
    ][
        "zone_id"
    ]
    == "ZONE-B"
)


assert (
    mapped[
        "location"
    ][
        "data_center_id"
    ]
    == "DC-01"
)


print(
    "PASS: Drive -> server -> rack -> "
    "zone -> data center mapping."
)


# ============================================================
# Synthetic scenario time
# ============================================================

assert (
    mapped[
        "timestamp"
    ]
    == "2026-09-16T14:25:00Z"
)


assert (
    mapped[
        "window"
    ][
        "start"
    ]
    == mapped[
        "window"
    ][
        "end"
    ]
)


print(
    "PASS: Point-in-time maintenance "
    "scenario timestamp applied."
)


# ============================================================
# Provenance
# ============================================================

assert (
    mapped[
        "provenance"
    ][
        "synthetic_mapping"
    ]
    is True
)


assert (
    mapped[
        "provenance"
    ][
        "mapping_type"
    ]
    == "SYNTHETIC_SCENARIO"
)


assert (
    mapped[
        "provenance"
    ][
        "scenario_id"
    ]
    == "SCENARIO-MAINT-001"
)


assert (
    mapped[
        "provenance"
    ][
        "original_event_id"
    ]
    == "EVT-MAINT-MAP-TEST-001"
)


print(
    "PASS: Mapping provenance preserved."
)


# ============================================================
# Original event immutable
# ============================================================

assert (
    normalized_event
    == original_copy
)


print(
    "PASS: Original normalized event unchanged."
)


# ============================================================
# Remapping protection
# ============================================================

try:

    map_maintenance_event_to_scenario(
        mapped,

        scenario_id=
            "SCENARIO-MAINT-002",

        scenario_timestamp=
            "2026-09-16T15:00:00Z",

        target_name=
            "ZONE_A_SERVER_STORAGE",
    )

    raise AssertionError(
        "Mapped maintenance event "
        "was allowed to remap."
    )

except ValueError:

    pass


print(
    "PASS: Remapping rejected."
)


print(
    "\n============================================"
)

print(
    "MAINTENANCE TOPOLOGY CONTRACT PASSED"
)

print(
    "============================================"
)