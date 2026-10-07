"""
DC-Guardian Phase 2
Face Recognition Neo4j Ingestion Contract

Tests:
    P001 @ CAM-B-01   -> AUTHORIZED
    P003 @ CAM-B-01   -> UNAUTHORIZED
    P004 @ CAM-B-01   -> AUTHORIZATION_UNKNOWN
    UNKNOWN @ CAM-B-01 -> NOT_APPLICABLE

Also verifies:
    - Event -> Camera observation
    - Event -> Person only for existing recognized identities
    - no Person:UNKNOWN node
    - topology relationships are reused
    - repeated ingestion is idempotent
"""

from pathlib import Path
import sys


# ============================================================
# Project paths
# ============================================================

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)


for directory in [
    PROJECT_ROOT,
    PROJECT_ROOT / "reasoning" / "adapters",
    PROJECT_ROOT / "reasoning" / "topology",
    PROJECT_ROOT / "reasoning" / "graph",
]:

    if str(directory) not in sys.path:

        sys.path.insert(
            0,
            str(directory)
        )


# ============================================================
# Imports
# ============================================================

from face_event_adapter import (
    adapt_face_assessment,
)

from topology_mapper import (
    map_face_event_to_scenario,
)

from ingest_event import (
    create_driver,
    ingest_face_event,
    NEO4J_DATABASE,
)


# ============================================================
# Controlled assessment builders
# ============================================================

