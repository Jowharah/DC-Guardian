"""
DC-Guardian Phase 2
Face + Cybersecurity Correlation Persistence Contract

Prerequisite:
    test_face_cyber_correlation.py has already created the
    controlled Face + Cyber scenario events.

Verifies:
    - correlation rediscovery
    - deterministic persistence
    - idempotent Correlation node
    - two contributing Event relationships
    - ZONE-B infrastructure concern
    - physical-security authorization context preserved
    - Face -> Camera -> Zone path remains explainable
    - Cyber -> Server -> Rack -> Zone path remains explainable
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
# ============================================================

SCENARIO_ID = (
    "SCENARIO-CORR-FACE-CYBER-001"
)


print(
    "\n============================================"
)
print(
    "DC-GUARDIAN FACE + CYBER CORRELATION STORE"
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
            "Expected exactly one Face + Cyber "
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
        "CYBERSECURITY",
        "PHYSICAL_SECURITY",
    }


    print(
        "PASS: Face + Cyber correlation rediscovered."
    )

    print(
        "PASS: Common scope = ZONE-B."
    )


    # ========================================================
    # Verify physical-security semantics before persistence
    # ========================================================

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


    cyber_event = next(
        event
        for event
        in correlation[
            "events"
        ]
        if (
            event[
                "domain"
            ]
            == "CYBERSECURITY"
        )
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


    assert (
        cyber_event[
            "state"
        ]
        == "HIGH_CONFIDENCE_ANOMALY"
    )


    print(
        "PASS: Unauthorized physical-security "
        "evidence preserved."
    )

    print(
        "PASS: Cybersecurity anomaly preserved."
    )


    # ========================================================
    # Remove previous persisted correlation only
    #
    # Contributing events remain untouched.
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
        "PASS: Previous persisted Face + Cyber "
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
        "CYBERSECURITY",
        "PHYSICAL_SECURITY",
    }


    print(
        "PASS: Face + Cyber correlation persisted."
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
            "CYBERSECURITY",
            "PHYSICAL_SECURITY",
        }


        print(
            "PASS: Face + Cyber Correlation node "
            "is idempotent."
        )


        # ----------------------------------------------------
        # Two contributing Events
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
            "CYBERSECURITY",
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
        # Full explainable Face + Cyber graph
        # ----------------------------------------------------

        context = session.run(
            """
            MATCH
                (physical:Event {
                    domain:
                        "PHYSICAL_SECURITY"
                })
                -[:CONTRIBUTES_TO]->
                (correlation:Correlation {
                    correlation_id:
                        $correlation_id
                })
                <-[:CONTRIBUTES_TO]-
                (cyber:Event {
                    domain:
                        "CYBERSECURITY"
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
            // Physical-security evidence path
            // -----------------------------------------------

            MATCH
                (physical)
                -[:OBSERVED_BY]->
                (camera:Camera {
                    camera_id:
                        "CAM-B-01"
                })

            MATCH
                (camera)
                -[:MONITORS]->
                (physical_zone:Zone {
                    zone_id:
                        "ZONE-B"
                })


            // P003 is an existing topology Person.
            MATCH
                (physical)
                -[:IDENTIFIES]->
                (person:Person {
                    person_id:
                        "P003"
                })


            // -----------------------------------------------
            // Cybersecurity evidence path
            // -----------------------------------------------

            MATCH
                (cyber)
                -[:TARGETS]->
                (server:Server {
                    server_id:
                        "SRV-B1-01"
                })

            MATCH
                (server)
                -[:LOCATED_IN]->
                (rack:Rack {
                    rack_id:
                        "RACK-B1"
                })
                -[:LOCATED_IN]->
                (cyber_zone:Zone {
                    zone_id:
                        "ZONE-B"
                })


            RETURN
                correlation.correlation_type
                    AS correlation_type,

                correlation.scope
                    AS scope,

                correlation.shared_entity_id
                    AS shared_entity_id,

                physical.state
                    AS physical_state,

                physical.authorization_status
                    AS authorization_status,

                person.person_id
                    AS person_id,

                camera.camera_id
                    AS camera_id,

                physical_zone.zone_id
                    AS physical_zone_id,

                cyber.state
                    AS cyber_state,

                server.server_id
                    AS server_id,

                rack.rack_id
                    AS rack_id,

                cyber_zone.zone_id
                    AS cyber_zone_id,

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
                "Explainable Face + Cyber "
                "correlation path not found."
            )


        # ----------------------------------------------------
        # Physical semantics
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
                "camera_id"
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
        # Cyber semantics
        # ----------------------------------------------------

        assert (
            context[
                "cyber_state"
            ]
            == "HIGH_CONFIDENCE_ANOMALY"
        )


        assert (
            context[
                "server_id"
            ]
            == "SRV-B1-01"
        )


        assert (
            context[
                "rack_id"
            ]
            == "RACK-B1"
        )


        assert (
            context[
                "cyber_zone_id"
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
            "PASS: Explainable Face + Cyber "
            "graph path verified."
        )


        # ====================================================
        # Display
        # ====================================================

        print(
            "\n============================================"
        )
        print(
            "PERSISTED FACE + CYBER CONTEXT"
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
            "\nPhysical Security:"
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
                "camera_id"
            ],
        )

        print(
            "  Zone:",
            context[
                "physical_zone_id"
            ],
        )


        print(
            "\nCybersecurity:"
        )

        print(
            "  State:",
            context[
                "cyber_state"
            ],
        )

        print(
            "  Server:",
            context[
                "server_id"
            ],
        )

        print(
            "  Rack:",
            context[
                "rack_id"
            ],
        )

        print(
            "  Zone:",
            context[
                "cyber_zone_id"
            ],
        )


    # ========================================================
    # Summary
    # ========================================================

    print(
        "\n============================================"
    )
    print(
        "FACE + CYBER STORE CONTRACT SUMMARY"
    )
    print(
        "============================================"
    )

    print(
        "PASS: Face + Cyber correlation persisted."
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
        "PASS: PHYSICAL_SECURITY preserved."
    )

    print(
        "PASS: CYBERSECURITY preserved."
    )

    print(
        "PASS: UNAUTHORIZED context preserved."
    )

    print(
        "PASS: ZONE-level concern preserved."
    )

    print(
        "PASS: Camera observation path preserved."
    )

    print(
        "PASS: Server topology path preserved."
    )

    print(
        "PASS: Explainable graph path available."
    )


    print(
        "\n============================================"
    )
    print(
        "DC-GUARDIAN FACE + CYBER "
        "CORRELATION STORE PASSED"
    )
    print(
        "============================================"
    )


finally:

    driver.close()
