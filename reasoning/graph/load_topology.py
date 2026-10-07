from pathlib import Path
import json
import os

from dotenv import load_dotenv
from neo4j import GraphDatabase


# ============================================================
# Project root
# ============================================================

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)


# ============================================================
# Load .env BEFORE reading environment variables
# ============================================================

ENV_FILE = (
    PROJECT_ROOT
    / ".env"
)

if not ENV_FILE.exists():
    raise FileNotFoundError(
        f".env file not found: {ENV_FILE}"
    )

load_dotenv(
    dotenv_path=ENV_FILE
)

TOPOLOGY_FILE = (
    PROJECT_ROOT
    / "shared"
    / "topology"
    / "data_center_topology.json"
)

SCHEMA_FILE = (
    PROJECT_ROOT
    / "reasoning"
    / "graph"
    / "schema.cypher"
)

# ============================================================
# Neo4j configuration
# ============================================================

NEO4J_URI = os.getenv(
    "NEO4J_URI",
    "bolt://localhost:7687"
)

NEO4J_USER = os.getenv(
    "NEO4J_USER",
    "neo4j"
)

NEO4J_PASSWORD = os.getenv(
    "NEO4J_PASSWORD"
)

NEO4J_DATABASE = os.getenv(
    "NEO4J_DATABASE",
    "neo4j"
)
# ============================================================
# Load JSON
# ============================================================