def make_recognized_assessment(
    person_id,
    *,
    distance=0.25,
):

    return {
        "domain":
            "PHYSICAL_SECURITY",

        "event_type":
            "FACE_IDENTIFICATION_ASSESSMENT",

        "image":
            f"{person_id}_graph_test.jpg",

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
            distance,

        "similarity":
            1.0 - distance,

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
            "UNKNOWN_graph_test.jpg",

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


# ============================================================
# Event preparation helper
# ============================================================

def prepare_event(
    assessment,
    *,
    event_id,
    scenario_id,
    timestamp,
):

    normalized = adapt_face_assessment(
        assessment,

        dataset_name=
            "DC-Guardian Controlled Face Dataset v1",

        source_type=
            "CONTROLLED_TEST",

        event_id=
            event_id,

        timestamp=
            timestamp,
    )


    mapped = map_face_event_to_scenario(
        normalized,

        scenario_id=
            scenario_id,

        scenario_timestamp=
            timestamp,

        camera_id=
            "CAM-B-01",
    )


    return mapped


# ============================================================
# Controlled events
# ============================================================

p001_event = prepare_event(
    make_recognized_assessment(
        "P001"
    ),

    event_id=
        "EVT-FACE-GRAPH-P001",

    scenario_id=
        "SCENARIO-FACE-GRAPH-P001",

    timestamp=
        "2026-09-24T15:00:00Z",
)


p003_event = prepare_event(
    make_recognized_assessment(
        "P003"
    ),

    event_id=
        "EVT-FACE-GRAPH-P003",

    scenario_id=
        "SCENARIO-FACE-GRAPH-P003",

    timestamp=
        "2026-09-24T15:01:00Z",
)


p004_event = prepare_event(
    make_recognized_assessment(
        "P004"
    ),

    event_id=
        "EVT-FACE-GRAPH-P004",

    scenario_id=
        "SCENARIO-FACE-GRAPH-P004",

    timestamp=
        "2026-09-24T15:02:00Z",
)


unknown_event = prepare_event(
    make_unknown_assessment(),

    event_id=
        "EVT-FACE-GRAPH-UNKNOWN",

    scenario_id=
        "SCENARIO-FACE-GRAPH-UNKNOWN",

    timestamp=
        "2026-09-24T15:03:00Z",
)


print(
    "\n============================================"
)
print(
    "DC-GUARDIAN FACE EVENT INGESTION"
)
print(
    "============================================"
)


# ============================================================
# Neo4j
# ============================================================

driver = create_driver()


try:

    print(
        "PASS: Connected to Neo4j."
    )


    # ========================================================
    # Clear previous test Event artifacts only
    #
    # Do NOT delete Person/Camera/topology nodes.
    # ========================================================

    event_ids = [
        p001_event[
            "event_id"
        ],

        p003_event[
            "event_id"
        ],

        p004_event[
            "event_id"
        ],

        unknown_event[
            "event_id"
        ],
    ]


    with driver.session(
        database=NEO4J_DATABASE
    ) as session:

        session.run(
            """
            MATCH (event:Event)

            WHERE event.event_id
                IN $event_ids

            DETACH DELETE event
            """,

            event_ids=
                event_ids,
        ).consume()


    print(
        "PASS: Previous Face test artifacts cleared."
    )


    # ========================================================
    # P001 -> AUTHORIZED
    # ========================================================

    p001_result = ingest_face_event(
        p001_event,
        driver,
    )


    assert (
        p001_result[
            "person_id"
        ]
        == "P001"
    )

    assert (
        p001_result[
            "camera_id"
        ]
        == "CAM-B-01"
    )

    assert (
        p001_result[
            "zone_id"
        ]
        == "ZONE-B"
    )

    assert (
        p001_result[
            "access_point_id"
        ]
        == "DOOR-B"
    )

    assert (
        p001_result[
            "authorization_status"
        ]
        == "AUTHORIZED"
    )


    print(
        "PASS: P001 Face event ingested."
    )

    print(
        "PASS: P001 @ ZONE-B -> AUTHORIZED."
    )


    # ========================================================
    # P003 -> UNAUTHORIZED
    # ========================================================

    p003_result = ingest_face_event(
        p003_event,
        driver,
    )


    assert (
        p003_result[
            "person_id"
        ]
        == "P003"
    )

    assert (
        p003_result[
            "authorization_status"
        ]
        == "UNAUTHORIZED"
    )


    print(
        "PASS: P003 Face event ingested."
    )

    print(
        "PASS: P003 @ ZONE-B -> UNAUTHORIZED."
    )


    # ========================================================
    # P004 -> AUTHORIZATION_UNKNOWN
    #
    # P004 is enrolled in Face Recognition but is not
    # represented in the current synthetic topology.
    # ========================================================

    p004_result = ingest_face_event(
        p004_event,
        driver,
    )


    assert (
        p004_result[
            "person_id"
        ]
        == "P004"
    )

    assert (
        p004_result[
            "authorization_status"
        ]
        == "AUTHORIZATION_UNKNOWN"
    )


    print(
        "PASS: P004 Face event ingested."
    )

    print(
        "PASS: P004 missing topology identity -> "
        "AUTHORIZATION_UNKNOWN."
    )


    # ========================================================
    # UNKNOWN -> NOT_APPLICABLE
    # ========================================================

    unknown_result = ingest_face_event(
        unknown_event,
        driver,
    )


    assert (
        unknown_result[
            "person_id"
        ]
        == "UNKNOWN"
    )

    assert (
        unknown_result[
            "state"
        ]
        == "UNKNOWN_PERSON"
    )

    assert (
        unknown_result[
            "authorization_status"
        ]
        == "NOT_APPLICABLE"
    )


    print(
        "PASS: UNKNOWN Face event ingested."
    )

    print(
        "PASS: UNKNOWN authorization -> "
        "NOT_APPLICABLE."
    )


    # ========================================================
    # Idempotency
    # ========================================================

    repeated = ingest_face_event(
        p001_event,
        driver,
    )


    assert (
        repeated[
            "event_id"
        ]
        == p001_result[
            "event_id"
        ]
    )


    print(
        "PASS: Repeated Face ingestion completed."
    )


    # ========================================================
    # Graph verification
    # ========================================================

    with driver.session(
        database=NEO4J_DATABASE
    ) as session:


        # ====================================================
        # Event -> Camera
        # ====================================================

        record = session.run(
            """
            MATCH
                (event:Event {
                    event_id: $event_id
                })
                -[r:OBSERVED_BY]->
                (camera:Camera {
                    camera_id: "CAM-B-01"
                })

            RETURN
                count(r)
                    AS relationship_count
            """,

            event_id=
                p001_event[
                    "event_id"
                ],
        ).single()


        assert (
            record[
                "relationship_count"
            ]
            == 1
        )


        print(
            "PASS: Event -> OBSERVED_BY -> Camera "
            "relationship verified."
        )


        # ====================================================
        # Existing recognized Person relationship
        # ====================================================

        record = session.run(
            """
            MATCH
                (event:Event {
                    event_id: $event_id
                })
                -[r:IDENTIFIES]->
                (person:Person {
                    person_id: "P001"
                })

            RETURN
                count(r)
                    AS relationship_count
            """,

            event_id=
                p001_event[
                    "event_id"
                ],
        ).single()


        assert (
            record[
                "relationship_count"
            ]
            == 1
        )


        print(
            "PASS: Recognized Event -> Person "
            "relationship verified."
        )


        # ====================================================
        # P003 is also a real topology Person
        # ====================================================

        record = session.run(
            """
            MATCH
                (event:Event {
                    event_id: $event_id
                })
                -[:IDENTIFIES]->
                (person:Person {
                    person_id: "P003"
                })

            RETURN
                count(person)
                    AS person_count
            """,

            event_id=
                p003_event[
                    "event_id"
                ],
        ).single()


        assert (
            record[
                "person_count"
            ]
            == 1
        )


        print(
            "PASS: P003 identity graph link preserved."
        )


        # ====================================================
        # P004 must NOT be invented as a Person node
        # ====================================================

        record = session.run(
            """
            OPTIONAL MATCH (person:Person {
                person_id: "P004"
            })

            RETURN
                count(person)
                    AS person_count
            """
        ).single()


        assert (
            record[
                "person_count"
            ]
            == 0
        )


        record = session.run(
            """
            MATCH (event:Event {
                event_id: $event_id
            })

            OPTIONAL MATCH
                (event)-[r:IDENTIFIES]->(:Person)

            RETURN
                count(r)
                    AS identifies_count
            """,

            event_id=
                p004_event[
                    "event_id"
                ],
        ).single()


        assert (
            record[
                "identifies_count"
            ]
            == 0
        )


        print(
            "PASS: Missing P004 topology identity "
            "was not invented."
        )


        # ====================================================
        # UNKNOWN must NOT become Person node
        # ====================================================

        record = session.run(
            """
            OPTIONAL MATCH (person:Person {
                person_id: "UNKNOWN"
            })

            RETURN
                count(person)
                    AS person_count
            """
        ).single()


        assert (
            record[
                "person_count"
            ]
            == 0
        )


        record = session.run(
            """
            MATCH (event:Event {
                event_id: $event_id
            })

            OPTIONAL MATCH
                (event)-[r:IDENTIFIES]->(:Person)

            RETURN
                count(r)
                    AS identifies_count
            """,

            event_id=
                unknown_event[
                    "event_id"
                ],
        ).single()


        assert (
            record[
                "identifies_count"
            ]
            == 0
        )


        print(
            "PASS: No Person:UNKNOWN node created."
        )

        print(
            "PASS: UNKNOWN event has no IDENTIFIES "
            "relationship."
        )


        # ====================================================
        # Camera topology reused
        # ====================================================

        context = session.run(
            """
            MATCH
                (event:Event {
                    event_id: $event_id
                })
                -[:OBSERVED_BY]->
                (camera:Camera {
                    camera_id: "CAM-B-01"
                })

            MATCH
                (camera)
                -[:MONITORS]->
                (zone:Zone {
                    zone_id: "ZONE-B"
                })

            MATCH
                (camera)
                -[:MONITORS]->
                (access:AccessPoint {
                    access_point_id: "DOOR-B"
                })

            RETURN
                camera.camera_id
                    AS camera_id,

                zone.zone_id
                    AS zone_id,

                access.access_point_id
                    AS access_point_id
            """,

            event_id=
                p001_event[
                    "event_id"
                ],
        ).single()


        if context is None:

            raise AssertionError(
                "Face observation physical context "
                "not found."
            )


        print(
            "PASS: Existing Camera -> Zone / "
            "AccessPoint topology reused."
        )


        # ====================================================
        # Authorization relationships remain graph-derived
        # ====================================================

        authorized = session.run(
            """
            MATCH
                (person:Person {
                    person_id: "P001"
                })
                -[:AUTHORIZED_FOR]->
                (zone:Zone {
                    zone_id: "ZONE-B"
                })

            RETURN
                count(zone)
                    AS count
            """
        ).single()


        assert (
            authorized[
                "count"
            ]
            == 1
        )


        unauthorized = session.run(
            """
            MATCH (person:Person {
                person_id: "P003"
            })

            MATCH (zone:Zone {
                zone_id: "ZONE-B"
            })

            OPTIONAL MATCH
                (person)
                -[r:AUTHORIZED_FOR]->
                (zone)

            RETURN
                count(r)
                    AS count
            """
        ).single()


        assert (
            unauthorized[
                "count"
            ]
            == 0
        )


        print(
            "PASS: Authorization remains "
            "graph-derived."
        )


        # ====================================================
        # Event/relationship idempotency
        # ====================================================

        record = session.run(
            """
            MATCH (event:Event {
                event_id: $event_id
            })

            OPTIONAL MATCH
                (event)-[observed:OBSERVED_BY]->
                (:Camera)

            OPTIONAL MATCH
                (event)-[identified:IDENTIFIES]->
                (:Person)

            RETURN
                count(
                    DISTINCT event
                )
                    AS event_count,

                count(
                    DISTINCT observed
                )
                    AS observed_count,

                count(
                    DISTINCT identified
                )
                    AS identifies_count
            """,

            event_id=
                p001_event[
                    "event_id"
                ],
        ).single()


        assert (
            record[
                "event_count"
            ]
            == 1
        )

        assert (
            record[
                "observed_count"
            ]
            == 1
        )

        assert (
            record[
                "identifies_count"
            ]
            == 1
        )


        print(
            "PASS: Face Event and relationships "
            "are idempotent."
        )


    # ========================================================
    # Display
    # ========================================================

    print(
        "\n============================================"
    )
    print(
        "FACE -> PHYSICAL / AUTHORIZATION CONTEXT"
    )
    print(
        "============================================"
    )


    print(
        "P001:"
    )
    print(
        "  Camera: CAM-B-01"
    )
    print(
        "  Zone: ZONE-B"
    )
    print(
        "  Authorization:",
        p001_result[
            "authorization_status"
        ],
    )


    print(
        "\nP003:"
    )
    print(
        "  Camera: CAM-B-01"
    )
    print(
        "  Zone: ZONE-B"
    )
    print(
        "  Authorization:",
        p003_result[
            "authorization_status"
        ],
    )


    print(
        "\nP004:"
    )
    print(
        "  Recognized by Face model"
    )
    print(
        "  Person topology node: absent"
    )
    print(
        "  Authorization:",
        p004_result[
            "authorization_status"
        ],
    )


    print(
        "\nUNKNOWN:"
    )
    print(
        "  Camera: CAM-B-01"
    )
    print(
        "  Zone: ZONE-B"
    )
    print(
        "  Person node: none"
    )
    print(
        "  Authorization:",
        unknown_result[
            "authorization_status"
        ],
    )


    # ========================================================
    # Final
    # ========================================================

    print(
        "\n============================================"
    )
    print(
        "FACE EVENT INGESTION CONTRACT SUMMARY"
    )
    print(
        "============================================"
    )

    print(
        "PASS: Recognized Face ingestion."
    )

    print(
        "PASS: Unknown Face ingestion."
    )

    print(
        "PASS: Event -> Camera observation."
    )

    print(
        "PASS: Existing Person identity links."
    )

    print(
        "PASS: No synthetic UNKNOWN Person."
    )

    print(
        "PASS: No synthetic P004 Person."
    )

    print(
        "PASS: AUTHORIZED distinction."
    )

    print(
        "PASS: UNAUTHORIZED distinction."
    )

    print(
        "PASS: AUTHORIZATION_UNKNOWN distinction."
    )

    print(
        "PASS: NOT_APPLICABLE distinction."
    )

    print(
        "PASS: Graph topology reused."
    )

    print(
        "PASS: Ingestion idempotent."
    )


    print(
        "\n============================================"
    )
    print(
        "DC-GUARDIAN FACE EVENT INGESTION PASSED"
    )
    print(
        "============================================"
    )


finally:

    driver.close()
