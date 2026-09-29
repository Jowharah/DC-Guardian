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
    PROJECT_ROOT / "phase2" / "graph",
    PROJECT_ROOT / "phase2" / "correlation",
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
    find_multi_domain_correlations,
)

from correlation_store import (
    persist_correlation,
)


# ============================================================
# Scenario
#
# This test expects test_three_domain_correlation.py to have
# created the three controlled events first.
# ============================================================

SCENARIO_ID = (
    "SCENARIO-CORR-3D-001"
)


print(
    "\n============================================"
)
print(
    "DC-GUARDIAN THREE-DOMAIN CORRELATION STORE"
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
    # Rediscover the three-domain correlation
    # ========================================================

    correlations = (
        find_multi_domain_correlations(
            driver,

            scenario_id=
                SCENARIO_ID,

            window_minutes=
                15,

            minimum_domains=
                3,
        )
    )


    if len(
        correlations
    ) != 1:

        raise AssertionError(
            "Expected exactly one "
            "three-domain correlation; "
            f"found {len(correlations)}."
        )


    correlation = (
        correlations[0]
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


    assert (
        correlation[
            "domain_count"
        ]
        == 3
    )


    assert (
        correlation[
            "event_count"
        ]
        == 3
    )


    assert set(
        correlation[
            "domains"
        ]
    ) == {
        "CYBERSECURITY",
        "ENVIRONMENTAL",
        "MAINTENANCE",
    }


    print(
        "PASS: Three-domain correlation rediscovered."
    )

    print(
        "PASS: Common scope = ZONE-B."
    )


    # ========================================================
    # Confirm independent environmental evidence
    # ========================================================

    environmental_events = [
        event
        for event
        in correlation[
            "events"
        ]
        if event[
            "domain"
        ] == "ENVIRONMENTAL"
    ]


    assert (
        len(
            environmental_events
        )
        == 1
    )


    assert (
        environmental_events[
            0
        ][
            "evidence_independence"
        ]
        == "INDEPENDENT"
    )


    print(
        "PASS: Independent environmental "
        "evidence preserved."
    )


    # ========================================================
    # Remove previous persisted correlation for this scenario
    #
    # Contributing Events are deliberately preserved.
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
        "PASS: Previous persisted "
        "three-domain correlation cleared."
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
        == 3
    )


    assert set(
        result[
            "domains"
        ]
    ) == {
        "CYBERSECURITY",
        "ENVIRONMENTAL",
        "MAINTENANCE",
    }


    print(
        "PASS: Three-domain correlation persisted."
    )


    # ========================================================
    # Repeated persistence
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
        "PASS: Repeated persistence "
        "uses deterministic correlation ID."
    )


    # ========================================================
    # Verify graph
    # ========================================================

    with driver.session(
        database=NEO4J_DATABASE
    ) as session:


        # ====================================================
        # Correlation node
        # ====================================================

        record = session.run(
            """
            MATCH (c:Correlation {
                correlation_id:
                    $correlation_id
            })

            RETURN
                count(c)
                    AS correlation_count,

                c.correlation_type
                    AS correlation_type,

                c.scenario_id
                    AS scenario_id,

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
                "correlation_count"
            ]
            == 1
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
            == 3
        )


        assert set(
            record[
                "domains"
            ]
        ) == {
            "CYBERSECURITY",
            "ENVIRONMENTAL",
            "MAINTENANCE",
        }


        print(
            "PASS: Three-domain Correlation "
            "node is idempotent."
        )


        # ====================================================
        # Exactly three contributing events
        # ====================================================

        record = session.run(
            """
            MATCH
                (e:Event)
                -[r:CONTRIBUTES_TO]->
                (c:Correlation {
                    correlation_id:
                        $correlation_id
                })

            RETURN
                count(r)
                    AS relationship_count,

                count(
                    DISTINCT e
                )
                    AS event_count,

                collect(
                    DISTINCT e.domain
                )
                    AS domains,

                collect(
                    DISTINCT e.event_id
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
            == 3
        )


        assert (
            record[
                "event_count"
            ]
            == 3
        )


        assert set(
            record[
                "domains"
            ]
        ) == {
            "CYBERSECURITY",
            "ENVIRONMENTAL",
            "MAINTENANCE",
        }


        print(
            "PASS: Three contributing "
            "events linked."
        )


        # ====================================================
        # Correlation must concern ZONE-B
        # ====================================================

        record = session.run(
            """
            MATCH
                (c:Correlation {
                    correlation_id:
                        $correlation_id
                })
                -[r:CONCERNS]->
                (z:Zone)

            RETURN
                count(r)
                    AS relationship_count,

                collect(
                    z.zone_id
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


        # ====================================================
        # Explainable three-domain graph path
        # ====================================================

        context = session.run(
            """
            MATCH
                (cyber:Event {
                    domain:
                        "CYBERSECURITY"
                })
                -[:CONTRIBUTES_TO]->
                (c:Correlation {
                    correlation_id:
                        $correlation_id
                })

            MATCH
                (environmental:Event {
                    domain:
                        "ENVIRONMENTAL"
                })
                -[:CONTRIBUTES_TO]->
                (c)

            MATCH
                (maintenance:Event {
                    domain:
                        "MAINTENANCE"
                })
                -[:CONTRIBUTES_TO]->
                (c)

            MATCH
                (c)-[:CONCERNS]->
                (zone:Zone)

            RETURN
                c.correlation_type
                    AS correlation_type,

                c.scope
                    AS scope,

                cyber.state
                    AS cyber_state,

                environmental.state
                    AS environmental_state,

                environmental.environmental_source_class
                    AS environmental_source_class,

                environmental.temperature_c
                    AS temperature_c,

                maintenance.state
                    AS maintenance_state,

                maintenance.failure_probability
                    AS failure_probability,

                zone.zone_id
                    AS zone_id
            """,

            correlation_id=
                result[
                    "correlation_id"
                ],
        ).single()


        if context is None:

            raise AssertionError(
                "Explainable three-domain "
                "correlation path not found."
            )


        assert (
            context[
                "cyber_state"
            ]
            == "HIGH_CONFIDENCE_ANOMALY"
        )


        assert (
            context[
                "environmental_state"
            ]
            == "HIGH_TEMPERATURE"
        )


        assert (
            context[
                "environmental_source_class"
            ]
            == "ENVIRONMENTAL_SENSOR"
        )


        assert abs(
            context[
                "temperature_c"
            ]
            - 42.5
        ) < 1e-9


        assert (
            context[
                "maintenance_state"
            ]
            == "AT_RISK"
        )


        assert abs(
            context[
                "failure_probability"
            ]
            - 0.714008
        ) < 1e-9


        assert (
            context[
                "zone_id"
            ]
            == "ZONE-B"
        )


        print(
            "PASS: Explainable three-domain "
            "graph path verified."
        )


        # ====================================================
        # Stronger cyber-maintenance server context
        #
        # The persisted correlation concerns ZONE-B because
        # that is the strongest scope shared by all 3 domains.
        #
        # But the original events must still expose the
        # stronger server relationship.
        # ====================================================

        pairwise = (
            find_cross_domain_correlations(
                driver,

                scenario_id=
                    SCENARIO_ID,

                window_minutes=
                    15,
            )
        )


        cyber_maintenance = None


        for item in pairwise:

            domains = {
                event[
                    "domain"
                ]
                for event
                in item[
                    "events"
                ]
            }


            if domains == {
                "CYBERSECURITY",
                "MAINTENANCE",
            }:

                cyber_maintenance = item
                break


        if cyber_maintenance is None:

            raise AssertionError(
                "Supporting cybersecurity-maintenance "
                "relationship not found."
            )


        assert (
            cyber_maintenance[
                "scope"
            ]
            == "SERVER"
        )


        assert (
            cyber_maintenance[
                "shared_entity_id"
            ]
            == "SRV-B1-01"
        )


        print(
            "PASS: Stronger cyber-maintenance "
            "SERVER context remains discoverable."
        )


        # ====================================================
        # Display
        # ====================================================

        print(
            "\n============================================"
        )
        print(
            "PERSISTED THREE-DOMAIN CONTEXT"
        )
        print(
            "============================================"
        )


        print(
            "Correlation ID:",
            result[
                "correlation_id"
            ]
        )


        print(
            "Type:",
            context[
                "correlation_type"
            ]
        )


        print(
            "Scope:",
            context[
                "scope"
            ]
        )


        print(
            "Zone:",
            context[
                "zone_id"
            ]
        )


        print(
            "\nCybersecurity:"
        )

        print(
            "  State:",
            context[
                "cyber_state"
            ]
        )


        print(
            "\nEnvironmental:"
        )

        print(
            "  State:",
            context[
                "environmental_state"
            ]
        )

        print(
            "  Source:",
            context[
                "environmental_source_class"
            ]
        )

        print(
            "  Temperature:",
            context[
                "temperature_c"
            ],
            "C"
        )


        print(
            "\nMaintenance:"
        )

        print(
            "  State:",
            context[
                "maintenance_state"
            ]
        )

        print(
            "  Failure probability:",
            context[
                "failure_probability"
            ]
        )


        print(
            "\nSupporting topology:"
        )

        print(
            "  Cyber + Maintenance -> "
            "SRV-B1-01"
        )

        print(
            "  All three domains -> ZONE-B"
        )


    # ========================================================
    # Final
    # ========================================================

    print(
        "\n============================================"
    )
    print(
        "THREE-DOMAIN STORE CONTRACT SUMMARY"
    )
    print(
        "============================================"
    )


    print(
        "PASS: Three-domain correlation persisted."
    )

    print(
        "PASS: Deterministic ID preserved."
    )

    print(
        "PASS: Three event relationships preserved."
    )

    print(
        "PASS: Three domains preserved."
    )

    print(
        "PASS: ZONE-level concern preserved."
    )

    print(
        "PASS: Independent sensor evidence preserved."
    )

    print(
        "PASS: Stronger pairwise server context preserved."
    )

    print(
        "PASS: Explainable graph path available."
    )


    print(
        "\n============================================"
    )
    print(
        "DC-GUARDIAN THREE-DOMAIN "
        "CORRELATION STORE PASSED"
    )
    print(
        "============================================"
    )


finally:

    driver.close()