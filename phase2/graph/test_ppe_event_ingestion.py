"""
DC-Guardian Phase 2
PPE Compliance Neo4j Ingestion Contract

Tests:
    COMPLIANT @ CAM-B-01
    NON_COMPLIANT @ CAM-B-01
    NO_PERSON @ CAM-B-01

Also verifies:
    - Event -> Camera observation
    - existing camera topology is reused
    - person_index remains event evidence only
    - no Person nodes are created
    - no IDENTIFIES relationship is created
    - authorization is not evaluated
    - repeated ingestion is idempotent
"""

from pathlib import Path
import json
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
    PROJECT_ROOT / "phase2" / "adapters",
    PROJECT_ROOT / "phase2" / "topology",
    PROJECT_ROOT / "phase2" / "graph",
]:

    if str(directory) not in sys.path:

        sys.path.insert(
            0,
            str(directory)
        )


# ============================================================
# Imports
# ============================================================

from ppe_event_adapter import (
    adapt_ppe_assessment,
)

from topology_mapper import (
    map_ppe_event_to_scenario,
)

from ingest_event import (
    create_driver,
    ingest_ppe_event,
    NEO4J_DATABASE,
)


# ============================================================
# Assessment builders
# ============================================================

def make_person(
    index,
    status,
    detected,
    not_detected,
):

    return {
        "person_index":
            index,

        "status":
            status,

        "required_ppe": [
            "helmet",
            "safety-vest",
        ],

        "required_ppe_detected":
            detected,

        "required_ppe_not_detected":
            not_detected,

        "optional_ppe_detected":
            [],

        "all_associated_classes":
            list(
                detected
            ),
    }


def make_assessment(
    status,
    people,
):

    return {
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
            bool(
                people
            ),

        "person_count":
            len(
                people
            ),

        "overall_status":
            status,

        "people":
            people,

        "detections":
            [],

        "unassigned_detections":
            [],

        "latency_ms":
            100.0,
    }


# ============================================================
# Event preparation
# ============================================================

def prepare_event(
    assessment,
    *,
    event_id,
    scenario_id,
    timestamp,
):

    normalized = adapt_ppe_assessment(
        assessment,

        dataset_name=
            "DC-Guardian Controlled PPE Dataset v1",

        source_type=
            "CONTROLLED_TEST",

        event_id=
            event_id,

        timestamp=
            timestamp,
    )


    return map_ppe_event_to_scenario(
        normalized,

        scenario_id=
            scenario_id,

        scenario_timestamp=
            timestamp,

        camera_id=
            "CAM-B-01",
    )


# ============================================================
# Controlled events
# ============================================================

compliant_event = prepare_event(
    make_assessment(
        "COMPLIANT",
        [
            make_person(
                0,
                "COMPLIANT",
                [
                    "helmet",
                    "safety-vest",
                ],
                [],
            )
        ],
    ),

    event_id=
        "EVT-PPE-GRAPH-COMPLIANT",

    scenario_id=
        "SCENARIO-PPE-GRAPH-COMPLIANT",

    timestamp=
        "2026-09-27T10:00:00Z",
)


non_compliant_event = prepare_event(
    make_assessment(
        "NON_COMPLIANT",
        [
            make_person(
                0,
                "COMPLIANT",
                [
                    "helmet",
                    "safety-vest",
                ],
                [],
            ),

            make_person(
                1,
                "NON_COMPLIANT",
                [
                    "helmet",
                ],
                [
                    "safety-vest",
                ],
            ),
        ],
    ),

    event_id=
        "EVT-PPE-GRAPH-NONCOMPLIANT",

    scenario_id=
        "SCENARIO-PPE-GRAPH-NONCOMPLIANT",

    timestamp=
        "2026-09-27T10:01:00Z",
)


