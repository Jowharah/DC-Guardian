from copy import deepcopy
from datetime import (
    datetime,
    timedelta,
)
from pathlib import Path

import json


# ============================================================
# Project paths
# ============================================================

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

TOPOLOGY_FILE = (
    PROJECT_ROOT
    / "shared"
    / "topology"
    / "data_center_topology.json"
)

SSH_MAPPING_FILE = (
    PROJECT_ROOT
    / "shared"
    / "topology"
    / "mappings"
    / "ssh_asset_mapping.json"
)

MAINTENANCE_MAPPING_FILE = (
    PROJECT_ROOT
    / "shared"
    / "topology"
    / "mappings"
    / "maintenance_asset_mapping.json"
)

def load_maintenance_mapping():

    return load_json(
        MAINTENANCE_MAPPING_FILE
    )

def resolve_maintenance_target(
    target_name
):
    """
    Resolve and validate one synthetic maintenance
    scenario target.

    The target identifies the server containing the
    observed hard-drive asset.
    """

    topology = load_topology()

    mapping = (
        load_maintenance_mapping()
    )

    server_index = (
        build_server_index(
            topology
        )
    )

    data_center_id = mapping[
        "data_center_id"
    ]

    scenario_targets = mapping[
        "scenario_targets"
    ]

    if (
        target_name
        not in scenario_targets
    ):

        raise ValueError(
            "Unknown maintenance scenario target: "
            f"{target_name}"
        )

    target = scenario_targets[
        target_name
    ]

    return validate_target_mapping(
        target,
        server_index,
        data_center_id,
    )

def map_maintenance_event_to_scenario(
    common_event,
    *,
    scenario_id,
    scenario_timestamp,
    target_name,
):
    """
    Map one normalized maintenance event into a synthetic
    DC-Guardian infrastructure scenario.

    IMPORTANT:
        The hard-drive asset_id is preserved.

        The synthetic mapping adds the server containing
        the drive plus rack/zone/data-center location.

    The incoming event is never modified.
    """

    if not isinstance(
        common_event,
        dict,
    ):

        raise TypeError(
            "common_event must be a dictionary."
        )


    # ========================================================
    # Domain contract
    # ========================================================

    if (
        common_event.get(
            "domain"
        )
        != "MAINTENANCE"
    ):

        raise ValueError(
            "Maintenance topology mapper expected "
            "a MAINTENANCE event."
        )


    if (
        common_event.get(
            "event_type"
        )
        != "STORAGE_FAILURE_RISK_ASSESSMENT"
    ):

        raise ValueError(
            "Maintenance topology mapper expected "
            "STORAGE_FAILURE_RISK_ASSESSMENT."
        )


    # ========================================================
    # Must contain observed drive identity
    # ========================================================

    drive_asset_id = (
        common_event
        .get(
            "entities",
            {}
        )
        .get(
            "asset_id"
        )
    )


    if (
        not isinstance(
            drive_asset_id,
            str,
        )
        or
        not drive_asset_id.strip()
    ):

        raise ValueError(
            "Maintenance event must contain "
            "a hard-drive asset_id."
        )


    # ========================================================
    # Prevent remapping
    # ========================================================

    provenance = common_event.get(
        "provenance",
        {},
    )


    if provenance.get(
        "synthetic_mapping"
    ) is True:

        raise ValueError(
            "Event already contains a "
            "synthetic mapping."
        )


    # ========================================================
    # Scenario identity/time
    # ========================================================

    scenario_id = validate_scenario_id(
        scenario_id
    )


    scenario_timestamp = (
        validate_scenario_timestamp(
            scenario_timestamp
        )
    )


    # ========================================================
    # Resolve server containing drive
    # ========================================================

    target = (
        resolve_maintenance_target(
            target_name
        )
    )


    # ========================================================
    # Preserve provenance
    # ========================================================

    original_event_id = (
        common_event[
            "event_id"
        ]
    )

    original_timestamp = (
        common_event[
            "timestamp"
        ]
    )


    mapped_event = deepcopy(
        common_event
    )


    mapped_event[
        "event_id"
    ] = (
        f"{original_event_id}"
        f"-{scenario_id}"
    )


    # ========================================================
    # Synthetic scenario timestamp
    #
    # Maintenance is a point-in-time assessment.
    # ========================================================

    mapped_event[
        "timestamp"
    ] = scenario_timestamp


    mapped_event[
        "window"
    ] = {
        "start":
            scenario_timestamp,

        "end":
            scenario_timestamp,
    }


    # ========================================================
    # Infrastructure mapping
    #
    # DO NOT overwrite asset_id.
    # ========================================================

    mapped_event[
        "entities"
    ][
        "asset_id"
    ] = drive_asset_id


    mapped_event[
        "entities"
    ][
        "server_id"
    ] = target[
        "server_id"
    ]


    mapped_event[
        "location"
    ][
        "data_center_id"
    ] = target[
        "data_center_id"
    ]


    mapped_event[
        "location"
    ][
        "zone_id"
    ] = target[
        "zone_id"
    ]


    mapped_event[
        "location"
    ][
        "rack_id"
    ] = target[
        "rack_id"
    ]


    # ========================================================
    # Provenance
    # ========================================================

    mapped_event[
        "provenance"
    ][
        "original_event_id"
    ] = original_event_id


    mapped_event[
        "provenance"
    ][
        "synthetic_mapping"
    ] = True


    mapped_event[
        "provenance"
    ][
        "mapping_type"
    ] = "SYNTHETIC_SCENARIO"


    mapped_event[
        "provenance"
    ][
        "original_timestamp"
    ] = original_timestamp


    mapped_event[
        "provenance"
    ][
        "scenario_id"
    ] = scenario_id


    return mapped_event