def load_json(file_path):

    if not file_path.exists():
        raise FileNotFoundError(
            f"File not found: {file_path}"
        )

    with open(
        file_path,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


# ============================================================
# Validate configuration
# ============================================================

def validate_configuration():

    if not NEO4J_PASSWORD:

        raise ValueError(
            "NEO4J_PASSWORD environment variable "
            "has not been set."
        )


# ============================================================
# Apply graph constraints
# ============================================================

def apply_schema(driver):

    if not SCHEMA_FILE.exists():

        raise FileNotFoundError(
            f"Schema file not found: "
            f"{SCHEMA_FILE}"
        )

    schema_text = SCHEMA_FILE.read_text(
        encoding="utf-8"
    )

    statements = [
        statement.strip()
        for statement
        in schema_text.split(";")
        if statement.strip()
    ]

    with driver.session(
        database=NEO4J_DATABASE
    ) as session:

        for statement in statements:

            session.run(
                statement
            ).consume()


# ============================================================
# Load topology
# ============================================================

def load_topology_into_neo4j(
    driver,
    topology
):

    data_center = topology[
        "data_center"
    ]

    dc_id = data_center[
        "data_center_id"
    ]

    dc_name = data_center[
        "name"
    ]


    with driver.session(
        database=NEO4J_DATABASE
    ) as session:

        # ====================================================
        # Data center
        # ====================================================

        session.run(
            """
            MERGE (dc:DataCenter {
                data_center_id: $dc_id
            })
            SET
                dc.name = $name,
                dc.topology_version = $version,
                dc.topology_type = $topology_type
            """,
            dc_id=dc_id,
            name=dc_name,
            version=topology[
                "topology_version"
            ],
            topology_type=topology[
                "topology_type"
            ],
        ).consume()


        # ====================================================
        # Zones and contained infrastructure
        # ====================================================

        for zone in data_center[
            "zones"
        ]:

            zone_id = zone[
                "zone_id"
            ]


            session.run(
                """
                MATCH (dc:DataCenter {
                    data_center_id: $dc_id
                })

                MERGE (z:Zone {
                    zone_id: $zone_id
                })

                SET
                    z.name = $name,
                    z.zone_type = $zone_type,
                    z.criticality = $criticality

                MERGE (z)-[:PART_OF]->(dc)
                """,
                dc_id=dc_id,
                zone_id=zone_id,
                name=zone[
                    "name"
                ],
                zone_type=zone[
                    "zone_type"
                ],
                criticality=zone[
                    "criticality"
                ],
            ).consume()


            # ================================================
            # Access points
            # ================================================

            for access_point in zone.get(
                "access_points",
                []
            ):

                session.run(
                    """
                    MATCH (z:Zone {
                        zone_id: $zone_id
                    })

                    MERGE (a:AccessPoint {
                        access_point_id:
                            $access_point_id
                    })

                    SET a.name = $name

                    MERGE (a)-[:CONTROLS_ACCESS_TO]->(z)
                    """,
                    zone_id=zone_id,
                    access_point_id=
                        access_point[
                            "access_point_id"
                        ],
                    name=access_point[
                        "name"
                    ],
                ).consume()


            # ================================================
            # Cameras
            # ================================================

            for camera in zone.get(
                "cameras",
                []
            ):

                session.run(
                    """
                    MERGE (c:Camera {
                        camera_id: $camera_id
                    })

                    SET c.name = $name
                    """,
                    camera_id=camera[
                        "camera_id"
                    ],
                    name=camera[
                        "name"
                    ],
                ).consume()


                for target in camera.get(
                    "monitors",
                    []
                ):

                    if target.startswith(
                        "ZONE-"
                    ):

                        session.run(
                            """
                            MATCH
                                (c:Camera {
                                    camera_id:
                                        $camera_id
                                }),
                                (target:Zone {
                                    zone_id:
                                        $target_id
                                })

                            MERGE
                                (c)-[:MONITORS]->
                                (target)
                            """,
                            camera_id=camera[
                                "camera_id"
                            ],
                            target_id=target,
                        ).consume()


                    elif target.startswith(
                        "DOOR-"
                    ):

                        session.run(
                            """
                            MATCH
                                (c:Camera {
                                    camera_id:
                                        $camera_id
                                }),
                                (target:AccessPoint {
                                    access_point_id:
                                        $target_id
                                })

                            MERGE
                                (c)-[:MONITORS]->
                                (target)
                            """,
                            camera_id=camera[
                                "camera_id"
                            ],
                            target_id=target,
                        ).consume()


            # ================================================
            # Racks and servers
            # ================================================

            for rack in zone.get(
                "racks",
                []
            ):

                rack_id = rack[
                    "rack_id"
                ]


                session.run(
                    """
                    MATCH (z:Zone {
                        zone_id: $zone_id
                    })

                    MERGE (r:Rack {
                        rack_id: $rack_id
                    })

                    SET r.name = $name

                    MERGE
                        (r)-[:LOCATED_IN]->(z)
                    """,
                    zone_id=zone_id,
                    rack_id=rack_id,
                    name=rack[
                        "name"
                    ],
                ).consume()


                for server in rack.get(
                    "servers",
                    []
                ):

                    session.run(
                        """
                        MATCH (r:Rack {
                            rack_id: $rack_id
                        })

                        MERGE (s:Server {
                            server_id: $server_id
                        })

                        SET
                            s.name = $name,
                            s.asset_type =
                                $asset_type,
                            s.criticality =
                                $criticality

                        MERGE
                            (s)-[:LOCATED_IN]->
                            (r)
                        """,
                        rack_id=rack_id,
                        server_id=server[
                            "server_id"
                        ],
                        name=server[
                            "name"
                        ],
                        asset_type=server[
                            "asset_type"
                        ],
                        criticality=server[
                            "criticality"
                        ],
                    ).consume()


            # ================================================
            # Equipment
            # ================================================

            for equipment in zone.get(
                "equipment",
                []
            ):

                session.run(
                    """
                    MATCH (z:Zone {
                        zone_id: $zone_id
                    })

                    MERGE (e:Equipment {
                        equipment_id:
                            $equipment_id
                    })

                    SET
                        e.name = $name,
                        e.asset_type =
                            $asset_type,
                        e.criticality =
                            $criticality

                    MERGE
                        (e)-[:LOCATED_IN]->(z)
                    """,
                    zone_id=zone_id,
                    equipment_id=equipment[
                        "equipment_id"
                    ],
                    name=equipment[
                        "name"
                    ],
                    asset_type=equipment[
                        "asset_type"
                    ],
                    criticality=equipment[
                        "criticality"
                    ],
                ).consume()


            # ================================================
            # Sensors
            # ================================================

            for sensor in zone.get(
                "sensors",
                []
            ):

                session.run(
                    """
                    MERGE (s:Sensor {
                        sensor_id: $sensor_id
                    })

                    SET
                        s.name = $name,
                        s.sensor_type =
                            $sensor_type
                    """,
                    sensor_id=sensor[
                        "sensor_id"
                    ],
                    name=sensor[
                        "name"
                    ],
                    sensor_type=sensor[
                        "sensor_type"
                    ],
                ).consume()


                for target in sensor.get(
                    "monitors",
                    []
                ):

                    if target.startswith(
                        "ZONE-"
                    ):

                        session.run(
                            """
                            MATCH
                                (s:Sensor {
                                    sensor_id:
                                        $sensor_id
                                }),
                                (target:Zone {
                                    zone_id:
                                        $target_id
                                })

                            MERGE
                                (s)-[:MONITORS]->
                                (target)
                            """,
                            sensor_id=sensor[
                                "sensor_id"
                            ],
                            target_id=target,
                        ).consume()


                    elif target.startswith(
                        "CHILLER-"
                    ):

                        session.run(
                            """
                            MATCH
                                (s:Sensor {
                                    sensor_id:
                                        $sensor_id
                                }),
                                (target:Equipment {
                                    equipment_id:
                                        $target_id
                                })

                            MERGE
                                (s)-[:MONITORS]->
                                (target)
                            """,
                            sensor_id=sensor[
                                "sensor_id"
                            ],
                            target_id=target,
                        ).consume()


        # ====================================================
        # People and authorization
        # ====================================================

        for person in topology.get(
            "people",
            []
        ):

            session.run(
                """
                MERGE (p:Person {
                    person_id: $person_id
                })

                SET p.role = $role
                """,
                person_id=person[
                    "person_id"
                ],
                role=person[
                    "role"
                ],
            ).consume()


            for zone_id in person[
                "authorized_zones"
            ]:

                session.run(
                    """
                    MATCH
                        (p:Person {
                            person_id:
                                $person_id
                        }),
                        (z:Zone {
                            zone_id:
                                $zone_id
                        })

                    MERGE
                        (p)-[:AUTHORIZED_FOR]->
                        (z)
                    """,
                    person_id=person[
                        "person_id"
                    ],
                    zone_id=zone_id,
                ).consume()


# ============================================================
# Summary
# ============================================================

def print_graph_summary(
    driver
):

    query = """
    MATCH (n)
    UNWIND labels(n) AS label
    RETURN
        label,
        count(*) AS count
    ORDER BY label
    """


    with driver.session(
        database=NEO4J_DATABASE
    ) as session:

        results = session.run(
            query
        )


        print(
            "\n============================================"
        )

        print(
            "NEO4J NODE SUMMARY"
        )

        print(
            "============================================"
        )


        for record in results:

            print(
                f"{record['label']:<15} "
                f"{record['count']}"
            )


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":

    print(
        "\n============================================"
    )

    print(
        "DC-GUARDIAN NEO4J TOPOLOGY LOADER"
    )

    print(
        "============================================"
    )


    validate_configuration()


    topology = load_json(
        TOPOLOGY_FILE
    )


    driver = GraphDatabase.driver(
        NEO4J_URI,
        auth=(
            NEO4J_USER,
            NEO4J_PASSWORD
        )
    )


    try:

        # ----------------------------------------------------
        # Verify connectivity
        # ----------------------------------------------------

        driver.verify_connectivity()

        print(
            "\nPASS: Connected to Neo4j."
        )


        # ----------------------------------------------------
        # Constraints
        # ----------------------------------------------------

        apply_schema(
            driver
        )

        print(
            "PASS: Graph constraints applied."
        )


        # ----------------------------------------------------
        # Load topology
        # ----------------------------------------------------

        load_topology_into_neo4j(
            driver,
            topology
        )

        print(
            "PASS: DC-01 topology loaded."
        )


        print_graph_summary(
            driver
        )


        print(
            "\n============================================"
        )

        print(
            "DC-GUARDIAN NEO4J "
            "TOPOLOGY LOAD PASSED"
        )

        print(
            "============================================"
        )


    finally:

        driver.close()
