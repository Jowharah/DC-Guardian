from pathlib import Path
import os

from dotenv import load_dotenv
from neo4j import GraphDatabase


# ============================================================
# Project / environment configuration
# ============================================================

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

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
# Configuration validation
# ============================================================

def validate_configuration():

    if not NEO4J_PASSWORD:
        raise ValueError(
            "NEO4J_PASSWORD is missing."
        )


# ============================================================
# Query helpers
# ============================================================

def relationship_exists(
    session,
    query,
    **parameters
):

    record = session.run(
        query,
        **parameters
    ).single()

    if record is None:
        return False

    return bool(
        record["exists"]
    )


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":

    print(
        "\n============================================"
    )
    print(
        "DC-GUARDIAN NEO4J GRAPH VALIDATION"
    )
    print(
        "============================================"
    )

    validate_configuration()

    driver = GraphDatabase.driver(
        NEO4J_URI,
        auth=(
            NEO4J_USER,
            NEO4J_PASSWORD
        )
    )

    try:

        driver.verify_connectivity()

        print(
            "\nPASS: Connected to Neo4j."
        )

        with driver.session(
            database=NEO4J_DATABASE
        ) as session:

            # =================================================
            # Test 1:
            # Server -> Rack -> Zone -> DataCenter
            # =================================================

            query = """
            MATCH
                (s:Server {
                    server_id: $server_id
                }),
                (r:Rack {
                    rack_id: $rack_id
                }),
                (z:Zone {
                    zone_id: $zone_id
                }),
                (dc:DataCenter {
                    data_center_id: $dc_id
                })

            RETURN EXISTS {
                MATCH
                    (s)-[:LOCATED_IN]->(r)
                    -[:LOCATED_IN]->(z)
                    -[:PART_OF]->(dc)
            } AS exists
            """

            result = relationship_exists(
                session,
                query,
                server_id="SRV-A1-01",
                rack_id="RACK-A1",
                zone_id="ZONE-A",
                dc_id="DC-01",
            )

            assert result is True

            print(
                "PASS: SRV-A1-01 -> "
                "RACK-A1 -> ZONE-A -> DC-01"
            )


            # =================================================
            # Test 2:
            # Critical Zone-B server
            # =================================================

            result = relationship_exists(
                session,
                query,
                server_id="SRV-B1-01",
                rack_id="RACK-B1",
                zone_id="ZONE-B",
                dc_id="DC-01",
            )

            assert result is True

            print(
                "PASS: SRV-B1-01 -> "
                "RACK-B1 -> ZONE-B -> DC-01"
            )


            # =================================================
            # Test 3:
            # P001 authorization
            # =================================================

            query = """
            MATCH
                (p:Person {
                    person_id: $person_id
                }),
                (z:Zone {
                    zone_id: $zone_id
                })

            RETURN EXISTS {
                MATCH
                    (p)-[:AUTHORIZED_FOR]->(z)
            } AS exists
            """

            for zone_id in [
                "ZONE-A",
                "ZONE-B",
            ]:

                result = relationship_exists(
                    session,
                    query,
                    person_id="P001",
                    zone_id=zone_id,
                )

                assert result is True

            print(
                "PASS: P001 authorized for "
                "ZONE-A and ZONE-B."
            )


            # =================================================
            # Test 4:
            # P001 should NOT be authorized for Zone C
            # =================================================

            result = relationship_exists(
                session,
                query,
                person_id="P001",
                zone_id="ZONE-C",
            )

            assert result is False

            print(
                "PASS: P001 is not authorized "
                "for ZONE-C."
            )


            # =================================================
            # Test 5:
            # Camera A monitoring
            # =================================================

            query = """
            MATCH
                (c:Camera {
                    camera_id: $camera_id
                }),
                (z:Zone {
                    zone_id: $zone_id
                })

            RETURN EXISTS {
                MATCH
                    (c)-[:MONITORS]->(z)
            } AS exists
            """

            result = relationship_exists(
                session,
                query,
                camera_id="CAM-A-01",
                zone_id="ZONE-A",
            )

            assert result is True


            query = """
            MATCH
                (c:Camera {
                    camera_id: $camera_id
                }),
                (a:AccessPoint {
                    access_point_id:
                        $access_point_id
                })

            RETURN EXISTS {
                MATCH
                    (c)-[:MONITORS]->(a)
            } AS exists
            """

            result = relationship_exists(
                session,
                query,
                camera_id="CAM-A-01",
                access_point_id="DOOR-A",
            )

            assert result is True

            print(
                "PASS: CAM-A-01 monitors "
                "ZONE-A and DOOR-A."
            )


            # =================================================
            # Test 6:
            # Cooling sensor
            # =================================================

            query = """
            MATCH
                (s:Sensor {
                    sensor_id: $sensor_id
                }),
                (z:Zone {
                    zone_id: $zone_id
                })

            RETURN EXISTS {
                MATCH
                    (s)-[:MONITORS]->(z)
            } AS exists
            """

            result = relationship_exists(
                session,
                query,
                sensor_id="SEN-C-01",
                zone_id="ZONE-C",
            )

            assert result is True


            query = """
            MATCH
                (s:Sensor {
                    sensor_id: $sensor_id
                }),
                (e:Equipment {
                    equipment_id:
                        $equipment_id
                })

            RETURN EXISTS {
                MATCH
                    (s)-[:MONITORS]->(e)
            } AS exists
            """

            result = relationship_exists(
                session,
                query,
                sensor_id="SEN-C-01",
                equipment_id="CHILLER-C1",
            )

            assert result is True

            print(
                "PASS: SEN-C-01 monitors "
                "ZONE-C and CHILLER-C1."
            )


            # =================================================
            # Test 7:
            # Negative topology relationship
            # =================================================

            query = """
            MATCH
                (s:Server {
                    server_id: $server_id
                }),
                (r:Rack {
                    rack_id: $rack_id
                })

            RETURN EXISTS {
                MATCH
                    (s)-[:LOCATED_IN]->(r)
            } AS exists
            """

            result = relationship_exists(
                session,
                query,
                server_id="SRV-A1-01",
                rack_id="RACK-B1",
            )

            assert result is False

            print(
                "PASS: Invalid relationship "
                "SRV-A1-01 -> RACK-B1 "
                "does not exist."
            )


            # =================================================
            # Test 8:
            # Expected node counts
            # =================================================

            expected_counts = {
                "DataCenter": 1,
                "Zone": 3,
                "Rack": 2,
                "Server": 4,
                "Camera": 3,
                "Sensor": 3,
                "AccessPoint": 3,
                "Equipment": 1,
                "Person": 3,
            }


            for label, expected in (
                expected_counts.items()
            ):

                # Label comes only from our fixed internal
                # dictionary above, not from user input.

                count_query = (
                    f"MATCH (n:{label}) "
                    f"RETURN count(n) AS count"
                )

                record = session.run(
                    count_query
                ).single()

                actual = record[
                    "count"
                ]

                if actual != expected:

                    raise AssertionError(
                        f"{label}: expected "
                        f"{expected}, found "
                        f"{actual}."
                    )


            print(
                "PASS: All expected node "
                "counts are correct."
            )


        # =====================================================
        # Final result
        # =====================================================

        print(
            "\n============================================"
        )
        print(
            "GRAPH VALIDATION SUMMARY"
        )
        print(
            "============================================"
        )

        print(
            "PASS: Physical hierarchy"
        )
        print(
            "PASS: Person authorization"
        )
        print(
            "PASS: Camera monitoring"
        )
        print(
            "PASS: Sensor monitoring"
        )
        print(
            "PASS: Negative relationship test"
        )
        print(
            "PASS: Node-count integrity"
        )

        print(
            "\n============================================"
        )
        print(
            "DC-GUARDIAN NEO4J GRAPH "
            "VALIDATION PASSED"
        )
        print(
            "============================================"
        )


    finally:

        driver.close()