# ============================================================
# JSON loader
# ============================================================

def load_json(file_path):

    if not file_path.exists():

        raise FileNotFoundError(
            f"Required file not found: "
            f"{file_path}"
        )

    with open(
        file_path,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


# ============================================================
# Load topology
# ============================================================

def load_topology():

    return load_json(
        TOPOLOGY_FILE
    )


def load_ssh_mapping():

    return load_json(
        SSH_MAPPING_FILE
    )


# ============================================================
# Build server topology index
# ============================================================

def build_server_index(
    topology
):

    """
    Build a lookup table:

    server_id
        ->
    {
        data_center_id,
        zone_id,
        rack_id,
        server_id,
        criticality
    }
    """

    data_center = topology[
        "data_center"
    ]

    data_center_id = data_center[
        "data_center_id"
    ]

    server_index = {}


    for zone in data_center[
        "zones"
    ]:

        zone_id = zone[
            "zone_id"
        ]


        for rack in zone.get(
            "racks",
            []
        ):

            rack_id = rack[
                "rack_id"
            ]


            for server in rack.get(
                "servers",
                []
            ):

                server_id = server[
                    "server_id"
                ]


                if server_id in server_index:

                    raise ValueError(
                        "Duplicate server ID "
                        f"detected: {server_id}"
                    )


                server_index[
                    server_id
                ] = {
                    "data_center_id":
                        data_center_id,

                    "zone_id":
                        zone_id,

                    "rack_id":
                        rack_id,

                    "server_id":
                        server_id,

                    "criticality":
                        server.get(
                            "criticality"
                        ),
                }


    return server_index

# ============================================================
# Build environmental sensor topology index
# ============================================================

def build_sensor_index(
    topology
):
    """
    Build:

    sensor_id ->
    {
        data_center_id,
        zone_id,
        sensor_id,
        sensor_type,
        monitors
    }
    """

    data_center = topology[
        "data_center"
    ]

    data_center_id = data_center[
        "data_center_id"
    ]

    sensor_index = {}


    for zone in data_center[
        "zones"
    ]:

        zone_id = zone[
            "zone_id"
        ]


        for sensor in zone.get(
            "sensors",
            []
        ):

            sensor_id = sensor[
                "sensor_id"
            ]


            if sensor_id in sensor_index:

                raise ValueError(
                    "Duplicate sensor ID "
                    f"detected: {sensor_id}"
                )


            sensor_index[
                sensor_id
            ] = {
                "data_center_id":
                    data_center_id,

                "zone_id":
                    zone_id,

                "sensor_id":
                    sensor_id,

                "sensor_type":
                    sensor.get(
                        "sensor_type"
                    ),

                "monitors":
                    list(
                        sensor.get(
                            "monitors",
                            []
                        )
                    ),
            }


    return sensor_index

# ============================================================
# Build camera topology index
# ============================================================

def build_camera_index(
    topology
):
    """
    Build:

    camera_id ->
    {
        data_center_id,
        zone_id,
        camera_id,
        monitors,
        access_point_id
    }

    Cameras remain observation infrastructure.
    This function does NOT evaluate person authorization.
    """

    data_center = topology[
        "data_center"
    ]

    data_center_id = data_center[
        "data_center_id"
    ]

    camera_index = {}


    for zone in data_center[
        "zones"
    ]:

        zone_id = zone[
            "zone_id"
        ]


        access_point_ids = {
            access_point[
                "access_point_id"
            ]

            for access_point
            in zone.get(
                "access_points",
                []
            )
        }


        for camera in zone.get(
            "cameras",
            []
        ):

            camera_id = camera[
                "camera_id"
            ]


            if camera_id in camera_index:

                raise ValueError(
                    "Duplicate camera ID "
                    f"detected: {camera_id}"
                )


            monitors = list(
                camera.get(
                    "monitors",
                    []
                )
            )


            # A camera may monitor a zone plus an access point.
            # Resolve the declared access point without
            # inventing one.

            monitored_access_points = [
                item
                for item in monitors
                if item
                in access_point_ids
            ]


            if (
                len(
                    monitored_access_points
                )
                > 1
            ):

                raise ValueError(
                    "Camera monitors multiple "
                    "access points and requires "
                    "explicit disambiguation: "
                    f"{camera_id}"
                )


            access_point_id = (
                monitored_access_points[
                    0
                ]
                if monitored_access_points
                else None
            )


            camera_index[
                camera_id
            ] = {
                "data_center_id":
                    data_center_id,

                "zone_id":
                    zone_id,

                "camera_id":
                    camera_id,

                "access_point_id":
                    access_point_id,

                "monitors":
                    monitors,
            }


    return camera_index

# ============================================================
# Resolve face observation camera
# ============================================================

def resolve_face_camera(
    camera_id
):
    """
    Resolve one declared camera from the synthetic
    DC-Guardian topology.

    This resolves observation context only.

    It does NOT evaluate whether a recognized person
    is authorized for the camera's zone.
    """

    if (
        not isinstance(
            camera_id,
            str,
        )
        or
        not camera_id.strip()
    ):

        raise ValueError(
            "camera_id must be "
            "a non-empty string."
        )


    topology = load_topology()


    camera_index = (
        build_camera_index(
            topology
        )
    )


    if camera_id not in camera_index:

        raise ValueError(
            "Unknown face observation camera: "
            f"{camera_id}"
        )


    return camera_index[
        camera_id
    ]

# ============================================================
# Resolve PPE observation camera
# ============================================================

def resolve_ppe_camera(
    camera_id
):
    """
    Resolve one declared camera from the DC-Guardian topology
    for a PPE safety observation.

    This establishes observation context only.

    It does NOT:
        - identify an employee
        - convert person_index into person_id
        - evaluate authorization
        - change PPE compliance state
    """

    if (
        not isinstance(
            camera_id,
            str,
        )
        or
        not camera_id.strip()
    ):

        raise ValueError(
            "camera_id must be "
            "a non-empty string."
        )


    topology = load_topology()


    camera_index = (
        build_camera_index(
            topology
        )
    )


    if camera_id not in camera_index:

        raise ValueError(
            "Unknown PPE observation camera: "
            f"{camera_id}"
        )


    return camera_index[
        camera_id
    ]

# ============================================================
# Build equipment topology index
# ============================================================

def build_equipment_index(
    topology
):
    """
    Build:

    equipment_id ->
    {
        data_center_id,
        zone_id,
        equipment_id,
        asset_type,
        criticality
    }
    """

    data_center = topology[
        "data_center"
    ]

    data_center_id = data_center[
        "data_center_id"
    ]

    equipment_index = {}


    for zone in data_center[
        "zones"
    ]:

        zone_id = zone[
            "zone_id"
        ]


        for equipment in zone.get(
            "equipment",
            []
        ):

            equipment_id = equipment[
                "equipment_id"
            ]


            if equipment_id in equipment_index:

                raise ValueError(
                    "Duplicate equipment ID "
                    f"detected: {equipment_id}"
                )


            equipment_index[
                equipment_id
            ] = {
                "data_center_id":
                    data_center_id,

                "zone_id":
                    zone_id,

                "equipment_id":
                    equipment_id,

                "asset_type":
                    equipment.get(
                        "asset_type"
                    ),

                "criticality":
                    equipment.get(
                        "criticality"
                    ),
            }


    return equipment_index

def resolve_environmental_source(
    common_event,
    *,
    hard_drive_target_name=None,
):
    """
    Resolve an environmental event against the declared
    DC-Guardian topology.

    Dedicated sensors, servers, and cooling equipment use
    existing topology identity.

    Hard drives require a controlled synthetic host-server
    target because external drive IDs are not represented
    directly in the synthetic topology.
    """

    topology = load_topology()

    entities = common_event[
        "entities"
    ]

    evidence = common_event[
        "evidence"
    ]

    source_class = evidence[
        "source_class"
    ]

    source_asset_type = evidence[
        "source_asset_type"
    ]


    # ========================================================
    # Dedicated environmental sensor
    # ========================================================

    if (
        source_class
        == "ENVIRONMENTAL_SENSOR"
    ):

        sensor_id = entities.get(
            "sensor_id"
        )


        sensor_index = build_sensor_index(
            topology
        )


        if sensor_id not in sensor_index:

            raise ValueError(
                "Unknown environmental sensor: "
                f"{sensor_id}"
            )


        sensor = sensor_index[
            sensor_id
        ]


        return {
            "mapping_source":
                "DECLARED_TOPOLOGY",

            "data_center_id":
                sensor[
                    "data_center_id"
                ],

            "zone_id":
                sensor[
                    "zone_id"
                ],

            "rack_id":
                None,

            "server_id":
                None,

            "sensor_id":
                sensor_id,

            "equipment_id":
                None,

            "monitors":
                sensor[
                    "monitors"
                ],
        }


    # ========================================================
    # Hardware telemetry
    # ========================================================

    if (
        source_class
        != "HARDWARE_TELEMETRY"
    ):

        raise ValueError(
            "Unsupported environmental "
            f"source class: {source_class}"
        )


    # --------------------------------------------------------
    # Server
    # --------------------------------------------------------

    if source_asset_type == "SERVER":

        server_id = entities.get(
            "server_id"
        )


        server_index = build_server_index(
            topology
        )


        if server_id not in server_index:

            raise ValueError(
                "Unknown environmental "
                f"server: {server_id}"
            )


        server = server_index[
            server_id
        ]


        return {
            "mapping_source":
                "DECLARED_TOPOLOGY",

            "data_center_id":
                server[
                    "data_center_id"
                ],

            "zone_id":
                server[
                    "zone_id"
                ],

            "rack_id":
                server[
                    "rack_id"
                ],

            "server_id":
                server_id,

            "sensor_id":
                None,

            "equipment_id":
                None,

            "monitors":
                [],
        }


    # --------------------------------------------------------
    # Cooling equipment
    # --------------------------------------------------------

    if (
        source_asset_type
        == "COOLING_SYSTEM"
    ):

        equipment_id = entities.get(
            "equipment_id"
        )


        equipment_index = (
            build_equipment_index(
                topology
            )
        )


        if (
            equipment_id
            not in equipment_index
        ):

            raise ValueError(
                "Unknown environmental "
                f"equipment: {equipment_id}"
            )


        equipment = equipment_index[
            equipment_id
        ]


        return {
            "mapping_source":
                "DECLARED_TOPOLOGY",

            "data_center_id":
                equipment[
                    "data_center_id"
                ],

            "zone_id":
                equipment[
                    "zone_id"
                ],

            "rack_id":
                None,

            "server_id":
                None,

            "sensor_id":
                None,

            "equipment_id":
                equipment_id,

            "monitors":
                [],
        }


    # --------------------------------------------------------
    # Hard drive
    # --------------------------------------------------------

    if source_asset_type == "HARD_DRIVE":

        if not hard_drive_target_name:

            raise ValueError(
                "Hard-drive environmental telemetry "
                "requires hard_drive_target_name."
            )


        server = (
            resolve_maintenance_target(
                hard_drive_target_name
            )
        )


        return {
            "mapping_source":
                "CONTROLLED_ASSET_MAPPING",

            "data_center_id":
                server[
                    "data_center_id"
                ],

            "zone_id":
                server[
                    "zone_id"
                ],

            "rack_id":
                server[
                    "rack_id"
                ],

            "server_id":
                server[
                    "server_id"
                ],

            "sensor_id":
                None,

            "equipment_id":
                None,

            "monitors":
                [],
        }


    raise ValueError(
        "Unsupported environmental "
        f"asset type: {source_asset_type}"
    )

def map_environmental_event_to_scenario(
    common_event,
    *,
    scenario_id,
    scenario_timestamp,
    hard_drive_target_name=None,
):
    """
    Create a NEW topology-aware environmental scenario event.

    The original normalized event is never modified.
    """

    if not isinstance(
        common_event,
        dict,
    ):

        raise TypeError(
            "common_event must be a dictionary."
        )


    if (
        common_event.get(
            "domain"
        )
        != "ENVIRONMENTAL"
    ):

        raise ValueError(
            "Environmental topology mapper expected "
            "an ENVIRONMENTAL event."
        )


    if (
        common_event.get(
            "event_type"
        )
        != "ENVIRONMENTAL_CONDITION_ASSESSMENT"
    ):

        raise ValueError(
            "Environmental topology mapper expected "
            "ENVIRONMENTAL_CONDITION_ASSESSMENT."
        )


    provenance = common_event.get(
        "provenance",
        {},
    )


    if provenance.get(
        "synthetic_mapping"
    ) is True:

        raise ValueError(
            "Event already contains a "
            "synthetic mapping."
        )


    scenario_id = validate_scenario_id(
        scenario_id
    )


    scenario_timestamp = (
        validate_scenario_timestamp(
            scenario_timestamp
        )
    )


    target = resolve_environmental_source(
        common_event,

        hard_drive_target_name=
            hard_drive_target_name,
    )


    original_event_id = (
        common_event[
            "event_id"
        ]
    )

    original_timestamp = (
        common_event[
            "timestamp"
        ]
    )


    mapped_event = deepcopy(
        common_event
    )


    mapped_event[
        "event_id"
    ] = (
        f"{original_event_id}"
        f"-{scenario_id}"
    )


    mapped_event[
        "timestamp"
    ] = scenario_timestamp


    mapped_event[
        "window"
    ] = {
        "start":
            scenario_timestamp,

        "end":
            scenario_timestamp,
    }


    # ========================================================
    # Preserve original entity identity while adding topology.
    # ========================================================

    if target[
        "server_id"
    ] is not None:

        mapped_event[
            "entities"
        ][
            "server_id"
        ] = target[
            "server_id"
        ]


    mapped_event[
        "location"
    ][
        "data_center_id"
    ] = target[
        "data_center_id"
    ]


    mapped_event[
        "location"
    ][
        "zone_id"
    ] = target[
        "zone_id"
    ]


    mapped_event[
        "location"
    ][
        "rack_id"
    ] = target[
        "rack_id"
    ]


    mapped_event[
        "provenance"
    ][
        "original_event_id"
    ] = original_event_id


    mapped_event[
        "provenance"
    ][
        "synthetic_mapping"
    ] = True


    mapped_event[
        "provenance"
    ][
        "mapping_type"
    ] = "SYNTHETIC_SCENARIO"


    mapped_event[
        "provenance"
    ][
        "original_timestamp"
    ] = original_timestamp


    mapped_event[
        "provenance"
    ][
        "scenario_id"
    ] = scenario_id


    # Preserve how topology was resolved.
    mapped_event[
        "evidence"
    ][
        "topology_resolution"
    ] = {
        "mapping_source":
            target[
                "mapping_source"
            ],

        "monitors":
            target[
                "monitors"
            ],
    }


    return mapped_event


# ============================================================
# Map normalized Face event into synthetic scenario
# ============================================================

def map_face_event_to_scenario(
    common_event,
    *,
    scenario_id,
    scenario_timestamp,
    camera_id,
):
    """
    Create a NEW topology-aware Face Recognition scenario
    event.

    The original normalized event is never modified.

    The mapper establishes observation context:

        Camera
          -> monitored Zone
          -> monitored Access Point

    IMPORTANT:
        Recognition does NOT imply authorization.

        Authorization is intentionally NOT evaluated here.

        UNKNOWN remains UNKNOWN and does not cause a
        synthetic Person identity to be created.
    """

    if not isinstance(
        common_event,
        dict,
    ):

        raise TypeError(
            "common_event must be a dictionary."
        )


    # ========================================================
    # Domain contract
    # ========================================================

    if (
        common_event.get(
            "domain"
        )
        != "PHYSICAL_SECURITY"
    ):

        raise ValueError(
            "Face topology mapper expected "
            "a PHYSICAL_SECURITY event."
        )


    if (
        common_event.get(
            "event_type"
        )
        != "FACE_IDENTIFICATION_ASSESSMENT"
    ):

        raise ValueError(
            "Face topology mapper expected "
            "FACE_IDENTIFICATION_ASSESSMENT."
        )


    # ========================================================
    # Face identity contract
    # ========================================================

    entities = common_event.get(
        "entities",
        {},
    )


    person_id = entities.get(
        "person_id"
    )


    if (
        not isinstance(
            person_id,
            str,
        )
        or
        not person_id.strip()
    ):

        raise ValueError(
            "Face event must preserve "
            "person_id."
        )


    # ========================================================
    # Prevent remapping
    # ========================================================

    provenance = common_event.get(
        "provenance",
        {},
    )


    if provenance.get(
        "synthetic_mapping"
    ) is True:

        raise ValueError(
            "Event already contains a "
            "synthetic mapping."
        )


    # ========================================================
    # Scenario identity
    # ========================================================

    scenario_id = validate_scenario_id(
        scenario_id
    )


    scenario_timestamp = (
        validate_scenario_timestamp(
            scenario_timestamp
        )
    )


    # ========================================================
    # Resolve declared camera
    # ========================================================

    camera = (
        resolve_face_camera(
            camera_id
        )
    )


    # ========================================================
    # Preserve original identity/provenance
    # ========================================================

    original_event_id = (
        common_event[
            "event_id"
        ]
    )

    original_timestamp = (
        common_event[
            "timestamp"
        ]
    )


    mapped_event = deepcopy(
        common_event
    )


    mapped_event[
        "event_id"
    ] = (
        f"{original_event_id}"
        f"-{scenario_id}"
    )


    # ========================================================
    # Point-in-time physical-security observation
    # ========================================================

    mapped_event[
        "timestamp"
    ] = scenario_timestamp


    mapped_event[
        "window"
    ] = {
        "start":
            scenario_timestamp,

        "end":
            scenario_timestamp,
    }


    # ========================================================
    # Observation topology
    #
    # Preserve person_id exactly as supplied by Evidence layer.
    # ========================================================

    mapped_event[
        "entities"
    ][
        "person_id"
    ] = person_id


    mapped_event[
        "entities"
    ][
        "camera_id"
    ] = camera[
        "camera_id"
    ]


    mapped_event[
        "location"
    ][
        "data_center_id"
    ] = camera[
        "data_center_id"
    ]


    mapped_event[
        "location"
    ][
        "zone_id"
    ] = camera[
        "zone_id"
    ]


    mapped_event[
        "location"
    ][
        "access_point_id"
    ] = camera[
        "access_point_id"
    ]


    # Face observation does not imply a rack.

    mapped_event[
        "location"
    ][
        "rack_id"
    ] = None


    # ========================================================
    # Mapping provenance
    # ========================================================

    mapped_event[
        "provenance"
    ][
        "original_event_id"
    ] = original_event_id


    mapped_event[
        "provenance"
    ][
        "synthetic_mapping"
    ] = True


    mapped_event[
        "provenance"
    ][
        "mapping_type"
    ] = "SYNTHETIC_SCENARIO"


    mapped_event[
        "provenance"
    ][
        "original_timestamp"
    ] = original_timestamp


    mapped_event[
        "provenance"
    ][
        "scenario_id"
    ] = scenario_id


    # ========================================================
    # Explainable topology evidence
    # ========================================================

    mapped_event[
        "evidence"
    ][
        "topology_resolution"
    ] = {
        "mapping_source":
            "DECLARED_TOPOLOGY",

        "camera_id":
            camera[
                "camera_id"
            ],

        "monitors":
            list(
                camera[
                    "monitors"
                ]
            ),
    }


    # Explicitly preserve the boundary:
    # mapper does NOT evaluate authorization.

    mapped_event[
        "evidence"
    ][
        "authorization_evaluated"
    ] = False


    return mapped_event

# ============================================================
# Map normalized PPE event into synthetic scenario
# ============================================================

def map_ppe_event_to_scenario(
    common_event,
    *,
    scenario_id,
    scenario_timestamp,
    camera_id,
):
    """
    Create a NEW topology-aware PPE safety scenario event.

    The original normalized event is never modified.

    The mapper establishes observation context:

        Camera
          -> monitored Zone
          -> monitored Access Point

    IMPORTANT:
        person_index is frame-local PPE evidence.

        It is NOT an employee identity and must never be
        promoted to entities.person_id.

        PPE compliance does NOT imply authorization.

        The mapper does not change the PPE assessment state.
    """

    if not isinstance(
        common_event,
        dict,
    ):

        raise TypeError(
            "common_event must be a dictionary."
        )


    # ========================================================
    # Domain contract
    # ========================================================

    if (
        common_event.get(
            "domain"
        )
        != "SAFETY"
    ):

        raise ValueError(
            "PPE topology mapper expected "
            "a SAFETY event."
        )


    if (
        common_event.get(
            "event_type"
        )
        != "PPE_COMPLIANCE_ASSESSMENT"
    ):

        raise ValueError(
            "PPE topology mapper expected "
            "PPE_COMPLIANCE_ASSESSMENT."
        )


    # ========================================================
    # PPE state contract
    # ========================================================

    assessment = common_event.get(
        "assessment",
        {},
    )


    state = assessment.get(
        "state"
    )


    supported_states = {
        "PPE_COMPLIANT",
        "PPE_NON_COMPLIANT",
        "NO_PERSON_DETECTED",
    }


    if state not in supported_states:

        raise ValueError(
            "Unsupported PPE assessment state: "
            f"{state}"
        )


    # ========================================================
    # Identity boundary
    #
    # PPE Evidence layer does not identify employees.
    # ========================================================

    entities = common_event.get(
        "entities",
        {},
    )


    if entities.get(
        "person_id"
    ) is not None:

        raise ValueError(
            "PPE event must not contain "
            "an employee person_id."
        )


    # ========================================================
    # Prevent remapping
    # ========================================================

    provenance = common_event.get(
        "provenance",
        {},
    )


    if provenance.get(
        "synthetic_mapping"
    ) is True:

        raise ValueError(
            "Event already contains a "
            "synthetic mapping."
        )


    # ========================================================
    # Scenario identity
    # ========================================================

    scenario_id = validate_scenario_id(
        scenario_id
    )


    scenario_timestamp = (
        validate_scenario_timestamp(
            scenario_timestamp
        )
    )


    # ========================================================
    # Resolve declared observation camera
    # ========================================================

    camera = (
        resolve_ppe_camera(
            camera_id
        )
    )


    # ========================================================
    # Preserve original provenance
    # ========================================================

    original_event_id = (
        common_event[
            "event_id"
        ]
    )

    original_timestamp = (
        common_event[
            "timestamp"
        ]
    )


    mapped_event = deepcopy(
        common_event
    )


    mapped_event[
        "event_id"
    ] = (
        f"{original_event_id}"
        f"-{scenario_id}"
    )


    # ========================================================
    # Point-in-time safety observation
    # ========================================================

    mapped_event[
        "timestamp"
    ] = scenario_timestamp


    mapped_event[
        "window"
    ] = {
        "start":
            scenario_timestamp,

        "end":
            scenario_timestamp,
    }


    # ========================================================
    # Observation topology
    # ========================================================

    mapped_event[
        "entities"
    ][
        "person_id"
    ] = None


    mapped_event[
        "entities"
    ][
        "camera_id"
    ] = camera[
        "camera_id"
    ]


    mapped_event[
        "location"
    ][
        "data_center_id"
    ] = camera[
        "data_center_id"
    ]


    mapped_event[
        "location"
    ][
        "zone_id"
    ] = camera[
        "zone_id"
    ]


    mapped_event[
        "location"
    ][
        "access_point_id"
    ] = camera[
        "access_point_id"
    ]


    # Camera observation does not imply a rack.

    mapped_event[
        "location"
    ][
        "rack_id"
    ] = None


    # ========================================================
    # Mapping provenance
    # ========================================================

    mapped_event[
        "provenance"
    ][
        "original_event_id"
    ] = original_event_id


    mapped_event[
        "provenance"
    ][
        "synthetic_mapping"
    ] = True


    mapped_event[
        "provenance"
    ][
        "mapping_type"
    ] = "SYNTHETIC_SCENARIO"


    mapped_event[
        "provenance"
    ][
        "original_timestamp"
    ] = original_timestamp


    mapped_event[
        "provenance"
    ][
        "scenario_id"
    ] = scenario_id


    # ========================================================
    # Explainable topology evidence
    # ========================================================

    mapped_event[
        "evidence"
    ][
        "topology_resolution"
    ] = {
        "mapping_source":
            "DECLARED_TOPOLOGY",

        "camera_id":
            camera[
                "camera_id"
            ],

        "monitors":
            list(
                camera[
                    "monitors"
                ]
            ),
    }


    # ========================================================
    # Preserve responsibility boundaries
    # ========================================================

    mapped_event[
        "evidence"
    ][
        "employee_identity_evaluated"
    ] = False


    mapped_event[
        "evidence"
    ][
        "authorization_evaluated"
    ] = False


    return mapped_event

# ============================================================
# Validate one configured mapping
# ============================================================

def validate_target_mapping(
    target,
    server_index,
    expected_data_center_id
):

    required = [
        "server_id",
        "rack_id",
        "zone_id",
    ]


    missing = [
        field
        for field in required
        if field not in target
    ]


    if missing:

        raise ValueError(
            "Target mapping is missing: "
            + ", ".join(
                missing
            )
        )


    server_id = target[
        "server_id"
    ]

    rack_id = target[
        "rack_id"
    ]

    zone_id = target[
        "zone_id"
    ]


    # --------------------------------------------------------
    # Does the server actually exist?
    # --------------------------------------------------------

    if server_id not in server_index:

        raise ValueError(
            f"Unknown server ID: "
            f"{server_id}"
        )


    actual = server_index[
        server_id
    ]


    # --------------------------------------------------------
    # Verify server -> rack
    # --------------------------------------------------------

    if (
        actual[
            "rack_id"
        ]
        != rack_id
    ):

        raise ValueError(
            f"Invalid topology mapping: "
            f"{server_id} belongs to "
            f"{actual['rack_id']}, "
            f"not {rack_id}."
        )


    # --------------------------------------------------------
    # Verify rack/server -> zone
    # --------------------------------------------------------

    if (
        actual[
            "zone_id"
        ]
        != zone_id
    ):

        raise ValueError(
            f"Invalid topology mapping: "
            f"{server_id} belongs to "
            f"{actual['zone_id']}, "
            f"not {zone_id}."
        )


    # --------------------------------------------------------
    # Verify data center
    # --------------------------------------------------------

    if (
        actual[
            "data_center_id"
        ]
        != expected_data_center_id
    ):

        raise ValueError(
            f"Invalid data-center mapping "
            f"for {server_id}."
        )


    return actual


# ============================================================
# Resolve named SSH scenario target
# ============================================================

def resolve_ssh_target(
    target_name
):

    topology = load_topology()

    mapping = load_ssh_mapping()


    server_index = (
        build_server_index(
            topology
        )
    )


    data_center_id = mapping[
        "data_center_id"
    ]


    scenario_targets = mapping[
        "scenario_targets"
    ]


    if (
        target_name
        not in scenario_targets
    ):

        raise ValueError(
            "Unknown SSH scenario target: "
            f"{target_name}"
        )


    target = scenario_targets[
        target_name
    ]


    actual = validate_target_mapping(
        target,
        server_index,
        data_center_id
    )


    return actual


# ============================================================
# Scenario identifier validation
# ============================================================

MAX_SCENARIO_ID_LENGTH = 128


def validate_scenario_id(
    value
):
    """
    Validate a scenario identifier before it is used to build
    mapped event/correlation identifiers.
    """

    if (
        not isinstance(
            value,
            str,
        )
        or not value.strip()
    ):

        raise ValueError(
            "scenario_id must be a non-empty string."
        )


    if len(value) > MAX_SCENARIO_ID_LENGTH:

        raise ValueError(
            "scenario_id exceeds the maximum "
            f"length of {MAX_SCENARIO_ID_LENGTH} characters."
        )


    if any(
        character.isspace()
        or ord(character) < 33
        or ord(character) > 126
        for character in value
    ):

        raise ValueError(
            "scenario_id must contain printable ASCII "
            "characters without whitespace."
        )


    return value


# ============================================================
# Scenario timestamp validation
# ============================================================

def validate_scenario_timestamp(
    value
):

    if not isinstance(
        value,
        str
    ):

        raise TypeError(
            "scenario_timestamp must "
            "be an ISO-8601 string."
        )


    try:

        normalized = value.replace(
            "Z",
            "+00:00"
        )

        datetime.fromisoformat(
            normalized
        )

    except ValueError as error:

        raise ValueError(
            "scenario_timestamp is not "
            "a valid ISO-8601 timestamp."
        ) from error


    return value


# ============================================================
# Map normalized SSH event into synthetic scenario
# ============================================================

def map_ssh_event_to_scenario(
    common_event,
    *,
    scenario_id,
    scenario_timestamp,
    target_name
):

    """
    Create a NEW mapped event.

    The incoming normalized event is not modified.

    The resulting event receives:
      - synthetic server/rack/zone/DC mapping
      - synthetic scenario timestamp
      - original timestamp provenance
      - original event ID provenance
      - scenario identifier
    """

    if not isinstance(
        common_event,
        dict
    ):

        raise TypeError(
            "common_event must be "
            "a dictionary."
        )


    # --------------------------------------------------------
    # Validate expected event type/domain
    # --------------------------------------------------------

    if (
        common_event.get(
            "domain"
        )
        != "CYBERSECURITY"
    ):

        raise ValueError(
            "Topology mapper expected "
            "a CYBERSECURITY event."
        )


    if (
        common_event.get(
            "event_type"
        )
        != "SSH_BEHAVIOR_ASSESSMENT"
    ):

        raise ValueError(
            "Topology mapper expected "
            "SSH_BEHAVIOR_ASSESSMENT."
        )


    # --------------------------------------------------------
    # Prevent accidental remapping
    # --------------------------------------------------------

    provenance = common_event.get(
        "provenance",
        {}
    )


    if provenance.get(
        "synthetic_mapping"
    ) is True:

        raise ValueError(
            "Event already contains a "
            "synthetic mapping."
        )


    # --------------------------------------------------------
    # Scenario ID
    # --------------------------------------------------------

    scenario_id = validate_scenario_id(
        scenario_id
    )


    # --------------------------------------------------------
    # Validate scenario time
    # --------------------------------------------------------

    scenario_timestamp = (
        validate_scenario_timestamp(
            scenario_timestamp
        )
    )


    # --------------------------------------------------------
    # Resolve and validate target
    # --------------------------------------------------------

    target = resolve_ssh_target(
        target_name
    )


    # --------------------------------------------------------
    # Preserve original event
    # --------------------------------------------------------

    original_event_id = (
        common_event[
            "event_id"
        ]
    )

    original_timestamp = (
        common_event[
            "timestamp"
        ]
    )


    # --------------------------------------------------------
    # Copy - do NOT mutate original
    # --------------------------------------------------------

    mapped_event = deepcopy(
        common_event
    )


    # --------------------------------------------------------
    # Create new mapped-event identifier
    # --------------------------------------------------------

    mapped_event[
        "event_id"
    ] = (
        f"{original_event_id}"
        f"-{scenario_id}"
    )


    # --------------------------------------------------------
    # Synthetic scenario timestamp
    # --------------------------------------------------------

    mapped_event[
        "timestamp"
    ] = scenario_timestamp


    # SSH uses five-minute windows.
    # Keep the same duration in the synthetic scenario.

    start_dt = datetime.fromisoformat(
        scenario_timestamp.replace(
            "Z",
            "+00:00"
        )
    )

    end_dt = (
        start_dt
        + timedelta(
            minutes=5
        )
    )


    mapped_event[
        "window"
    ] = {
        "start":
            scenario_timestamp,

        "end":
            end_dt
            .isoformat()
            .replace(
                "+00:00",
                "Z"
            ),
    }


    # --------------------------------------------------------
    # Synthetic infrastructure mapping
    # --------------------------------------------------------

    mapped_event[
        "entities"
    ][
        "asset_id"
    ] = target[
        "server_id"
    ]


    mapped_event[
        "entities"
    ][
        "server_id"
    ] = target[
        "server_id"
    ]


    mapped_event[
        "location"
    ][
        "data_center_id"
    ] = target[
        "data_center_id"
    ]


    mapped_event[
        "location"
    ][
        "zone_id"
    ] = target[
        "zone_id"
    ]


    mapped_event[
        "location"
    ][
        "rack_id"
    ] = target[
        "rack_id"
    ]


    # --------------------------------------------------------
    # Provenance
    # --------------------------------------------------------

    mapped_event[
        "provenance"
    ][
        "original_event_id"
    ] = original_event_id


    mapped_event[
        "provenance"
    ][
        "synthetic_mapping"
    ] = True


    mapped_event[
        "provenance"
    ][
        "mapping_type"
    ] = "SYNTHETIC_SCENARIO"


    mapped_event[
        "provenance"
    ][
        "original_timestamp"
    ] = original_timestamp


    mapped_event[
        "provenance"
    ][
        "scenario_id"
    ] = scenario_id


    return mapped_event