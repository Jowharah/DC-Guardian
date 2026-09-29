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


# ============================================================
# Python import paths
# ============================================================

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


from phase1.environmental_monitoring.src.sensor_monitor import (
    assess_sensor_reading,
)

from phase1.environmental_monitoring.src.hardware_monitor import (
    assess_hardware_environment,
)

from environmental_event_adapter import (
    adapt_environmental_assessment,
)

from topology_mapper import (
    map_environmental_event_to_scenario,
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


# ============================================================
# Helper
# ============================================================

def validate_common_event(
    event,
):

    errors = sorted(
        validator.iter_errors(
            event
        ),
        key=lambda error: list(
            error.absolute_path
        ),
    )


    if errors:

        for error in errors:

            location = ".".join(
                str(item)
                for item
                in error.absolute_path
            )

            if not location:
                location = "<root>"

            print(
                f"Field: {location}"
            )

            print(
                f"Error: {error.message}"
            )


        raise AssertionError(
            "Environmental mapped event "
            "failed Common Event Schema."
        )


# ============================================================
# Test
# ============================================================

print(
    "\n============================================"
)

print(
    "DC-GUARDIAN ENVIRONMENTAL TOPOLOGY TEST"
)

print(
    "============================================"
)


# ============================================================
# 1. Dedicated environmental sensor
#
# SEN-B-01 is declared in ZONE-B.
# ============================================================

sensor_assessment = assess_sensor_reading(
    sensor_id=
        "SEN-B-01",

    observation_timestamp=
        "2026-09-18T12:03:00Z",

    temperature_c=
        42.5,

    humidity_pct=
        48.0,
)


sensor_event = (
    adapt_environmental_assessment(
        sensor_assessment,

        dataset_name=
            "DC-Guardian Environmental "
            "Topology Test",

        source_type=
            "CONTROLLED_TEST",

        event_id=
            "EVT-ENV-MAP-SENSOR-001",
    )
)


sensor_original = deepcopy(
    sensor_event
)


sensor_mapped = (
    map_environmental_event_to_scenario(
        sensor_event,

        scenario_id=
            "SCENARIO-ENV-SENSOR-001",

        scenario_timestamp=
            "2026-09-18T12:03:00Z",
    )
)


validate_common_event(
    sensor_mapped
)


assert (
    sensor_mapped[
        "entities"
    ][
        "sensor_id"
    ]
    == "SEN-B-01"
)


assert (
    sensor_mapped[
        "location"
    ][
        "zone_id"
    ]
    == "ZONE-B"
)


assert (
    sensor_mapped[
        "location"
    ][
        "data_center_id"
    ]
    == "DC-01"
)


assert (
    sensor_mapped[
        "location"
    ][
        "rack_id"
    ]
    is None
)


assert (
    sensor_mapped[
        "evidence"
    ][
        "topology_resolution"
    ][
        "mapping_source"
    ]
    == "DECLARED_TOPOLOGY"
)


assert (
    "ZONE-B"
    in sensor_mapped[
        "evidence"
    ][
        "topology_resolution"
    ][
        "monitors"
    ]
)


assert (
    sensor_event
    == sensor_original
)


print(
    "PASS: Dedicated sensor -> "
    "ZONE-B topology mapping."
)


# ============================================================
# 2. Server hardware telemetry
# ============================================================

server_assessment = (
    assess_hardware_environment(
        asset_id=
            "SRV-B1-01",

        asset_type=
            "SERVER",

        observation_timestamp=
            "2026-09-18T12:04:00Z",

        temperature_c=
            40.0,
    )
)


server_event = (
    adapt_environmental_assessment(
        server_assessment,

        dataset_name=
            "DC-Guardian Environmental "
            "Topology Test",

        source_type=
            "CONTROLLED_TEST",

        event_id=
            "EVT-ENV-MAP-SERVER-001",
    )
)


server_mapped = (
    map_environmental_event_to_scenario(
        server_event,

        scenario_id=
            "SCENARIO-ENV-SERVER-001",

        scenario_timestamp=
            "2026-09-18T12:04:00Z",
    )
)


validate_common_event(
    server_mapped
)


assert (
    server_mapped[
        "entities"
    ][
        "asset_id"
    ]
    == "SRV-B1-01"
)


assert (
    server_mapped[
        "entities"
    ][
        "server_id"
    ]
    == "SRV-B1-01"
)


assert (
    server_mapped[
        "location"
    ][
        "rack_id"
    ]
    == "RACK-B1"
)


assert (
    server_mapped[
        "location"
    ][
        "zone_id"
    ]
    == "ZONE-B"
)


assert (
    server_mapped[
        "evidence"
    ][
        "topology_resolution"
    ][
        "mapping_source"
    ]
    == "DECLARED_TOPOLOGY"
)


print(
    "PASS: Server telemetry -> "
    "Server -> Rack -> Zone mapping."
)


# ============================================================
# 3. Cooling-system telemetry
#
# CHILLER-C1 is declared in ZONE-C.
# ============================================================

cooling_assessment = (
    assess_hardware_environment(
        asset_id=
            "CHILLER-C1",

        asset_type=
            "COOLING_SYSTEM",

        observation_timestamp=
            "2026-09-18T12:05:00Z",

        temperature_c=
            38.0,
    )
)


cooling_event = (
    adapt_environmental_assessment(
        cooling_assessment,

        dataset_name=
            "DC-Guardian Environmental "
            "Topology Test",

        source_type=
            "CONTROLLED_TEST",

        event_id=
            "EVT-ENV-MAP-COOLING-001",
    )
)


cooling_mapped = (
    map_environmental_event_to_scenario(
        cooling_event,

        scenario_id=
            "SCENARIO-ENV-COOLING-001",

        scenario_timestamp=
            "2026-09-18T12:05:00Z",
    )
)


validate_common_event(
    cooling_mapped
)


assert (
    cooling_mapped[
        "entities"
    ][
        "equipment_id"
    ]
    == "CHILLER-C1"
)


assert (
    cooling_mapped[
        "location"
    ][
        "zone_id"
    ]
    == "ZONE-C"
)


assert (
    cooling_mapped[
        "location"
    ][
        "rack_id"
    ]
    is None
)


assert (
    cooling_mapped[
        "evidence"
    ][
        "topology_resolution"
    ][
        "mapping_source"
    ]
    == "DECLARED_TOPOLOGY"
)


print(
    "PASS: Cooling telemetry -> "
    "ZONE-C topology mapping."
)


# ============================================================
# 4. Hard-drive environmental telemetry
#
# External drive identity does not exist directly in the
# synthetic topology, therefore controlled asset placement
# is required.
# ============================================================

drive_assessment = (
    assess_hardware_environment(
        asset_id=
            "DRV-ENV-001",

        asset_type=
            "HARD_DRIVE",

        observation_timestamp=
            "2026-09-18T12:06:00Z",

        temperature_c=
            41.0,
    )
)


drive_event = (
    adapt_environmental_assessment(
        drive_assessment,

        dataset_name=
            "DC-Guardian Environmental "
            "Topology Test",

        source_type=
            "CONTROLLED_TEST",

        event_id=
            "EVT-ENV-MAP-DRIVE-001",
    )
)


drive_original = deepcopy(
    drive_event
)


drive_mapped = (
    map_environmental_event_to_scenario(
        drive_event,

        scenario_id=
            "SCENARIO-ENV-DRIVE-001",

        scenario_timestamp=
            "2026-09-18T12:06:00Z",

        hard_drive_target_name=
            "ZONE_B_CRITICAL_STORAGE",
    )
)


validate_common_event(
    drive_mapped
)


# Drive identity must survive mapping.

assert (
    drive_mapped[
        "entities"
    ][
        "asset_id"
    ]
    == "DRV-ENV-001"
)


# Host infrastructure is added separately.

assert (
    drive_mapped[
        "entities"
    ][
        "server_id"
    ]
    == "SRV-B1-01"
)


assert (
    drive_mapped[
        "location"
    ][
        "rack_id"
    ]
    == "RACK-B1"
)


assert (
    drive_mapped[
        "location"
    ][
        "zone_id"
    ]
    == "ZONE-B"
)


assert (
    drive_mapped[
        "location"
    ][
        "data_center_id"
    ]
    == "DC-01"
)


assert (
    drive_mapped[
        "evidence"
    ][
        "topology_resolution"
    ][
        "mapping_source"
    ]
    == "CONTROLLED_ASSET_MAPPING"
)


assert (
    drive_event
    == drive_original
)


print(
    "PASS: Hard-drive telemetry -> "
    "Drive -> Server -> Rack -> Zone mapping."
)


# ============================================================
# 5. Provenance
# ============================================================

for mapped in [
    sensor_mapped,
    server_mapped,
    cooling_mapped,
    drive_mapped,
]:

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
            "original_event_id"
        ]
        is not None
    )


    assert (
        mapped[
            "provenance"
        ][
            "original_timestamp"
        ]
        is not None
    )


print(
    "PASS: Environmental mapping "
    "provenance preserved."
)


# ============================================================
# 6. Remapping protection
# ============================================================

rejected = False


try:

    map_environmental_event_to_scenario(
        sensor_mapped,

        scenario_id=
            "SCENARIO-ENV-REMAP",

        scenario_timestamp=
            "2026-09-18T13:00:00Z",
    )

except ValueError:

    rejected = True


assert rejected


print(
    "PASS: Environmental remapping rejected."
)


# ============================================================
# Final
# ============================================================

print(
    "\n============================================"
)

print(
    "ENVIRONMENTAL TOPOLOGY CONTRACT SUMMARY"
)

print(
    "============================================"
)


print(
    "PASS: Dedicated sensor topology."
)

print(
    "PASS: Server telemetry topology."
)

print(
    "PASS: Cooling equipment topology."
)

print(
    "PASS: Hard-drive telemetry topology."
)

print(
    "PASS: Declared vs controlled mapping distinguished."
)

print(
    "PASS: Original events remain immutable."
)


print(
    "\n============================================"
)

print(
    "ENVIRONMENTAL TOPOLOGY CONTRACT PASSED"
)

print(
    "============================================"
)