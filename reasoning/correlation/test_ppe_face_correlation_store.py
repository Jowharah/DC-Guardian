"""
DC-Guardian Reasoning
PPE Safety + Physical-Security Correlation Persistence Contract

Prerequisite:
    test_ppe_face_correlation.py has already created the
    controlled PPE + Face scenario events.

Verifies:
    - correlation rediscovery
    - deterministic persistence
    - idempotent Correlation node
    - two contributing Event relationships
    - ZONE-B infrastructure concern
    - PPE safety context preserved
    - unauthorized physical-security context preserved
    - PPE -> Camera -> Zone path remains explainable
    - Face -> Camera -> Zone path remains explainable
    - no cross-model person identity claim is introduced
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
    PROJECT_ROOT / "reasoning" / "graph",
    PROJECT_ROOT / "reasoning" / "correlation",
]:

    if str(directory) not in sys.path:

        sys.path.insert(
            0,
            str(directory)
        )


# ============================================================
# Imports
# ============================================================

from ingest_event import (
    create_driver,
    NEO4J_DATABASE,
)

from correlation_engine import (
    find_cross_domain_correlations,
)

from correlation_store import (
    persist_correlation,
)


# ============================================================
# Controlled scenario
#
# Created by test_ppe_face_correlation.py
# ============================================================

SCENARIO_ID = (
    "SCENARIO-CORR-PPE-FACE-001"
)


print(
    "\n============================================"
)
print(
    "DC-GUARDIAN PPE + FACE CORRELATION STORE"
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
    # Rediscover correlation
    # ========================================================

    correlations = (
        find_cross_domain_correlations(
            driver,

            scenario_id=
                SCENARIO_ID,

            window_minutes=
                15,
        )
    )


    if len(
        correlations
    ) != 1:

        raise AssertionError(
            "Expected exactly one PPE + Face "
            "correlation for "
            f"{SCENARIO_ID}; "
            f"found {len(correlations)}."
        )


    correlation = (
        correlations[
            0
        ]
    )


    assert (
        correlation[
            "correlation_type"
        ]
        == "CORRELATED_INFRASTRUCTURE_RISK"
    )


    assert (
        correlation[
            "scope"
        ]
        == "ZONE"
    )


    assert (
        correlation[
            "shared_entity_id"
        ]
        == "ZONE-B"
    )


    domains = {
        event[
            "domain"
        ]
        for event
        in correlation[
            "events"
        ]
    }


    assert domains == {
        "SAFETY",
        "PHYSICAL_SECURITY",
    }


    print(
        "PASS: PPE + Face correlation rediscovered."
    )

    print(
        "PASS: Common scope = ZONE-B."
    )


    # ========================================================
    # Verify semantics before persistence
    # ========================================================

    safety_event = next(
        event
        for event
        in correlation[
            "events"
        ]
        if (
            event[
                "domain"
            ]
            == "SAFETY"
        )
    )


    physical_event = next(
        event
        for event
        in correlation[
            "events"
        ]
        if (
            event[
                "domain"
            ]
            == "PHYSICAL_SECURITY"
        )
    )


    assert (
        safety_event[
            "state"
        ]
        == "PPE_NON_COMPLIANT"
    )


    assert (
        physical_event[
            "state"
        ]
        == "RECOGNIZED_PERSON"
    )


    assert (
        physical_event[
            "authorization_status"
        ]
        == "UNAUTHORIZED"
    )


    print(
        "PASS: PPE non-compliance evidence preserved."
    )

    print(
        "PASS: Unauthorized physical-security "
        "evidence preserved."
    )


    # ========================================================
    # Remove previous persisted correlation only
    #
    # Contributing Event nodes remain untouched.
    # ========================================================

    with driver.session(
        database=NEO4J_DATABASE
    ) as session:

        session.run(
            """
            MATCH (c:Correlation {
                scenario_id: $scenario_id
            })

            DETACH DELETE c
            """,

            scenario_id=
                SCENARIO_ID,
        ).consume()


    print(
        "PASS: Previous persisted PPE + Face "
        "correlation cleared."
    )


    # ========================================================
    # Persist
    # ========================================================

    result = persist_correlation(
        correlation,
        driver,
    )


    assert (
        result[
            "correlation_type"
        ]
        == "CORRELATED_INFRASTRUCTURE_RISK"
    )


    assert (
        result[
            "scope"
        ]
        == "ZONE"
    )


    assert (
        result[
            "shared_entity_id"
        ]
        == "ZONE-B"
    )


    assert (
        result[
            "event_count"
        ]
        == 2
    )


    assert set(
        result[
            "domains"
        ]
    ) == {
        "SAFETY",
        "PHYSICAL_SECURITY",
    }


    print(
        "PASS: PPE + Face correlation persisted."
    )


    # ========================================================
    # Deterministic / idempotent persistence
    # ========================================================

    second_result = persist_correlation(
        correlation,
        driver,
    )


    assert (
        second_result[
            "correlation_id"
        ]
        == result[
            "correlation_id"
        ]
    )


    print(
        "PASS: Repeated persistence uses "
        "deterministic correlation ID."
    )


    # ========================================================
    # Graph verification
    # ========================================================

    with driver.session(
        database=NEO4J_DATABASE
    ) as session:


        # ----------------------------------------------------
        # Exactly one Correlation node
        # ----------------------------------------------------

        record = session.run(
            """
            MATCH (c:Correlation {
                correlation_id: $correlation_id
            })

            RETURN
                count(c)
                    AS count,

                c.correlation_type
                    AS correlation_type,

                c.scope
                    AS scope,

                c.shared_entity_id
                    AS shared_entity_id,

                c.event_count
                    AS event_count,

                c.domains
                    AS domains
            """,

            correlation_id=
                result[
                    "correlation_id"
                ],
        ).single()


        assert (
            record[
                "count"
            ]
            == 1
        )


        assert (
            record[
                "correlation_type"
            ]
            == "CORRELATED_INFRASTRUCTURE_RISK"
        )


        assert (
            record[
                "scope"
            ]
            == "ZONE"
        )


        assert (
            record[
                "shared_entity_id"
            ]
            == "ZONE-B"
        )


        assert (
            record[
                "event_count"
            ]
            == 2
        )


        assert set(
            record[
                "domains"
            ]
        ) == {
            "SAFETY",
            "PHYSICAL_SECURITY",
        }


        print(
            "PASS: PPE + Face Correlation node "
            "is idempotent."
        )


        # ----------------------------------------------------
        # Exactly two contributing Events
        # ----------------------------------------------------

        record = session.run(
            """
            MATCH
                (event:Event)
                -[relationship:CONTRIBUTES_TO]->
                (correlation:Correlation {
                    correlation_id: $correlation_id
                })

            RETURN
                count(relationship)
                    AS relationship_count,

                collect(
                    DISTINCT event.domain
                )
                    AS domains,

                collect(
                    DISTINCT event.event_id
                )
                    AS event_ids
            """,

            correlation_id=
                result[
                    "correlation_id"
                ],
        ).single()


        assert (
            record[
                "relationship_count"
            ]
            == 2
        )


        assert set(
            record[
                "domains"
            ]
        ) == {
            "SAFETY",
            "PHYSICAL_SECURITY",
        }


        print(
            "PASS: Two contributing events linked."
        )


        # ----------------------------------------------------
        # Correlation -> ZONE-B
        # ----------------------------------------------------

        record = session.run(
            """
            MATCH
                (correlation:Correlation {
                    correlation_id: $correlation_id
                })
                -[relationship:CONCERNS]->
                (zone:Zone)

            RETURN
                count(relationship)
                    AS relationship_count,

                collect(
                    zone.zone_id
                )
                    AS zone_ids
            """,

            correlation_id=
                result[
                    "correlation_id"
                ],
        ).single()


        assert (
            record[
                "relationship_count"
            ]
            == 1
        )


        assert (
            record[
                "zone_ids"
            ]
            == [
                "ZONE-B"
            ]
        )


        print(
            "PASS: Correlation CONCERNS ZONE-B."
        )


        # ----------------------------------------------------
        # Full explainable PPE + Face graph
        # ----------------------------------------------------

        context = session.run(
            """
            MATCH
                (safety:Event {
                    domain:
                        "SAFETY"
                })
                -[:CONTRIBUTES_TO]->
                (correlation:Correlation {
                    correlation_id:
                        $correlation_id
                })
                <-[:CONTRIBUTES_TO]-
                (physical:Event {
                    domain:
                        "PHYSICAL_SECURITY"
                })


            // -----------------------------------------------
            // Shared correlation concern
            // -----------------------------------------------

            MATCH
                (correlation)
                -[:CONCERNS]->
                (shared_zone:Zone {
                    zone_id:
                        "ZONE-B"
                })


            // -----------------------------------------------
            // PPE safety evidence path
            // -----------------------------------------------

            MATCH
                (safety)
                -[:OBSERVED_BY]->
                (ppe_camera:Camera {
                    camera_id:
                        "CAM-B-01"
                })

            MATCH
                (ppe_camera)
                -[:MONITORS]->
                (safety_zone:Zone {
                    zone_id:
                        "ZONE-B"
                })


            // -----------------------------------------------
            // Face physical-security evidence path
            // -----------------------------------------------

            MATCH
                (physical)
                -[:OBSERVED_BY]->
                (face_camera:Camera {
                    camera_id:
                        "CAM-B-01"
                })

            MATCH
                (face_camera)
                -[:MONITORS]->
                (physical_zone:Zone {
                    zone_id:
                        "ZONE-B"
                })


            MATCH
                (physical)
                -[:IDENTIFIES]->
                (person:Person {
                    person_id:
                        "P003"
                })


            RETURN
                correlation.correlation_type
                    AS correlation_type,

                correlation.scope
                    AS scope,

                correlation.shared_entity_id
                    AS shared_entity_id,

                safety.state
                    AS safety_state,

                safety.ppe_status
                    AS ppe_status,

                safety.person_count
                    AS ppe_person_count,

                safety.people_json
                    AS ppe_people_json,

                ppe_camera.camera_id
                    AS ppe_camera_id,

                safety_zone.zone_id
                    AS safety_zone_id,

                physical.state
                    AS physical_state,

                physical.authorization_status
                    AS authorization_status,

                person.person_id
                    AS person_id,

                face_camera.camera_id
                    AS face_camera_id,

                physical_zone.zone_id
                    AS physical_zone_id,

                shared_zone.zone_id
                    AS shared_zone_id
            """,

            correlation_id=
                result[
                    "correlation_id"
                ],
        ).single()


        if context is None:

            raise AssertionError(
                "Explainable PPE + Face "
                "correlation path not found."
            )


        # ----------------------------------------------------
        # PPE semantics
        # ----------------------------------------------------

        assert (
            context[
                "safety_state"
            ]
            == "PPE_NON_COMPLIANT"
        )


        assert (
            context[
                "ppe_status"
            ]
            == "NON_COMPLIANT"
        )


        assert (
            context[
                "ppe_person_count"
            ]
            == 1
        )


        assert (
            context[
                "ppe_camera_id"
            ]
            == "CAM-B-01"
        )


        assert (
            context[
                "safety_zone_id"
            ]
            == "ZONE-B"
        )


        # ----------------------------------------------------
        # Face semantics
        # ----------------------------------------------------

        assert (
            context[
                "physical_state"
            ]
            == "RECOGNIZED_PERSON"
        )


        assert (
            context[
                "authorization_status"
            ]
            == "UNAUTHORIZED"
        )


        assert (
            context[
                "person_id"
            ]
            == "P003"
        )


        assert (
            context[
                "face_camera_id"
            ]
            == "CAM-B-01"
        )


        assert (
            context[
                "physical_zone_id"
            ]
            == "ZONE-B"
        )


        # ----------------------------------------------------
        # Correlation semantics
        # ----------------------------------------------------

        assert (
            context[
                "scope"
            ]
            == "ZONE"
        )


        assert (
            context[
                "shared_entity_id"
            ]
            == "ZONE-B"
        )


        assert (
            context[
                "shared_zone_id"
            ]
            == "ZONE-B"
        )


        print(
            "PASS: Explainable PPE + Face "
            "graph path verified."
        )


        # ----------------------------------------------------
        # Critical identity boundary
        #
        # PPE Event must NOT identify P003 or any Person.
        # ----------------------------------------------------

        record = session.run(
            """
            MATCH
                (safety:Event {
                    event_id:
                        $safety_event_id
                })

            OPTIONAL MATCH
                (safety)
                -[relationship:IDENTIFIES]->
                (person:Person)

            RETURN
                count(relationship)
                    AS identifies_count
            """,

            safety_event_id=
                safety_event[
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
            "PASS: PPE event has no Person "
            "identity relationship."
        )


        # ----------------------------------------------------
        # Both evidence paths share infrastructure context,
        # not asserted human identity.
        # ----------------------------------------------------

        assert (
            context[
                "ppe_camera_id"
            ]
            == context[
                "face_camera_id"
            ]
            == "CAM-B-01"
        )


        assert (
            context[
                "safety_zone_id"
            ]
            == context[
                "physical_zone_id"
            ]
            == context[
                "shared_zone_id"
            ]
            == "ZONE-B"
        )


        print(
            "PASS: Correlation is based on shared "
            "camera/zone context, not person identity."
        )


        # ====================================================
        # Display
        # ====================================================

        print(
            "\n============================================"
        )
        print(
            "PERSISTED PPE + FACE CONTEXT"
        )
        print(
            "============================================"
        )


        print(
            "Correlation ID:",
            result[
                "correlation_id"
            ],
        )


        print(
            "Type:",
            context[
                "correlation_type"
            ],
        )


        print(
            "Scope:",
            context[
                "scope"
            ],
        )


        print(
            "Shared zone:",
            context[
                "shared_zone_id"
            ],
        )


        print(
            "\nSafety / PPE:"
        )

        print(
            "  State:",
            context[
                "safety_state"
            ],
        )

        print(
            "  PPE status:",
            context[
                "ppe_status"
            ],
        )

        print(
            "  Persons:",
            context[
                "ppe_person_count"
            ],
        )

        print(
            "  Camera:",
            context[
                "ppe_camera_id"
            ],
        )

        print(
            "  Zone:",
            context[
                "safety_zone_id"
            ],
        )


        print(
            "\nPhysical Security / Face:"
        )

        print(
            "  Person:",
            context[
                "person_id"
            ],
        )

        print(
            "  State:",
            context[
                "physical_state"
            ],
        )

        print(
            "  Authorization:",
            context[
                "authorization_status"
            ],
        )

        print(
            "  Camera:",
            context[
                "face_camera_id"
            ],
        )

        print(
            "  Zone:",
            context[
                "physical_zone_id"
            ],
        )


    # ========================================================
    # Summary
    # ========================================================

    print(
        "\n============================================"
    )
    print(
        "PPE + FACE STORE CONTRACT SUMMARY"
    )
    print(
        "============================================"
    )

    print(
        "PASS: PPE + Face correlation persisted."
    )

    print(
        "PASS: Deterministic correlation ID."
    )

    print(
        "PASS: Persistence idempotent."
    )

    print(
        "PASS: Two evidence events preserved."
    )

    print(
        "PASS: SAFETY preserved."
    )

    print(
        "PASS: PHYSICAL_SECURITY preserved."
    )

    print(
        "PASS: PPE_NON_COMPLIANT preserved."
    )

    print(
        "PASS: UNAUTHORIZED context preserved."
    )

    print(
        "PASS: ZONE-level concern preserved."
    )

    print(
        "PASS: PPE Camera observation path preserved."
    )

    print(
        "PASS: Face Camera observation path preserved."
    )

    print(
        "PASS: No PPE -> Person identity link introduced."
    )

    print(
        "PASS: Shared physical context preserved "
        "without cross-model identity claim."
    )

    print(
        "PASS: Explainable graph path available."
    )


    print(
        "\n============================================"
    )
    print(
        "DC-GUARDIAN PPE + FACE "
        "CORRELATION STORE PASSED"
    )
    print(
        "============================================"
    )


finally:

    driver.close()
