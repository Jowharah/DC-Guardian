from pathlib import Path
import sys


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)


for directory in [
    PROJECT_ROOT / "phase2" / "graph",
    PROJECT_ROOT / "phase2" / "correlation",
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


SCENARIO_ID = (
    "SCENARIO-CORR-001"
)


print(
    "\n============================================"
)
print(
    "DC-GUARDIAN CORRELATION STORE TEST"
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
    # Discover correlation from existing controlled scenario
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
            "Expected exactly one correlation "
            f"for {SCENARIO_ID}; "
            f"found {len(correlations)}."
        )


    correlation = (
        correlations[0]
    )


    print(
        "PASS: Correlation rediscovered."
    )


    # ========================================================
    # Remove previous persisted correlation only
    #
    # Events remain untouched.
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
        "PASS: Previous test correlation cleared."
    )


    # ========================================================
    # Persist
    # ========================================================

    result = persist_correlation(
        correlation,
        driver,
    )


    print(
        "PASS: Correlation persisted."
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
        == "SERVER"
    )


    assert (
        result[
            "shared_entity_id"
        ]
        == "SRV-B1-01"
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
        "MAINTENANCE",
    }


    # ========================================================
    # Persist same correlation again
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
        "uses same correlation ID."
    )


    # ========================================================
    # Verify graph
    # ========================================================

    with driver.session(
        database=NEO4J_DATABASE
    ) as session:


        # ----------------------------------------------------
        # Correlation node
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
                "scope"
            ]
            == "SERVER"
        )


        assert (
            record[
                "shared_entity_id"
            ]
            == "SRV-B1-01"
        )


        print(
            "PASS: Correlation node "
            "is idempotent."
        )


        # ----------------------------------------------------
        # Contributing events
        # ----------------------------------------------------

        record = session.run(
            """
            MATCH
                (e:Event)
                -[r:CONTRIBUTES_TO]->
                (c:Correlation {
                    correlation_id: $correlation_id
                })

            RETURN
                count(r)
                    AS relationship_count,

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
            == 2
        )


        assert set(
            record[
                "domains"
            ]
        ) == {
            "CYBERSECURITY",
            "MAINTENANCE",
        }


        print(
            "PASS: Two contributing "
            "events linked."
        )


        # ----------------------------------------------------
        # Infrastructure concern
        # ----------------------------------------------------

        record = session.run(
            """
            MATCH
                (c:Correlation {
                    correlation_id: $correlation_id
                })
                -[r:CONCERNS]->
                (s:Server)

            RETURN
                count(r)
                    AS relationship_count,

                collect(
                    s.server_id
                )
                    AS server_ids
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
                "server_ids"
            ]
            == [
                "SRV-B1-01"
            ]
        )


        print(
            "PASS: Correlation CONCERNS "
            "shared server."
        )


        # ----------------------------------------------------
        # Full explainable path
        # ----------------------------------------------------

        context = session.run(
            """
            MATCH
                (cyber:Event {
                    domain: "CYBERSECURITY"
                })
                -[:CONTRIBUTES_TO]->
                (c:Correlation {
                    correlation_id: $correlation_id
                })
                <-[:CONTRIBUTES_TO]-
                (maintenance:Event {
                    domain: "MAINTENANCE"
                })

            MATCH
                (c)-[:CONCERNS]->
                (server:Server)

            RETURN
                c.correlation_type
                    AS correlation_type,

                c.scope
                    AS scope,

                cyber.state
                    AS cyber_state,

                maintenance.state
                    AS maintenance_state,

                server.server_id
                    AS server_id
            """,

            correlation_id=
                result[
                    "correlation_id"
                ],
        ).single()


        if context is None:

            raise AssertionError(
                "Explainable correlation "
                "graph path not found."
            )


        assert (
            context[
                "cyber_state"
            ]
            == "HIGH_CONFIDENCE_ANOMALY"
        )


        assert (
            context[
                "maintenance_state"
            ]
            == "AT_RISK"
        )


        assert (
            context[
                "server_id"
            ]
            == "SRV-B1-01"
        )


        print(
            "\n============================================"
        )
        print(
            "PERSISTED CORRELATION CONTEXT"
        )
        print(
            "============================================"
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
            "Cyber state:",
            context[
                "cyber_state"
            ]
        )


        print(
            "Maintenance state:",
            context[
                "maintenance_state"
            ]
        )


        print(
            "Shared server:",
            context[
                "server_id"
            ]
        )


    print(
        "\n============================================"
    )
    print(
        "CORRELATION STORE CONTRACT SUMMARY"
    )
    print(
        "============================================"
    )

    print(
        "PASS: Deterministic correlation ID."
    )

    print(
        "PASS: Correlation persistence idempotent."
    )

    print(
        "PASS: Event evidence preserved."
    )

    print(
        "PASS: Infrastructure context preserved."
    )

    print(
        "PASS: Explainable graph path available."
    )


    print(
        "\n============================================"
    )
    print(
        "DC-GUARDIAN CORRELATION STORE PASSED"
    )
    print(
        "============================================"
    )


finally:

    driver.close()