no_person_event = prepare_event(
    make_assessment(
        "NO_PERSON",
        [],
    ),

    event_id=
        "EVT-PPE-GRAPH-NOPERSON",

    scenario_id=
        "SCENARIO-PPE-GRAPH-NOPERSON",

    timestamp=
        "2026-09-27T10:02:00Z",
)


print(
    "\n============================================"
)
print(
    "DC-GUARDIAN PPE EVENT INGESTION"
)
print(
    "============================================"
)


driver = create_driver()


try:

    print(
        "PASS: Connected to Neo4j."
    )


    # ========================================================
    # Clear previous PPE test Event artifacts only
    # ========================================================

    event_ids = [
        compliant_event[
            "event_id"
        ],

        non_compliant_event[
            "event_id"
        ],

        no_person_event[
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
        "PASS: Previous PPE test artifacts cleared."
    )


    # ========================================================
    # COMPLIANT
    # ========================================================

    compliant_result = ingest_ppe_event(
        compliant_event,
        driver,
    )


    assert (
        compliant_result[
            "state"
        ]
        == "PPE_COMPLIANT"
    )

    assert (
        compliant_result[
            "anomaly_detected"
        ]
        is False
    )

    assert (
        compliant_result[
            "camera_id"
        ]
        == "CAM-B-01"
    )

    assert (
        compliant_result[
            "zone_id"
        ]
        == "ZONE-B"
    )

    assert (
        compliant_result[
            "access_point_id"
        ]
        == "DOOR-B"
    )


    print(
        "PASS: COMPLIANT PPE event ingested."
    )


    # ========================================================
    # NON_COMPLIANT
    # ========================================================

    non_compliant_result = ingest_ppe_event(
        non_compliant_event,
        driver,
    )


    assert (
        non_compliant_result[
            "state"
        ]
        == "PPE_NON_COMPLIANT"
    )

    assert (
        non_compliant_result[
            "anomaly_detected"
        ]
        is True
    )

    assert (
        non_compliant_result[
            "person_count"
        ]
        == 2
    )

    assert (
        non_compliant_result[
            "people"
        ][1][
            "person_index"
        ]
        == 1
    )

    assert (
        non_compliant_result[
            "people"
        ][1][
            "required_ppe_not_detected"
        ]
        == [
            "safety-vest"
        ]
    )


    print(
        "PASS: NON_COMPLIANT PPE event ingested."
    )

    print(
        "PASS: Person-level PPE evidence preserved."
    )


    # ========================================================
    # NO_PERSON
    # ========================================================

    no_person_result = ingest_ppe_event(
        no_person_event,
        driver,
    )


    assert (
        no_person_result[
            "state"
        ]
        == "NO_PERSON_DETECTED"
    )

    assert (
        no_person_result[
            "person_count"
        ]
        == 0
    )

    assert (
        no_person_result[
            "person_detected"
        ]
        is False
    )


    print(
        "PASS: NO_PERSON PPE event ingested."
    )


    # ========================================================
    # Responsibility boundaries
    # ========================================================

    for result in [
        compliant_result,
        non_compliant_result,
        no_person_result,
    ]:

        assert (
            result[
                "employee_identity_evaluated"
            ]
            is False
        )

        assert (
            result[
                "authorization_evaluated"
            ]
            is False
        )


    print(
        "PASS: Employee identity remains unevaluated."
    )

    print(
        "PASS: Authorization remains unevaluated."
    )


    # ========================================================
    # Idempotency
    # ========================================================

    repeated = ingest_ppe_event(
        non_compliant_event,
        driver,
    )


    assert (
        repeated[
            "event_id"
        ]
        == non_compliant_result[
            "event_id"
        ]
    )


    print(
        "PASS: Repeated PPE ingestion completed."
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
                non_compliant_event[
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
                non_compliant_event[
                    "event_id"
                ],
        ).single()


        if context is None:

            raise AssertionError(
                "PPE observation safety context "
                "not found."
            )


        print(
            "PASS: Existing Camera -> Zone / "
            "AccessPoint topology reused."
        )


        # ====================================================
        # No IDENTIFIES relationship
        # ====================================================

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
                non_compliant_event[
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
            "PASS: PPE Event has no IDENTIFIES "
            "relationship."
        )


        # ====================================================
        # person_index must not create Person nodes
        #
        # Check IDs that a naive implementation might create.
        # ====================================================

        record = session.run(
            """
            OPTIONAL MATCH (person:Person)

            WHERE person.person_id
                IN [
                    "0",
                    "1",
                    "PERSON-0",
                    "PERSON-1"
                ]

            RETURN
                count(person)
                    AS synthetic_person_count
            """
        ).single()


        assert (
            record[
                "synthetic_person_count"
            ]
            == 0
        )


        print(
            "PASS: person_index did not create "
            "synthetic Person nodes."
        )


        # ====================================================
        # Persisted person evidence
        # ====================================================

        record = session.run(
            """
            MATCH (event:Event {
                event_id: $event_id
            })

            RETURN
                event.people_json
                    AS people_json,

                event.person_count
                    AS person_count,

                event.policy_version
                    AS policy_version
            """,

            event_id=
                non_compliant_event[
                    "event_id"
                ],
        ).single()


        people = json.loads(
            record[
                "people_json"
            ]
        )


        assert (
            record[
                "person_count"
            ]
            == 2
        )

        assert (
            record[
                "policy_version"
            ]
            == "PPE-POLICY-v1"
        )

        assert (
            people[
                1
            ][
                "required_ppe_not_detected"
            ]
            == [
                "safety-vest"
            ]
        )


        print(
            "PASS: Required-PPE-not-detected "
            "evidence persisted."
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
                non_compliant_event[
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
            == 0
        )


        print(
            "PASS: PPE Event and relationships "
            "are idempotent."
        )


    # ========================================================
    # Display
    # ========================================================

    print(
        "\n============================================"
    )
    print(
        "PPE -> SAFETY / PHYSICAL CONTEXT"
    )
    print(
        "============================================"
    )

    print(
        "COMPLIANT:"
    )
    print(
        "  Camera: CAM-B-01"
    )
    print(
        "  Zone: ZONE-B"
    )
    print(
        "  State: PPE_COMPLIANT"
    )


    print(
        "\nNON_COMPLIANT:"
    )
    print(
        "  Camera: CAM-B-01"
    )
    print(
        "  Zone: ZONE-B"
    )
    print(
        "  Persons: 2"
    )
    print(
        "  Person 1: safety-vest not detected"
    )
    print(
        "  State: PPE_NON_COMPLIANT"
    )


    print(
        "\nNO_PERSON:"
    )
    print(
        "  Camera: CAM-B-01"
    )
    print(
        "  Zone: ZONE-B"
    )
    print(
        "  Persons: 0"
    )
    print(
        "  State: NO_PERSON_DETECTED"
    )


    # ========================================================
    # Final
    # ========================================================

    print(
        "\n============================================"
    )
    print(
        "PPE EVENT INGESTION CONTRACT SUMMARY"
    )
    print(
        "============================================"
    )

    print(
        "PASS: SAFETY Event ingestion."
    )

    print(
        "PASS: COMPLIANT distinction."
    )

    print(
        "PASS: NON_COMPLIANT distinction."
    )

    print(
        "PASS: NO_PERSON distinction."
    )

    print(
        "PASS: Event -> Camera observation."
    )

    print(
        "PASS: Existing camera topology reused."
    )

    print(
        "PASS: Person-level PPE evidence preserved."
    )

    print(
        "PASS: No synthetic Person identity."
    )

    print(
        "PASS: No IDENTIFIES relationship."
    )

    print(
        "PASS: Authorization not evaluated."
    )

    print(
        "PASS: Ingestion idempotent."
    )


    print(
        "\n============================================"
    )
    print(
        "DC-GUARDIAN PPE EVENT INGESTION PASSED"
    )
    print(
        "============================================"
    )


finally:

    driver.close()