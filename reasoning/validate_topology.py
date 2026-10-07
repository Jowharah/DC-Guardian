from pathlib import Path
import json


# ============================================================
# Paths
# ============================================================

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

TOPOLOGY_FILE = (
    PROJECT_ROOT
    / "shared"
    / "topology"
    / "data_center_topology.json"
)


# ============================================================
# Load topology
# ============================================================

def load_topology():

    if not TOPOLOGY_FILE.exists():

        raise FileNotFoundError(
            f"Topology file not found: "
            f"{TOPOLOGY_FILE}"
        )

    with open(
        TOPOLOGY_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


# ============================================================
# Main validation
# ============================================================

if __name__ == "__main__":

    print(
        "\n============================================"
    )

    print(
        "DC-GUARDIAN TOPOLOGY VALIDATION"
    )

    print(
        "============================================"
    )


    topology = load_topology()


    # --------------------------------------------------------
    # Basic metadata
    # --------------------------------------------------------

    assert (
        topology[
            "topology_version"
        ]
        == "1.0"
    )

    assert (
        topology[
            "topology_type"
        ]
        == "SYNTHETIC"
    )


    data_center = topology[
        "data_center"
    ]

    assert (
        data_center[
            "data_center_id"
        ]
        == "DC-01"
    )


    zones = data_center[
        "zones"
    ]


    # ========================================================
    # Collect identifiers
    # ========================================================

    zone_ids = []

    rack_ids = []

    server_ids = []

    camera_ids = []

    sensor_ids = []

    access_point_ids = []

    equipment_ids = []


    for zone in zones:

        zone_ids.append(
            zone[
                "zone_id"
            ]
        )


        for access_point in zone.get(
            "access_points",
            []
        ):

            access_point_ids.append(
                access_point[
                    "access_point_id"
                ]
            )


        for camera in zone.get(
            "cameras",
            []
        ):

            camera_ids.append(
                camera[
                    "camera_id"
                ]
            )


        for sensor in zone.get(
            "sensors",
            []
        ):

            sensor_ids.append(
                sensor[
                    "sensor_id"
                ]
            )


        for rack in zone.get(
            "racks",
            []
        ):

            rack_ids.append(
                rack[
                    "rack_id"
                ]
            )


            for server in rack.get(
                "servers",
                []
            ):

                server_ids.append(
                    server[
                        "server_id"
                    ]
                )


        for equipment in zone.get(
            "equipment",
            []
        ):

            equipment_ids.append(
                equipment[
                    "equipment_id"
                ]
            )


    # ========================================================
    # Duplicate-ID checks
    # ========================================================

    identifier_groups = {
        "zone":
            zone_ids,

        "rack":
            rack_ids,

        "server":
            server_ids,

        "camera":
            camera_ids,

        "sensor":
            sensor_ids,

        "access point":
            access_point_ids,

        "equipment":
            equipment_ids,
    }


    for name, identifiers in (
        identifier_groups.items()
    ):

        if (
            len(identifiers)
            != len(set(identifiers))
        ):

            raise ValueError(
                f"Duplicate {name} ID detected."
            )


    print(
        "\nPASS: Infrastructure IDs "
        "are unique."
    )


    # ========================================================
    # Person / authorization validation
    # ========================================================

    people = topology.get(
        "people",
        []
    )


    person_ids = [
        person[
            "person_id"
        ]
        for person
        in people
    ]


    if (
        len(person_ids)
        != len(set(person_ids))
    ):

        raise ValueError(
            "Duplicate person ID detected."
        )


    for person in people:

        for authorized_zone in person[
            "authorized_zones"
        ]:

            if (
                authorized_zone
                not in zone_ids
            ):

                raise ValueError(
                    f"{person['person_id']} "
                    f"references unknown zone "
                    f"{authorized_zone}."
                )


    print(
        "PASS: Person authorization "
        "references valid zones."
    )


    # ========================================================
    # Camera monitoring references
    # ========================================================

    valid_camera_targets = (
        set(zone_ids)
        | set(access_point_ids)
    )


    for zone in zones:

        for camera in zone.get(
            "cameras",
            []
        ):

            for target in camera.get(
                "monitors",
                []
            ):

                if (
                    target
                    not in valid_camera_targets
                ):

                    raise ValueError(
                        f"Camera "
                        f"{camera['camera_id']} "
                        f"references unknown "
                        f"monitoring target "
                        f"{target}."
                    )


    print(
        "PASS: Camera monitoring "
        "references are valid."
    )


    # ========================================================
    # Sensor monitoring references
    # ========================================================

    valid_sensor_targets = (
        set(zone_ids)
        | set(server_ids)
        | set(equipment_ids)
    )


    for zone in zones:

        for sensor in zone.get(
            "sensors",
            []
        ):

            for target in sensor.get(
                "monitors",
                []
            ):

                if (
                    target
                    not in valid_sensor_targets
                ):

                    raise ValueError(
                        f"Sensor "
                        f"{sensor['sensor_id']} "
                        f"references unknown "
                        f"monitoring target "
                        f"{target}."
                    )


    print(
        "PASS: Sensor monitoring "
        "references are valid."
    )


    # ========================================================
    # Summary
    # ========================================================

    print(
        "\n============================================"
    )

    print(
        "TOPOLOGY SUMMARY"
    )

    print(
        "============================================"
    )


    print(
        f"Data centers: 1"
    )

    print(
        f"Zones:        {len(zone_ids)}"
    )

    print(
        f"Racks:        {len(rack_ids)}"
    )

    print(
        f"Servers:      {len(server_ids)}"
    )

    print(
        f"Cameras:      {len(camera_ids)}"
    )

    print(
        f"Sensors:      {len(sensor_ids)}"
    )

    print(
        f"Access points:{len(access_point_ids)}"
    )

    print(
        f"Equipment:    {len(equipment_ids)}"
    )

    print(
        f"People:       {len(person_ids)}"
    )


    print(
        "\n============================================"
    )

    print(
        "DC-GUARDIAN SYNTHETIC "
        "TOPOLOGY PASSED"
    )

    print(
        "============================================"
    )