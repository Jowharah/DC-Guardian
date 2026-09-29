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

ADAPTER_DIR = (
    PROJECT_ROOT
    / "phase2"
    / "adapters"
)

TOPOLOGY_DIR = (
    PROJECT_ROOT
    / "phase2"
    / "topology"
)

GRAPH_DIR = (
    PROJECT_ROOT
    / "phase2"
    / "graph"
)


for directory in [
    ADAPTER_DIR,
    TOPOLOGY_DIR,
    GRAPH_DIR,
]:

    if str(directory) not in sys.path:

        sys.path.insert(
            0,
            str(directory)
        )


from ssh_event_adapter import (
    adapt_ssh_assessment
)

from topology_mapper import (
    map_ssh_event_to_scenario
)

from ingest_event import (
    create_driver,
    ingest_ssh_event,
    NEO4J_DATABASE,
)


# ============================================================
# Representative frozen SSH output
# ============================================================

ssh_assessment = {

    "event_type":
        "ssh_behavior_assessment",

    "source_ip":
        "203.0.113.20",

    "window_start":
        "2000-12-17T02:25:00Z",

    "window_end":
        "2000-12-17T02:30:00Z",

    "anomaly_detected":
        True,

    "detector_votes":
        2,

    "detector_combination":
        "RULE+AE",

    "confidence":
        "MEDIUM",

    "evidence_state":
        "HIGH_CONFIDENCE_ANOMALY",

    "explicit_security_signal":
        False,

    "security_signals":
        [],

    "security_signal_evidence":
        [],

    "rule": {
        "prediction":
            "ANOMALOUS",

        "anomalous":
            True,

        "suspicious":
            False,

        "score":
            1,

        "triggered_rules": [
            "ROOT_TARGETING"
        ],

        "evidence": [
            "100% of failed attempts "
            "targeted root"
        ],
    },

    "isolation_forest": {
        "prediction":
            "NORMAL",

        "anomalous":
            False,

        "anomaly_score":
            -0.138,
    },

    "autoencoder": {
        "prediction":
            "ANOMALOUS",

        "anomalous":
            True,

        "reconstruction_error":
            0.125,

        "threshold":
            0.0857589915394783,
    },

    "evidence": {
        "failed_login_count":
            6,

        "invalid_user_count":
            0,

        "unique_users":
            1,

        "failure_ratio":
            1.0,

        "root_attempt_ratio":
            1.0,

        "breakin_warning_count":
            0,

        "disconnect_count":
            0,

        "no_identification_count":
            0,

        "successful_login_count":
            0,

        "success_after_failures":
            0,
    },
}


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":

    print(
        "\n============================================"
    )
    print(
        "DC-GUARDIAN SSH EVENT INGESTION TEST"
    )
    print(
        "============================================"
    )


    # ========================================================
    # Step 1:
    # Phase 1 -> common event
    # ========================================================

    normalized_event = (
        adapt_ssh_assessment(
            ssh_assessment,

            dataset_name=
                "DC-Guardian Integration Test",

            source_type=
                "CONTROLLED_TEST",

            event_id=
                "EVT-SSH-INTEGRATION-001",
        )
    )


    print(
        "\nPASS: Common SSH event generated."
    )


    # ========================================================
    # Step 2:
    # Common event -> synthetic scenario
    # ========================================================

    mapped_event = (
        map_ssh_event_to_scenario(
            normalized_event,

            scenario_id=
                "SCENARIO-SSH-001",

            scenario_timestamp=
                "2026-09-18T12:00:00Z",

            target_name=
                "ZONE_A_SERVER",
        )
    )


    print(
        "PASS: Synthetic scenario "
        "mapping applied."
    )


    # ========================================================
    # Connect
    # ========================================================

    driver = create_driver()


    try:

        print(
            "PASS: Connected to Neo4j."
        )


        # ====================================================
        # Step 3:
        # First ingestion
        # ====================================================

        result = ingest_ssh_event(
            mapped_event,
            driver
        )


        print(
            "PASS: SSH event ingested."
        )


        assert (
            result[
                "server_id"
            ]
            == "SRV-A1-01"
        )

        assert (
            result[
                "source_ip"
            ]
            == "203.0.113.20"
        )


        # ====================================================
        # Step 4:
        # Repeat exact same ingestion
        #
        # MERGE should prevent duplicates.
        # ====================================================

        second_result = ingest_ssh_event(
            mapped_event,
            driver
        )


        assert (
            second_result[
                "event_id"
            ]
            == result[
                "event_id"
            ]
        )


        print(
            "PASS: Same event ingested "
            "twice without duplicate ID."
        )


        # ====================================================
        # Verify graph
        # ====================================================

        with driver.session(
            database=NEO4J_DATABASE
        ) as session:


            # ------------------------------------------------
            # Event count
            # ------------------------------------------------

            record = session.run(
                """
                MATCH (e:Event {
                    event_id: $event_id
                })

                RETURN count(e) AS count
                """,
                event_id=result[
                    "event_id"
                ],
            ).single()


            assert (
                record[
                    "count"
                ]
                == 1
            )


            print(
                "PASS: Event ingestion "
                "is idempotent."
            )


            # ------------------------------------------------
            # Source IP count
            # ------------------------------------------------

            record = session.run(
                """
                MATCH (ip:SourceIP {
                    address: $address
                })

                RETURN count(ip) AS count
                """,
                address=
                    "203.0.113.20",
            ).single()


            assert (
                record[
                    "count"
                ]
                == 1
            )


            print(
                "PASS: SourceIP node "
                "is idempotent."
            )


            # ------------------------------------------------
            # Full cyber -> physical path
            # ------------------------------------------------

            record = session.run(
                """
                MATCH
                    (e:Event {
                        event_id: $event_id
                    })
                    -[:TARGETS]->
                    (s:Server)
                    -[:LOCATED_IN]->
                    (r:Rack)
                    -[:LOCATED_IN]->
                    (z:Zone)
                    -[:PART_OF]->
                    (dc:DataCenter)

                MATCH
                    (e)-[:ORIGINATED_FROM]->
                    (ip:SourceIP)

                RETURN
                    e.event_id
                        AS event_id,

                    e.state
                        AS state,

                    e.scenario_id
                        AS scenario_id,

                    ip.address
                        AS source_ip,

                    s.server_id
                        AS server_id,

                    s.criticality
                        AS server_criticality,

                    r.rack_id
                        AS rack_id,

                    z.zone_id
                        AS zone_id,

                    z.criticality
                        AS zone_criticality,

                    dc.data_center_id
                        AS data_center_id
                """,
                event_id=result[
                    "event_id"
                ],
            ).single()


            if record is None:

                raise AssertionError(
                    "Cyber -> physical graph "
                    "path was not found."
                )


            assert (
                record[
                    "server_id"
                ]
                == "SRV-A1-01"
            )

            assert (
                record[
                    "rack_id"
                ]
                == "RACK-A1"
            )

            assert (
                record[
                    "zone_id"
                ]
                == "ZONE-A"
            )

            assert (
                record[
                    "data_center_id"
                ]
                == "DC-01"
            )


            print(
                "PASS: Event -> Server -> "
                "Rack -> Zone -> DC path verified."
            )


            # ------------------------------------------------
            # Relationship counts
            # ------------------------------------------------

            record = session.run(
                """
                MATCH
                    (e:Event {
                        event_id: $event_id
                    })
                    -[t:TARGETS]->
                    (:Server)

                WITH
                    e,
                    count(t)
                        AS target_count

                MATCH
                    (e)
                    -[o:ORIGINATED_FROM]->
                    (:SourceIP)

                RETURN
                    target_count,
                    count(o)
                        AS origin_count
                """,
                event_id=result[
                    "event_id"
                ],
            ).single()


            assert (
                record[
                    "target_count"
                ]
                == 1
            )

            assert (
                record[
                    "origin_count"
                ]
                == 1
            )


            print(
                "PASS: TARGETS relationship "
                "verified."
            )

            print(
                "PASS: ORIGINATED_FROM "
                "relationship verified."
            )


            # ------------------------------------------------
            # Provenance
            # ------------------------------------------------

            record = session.run(
                """
                MATCH (e:Event {
                    event_id: $event_id
                })

                RETURN
                    e.synthetic_mapping
                        AS synthetic_mapping,

                    e.mapping_type
                        AS mapping_type,

                    e.scenario_id
                        AS scenario_id,

                    e.original_event_id
                        AS original_event_id,

                    e.original_timestamp
                        AS original_timestamp
                """,
                event_id=result[
                    "event_id"
                ],
            ).single()


            assert (
                record[
                    "synthetic_mapping"
                ]
                is True
            )

            assert (
                record[
                    "mapping_type"
                ]
                == "SYNTHETIC_SCENARIO"
            )

            assert (
                record[
                    "scenario_id"
                ]
                == "SCENARIO-SSH-001"
            )


            print(
                "PASS: Event provenance "
                "preserved in graph."
            )


            # ------------------------------------------------
            # Display contextual result
            # ------------------------------------------------

            print(
                "\n============================================"
            )
            print(
                "CYBER -> PHYSICAL CONTEXT"
            )
            print(
                "============================================"
            )

            context = session.run(
                """
                MATCH
                    (e:Event {
                        event_id: $event_id
                    })
                    -[:TARGETS]->
                    (s:Server)
                    -[:LOCATED_IN]->
                    (r:Rack)
                    -[:LOCATED_IN]->
                    (z:Zone)
                    -[:PART_OF]->
                    (dc:DataCenter)

                RETURN
                    e.state
                        AS state,

                    s.server_id
                        AS server,

                    s.criticality
                        AS server_criticality,

                    r.rack_id
                        AS rack,

                    z.zone_id
                        AS zone,

                    z.criticality
                        AS zone_criticality,

                    dc.data_center_id
                        AS data_center
                """,
                event_id=result[
                    "event_id"
                ],
            ).single()


            print(
                "SSH assessment:",
                context[
                    "state"
                ]
            )

            print(
                "Target server:",
                context[
                    "server"
                ]
            )

            print(
                "Server criticality:",
                context[
                    "server_criticality"
                ]
            )

            print(
                "Rack:",
                context[
                    "rack"
                ]
            )

            print(
                "Zone:",
                context[
                    "zone"
                ]
            )

            print(
                "Zone criticality:",
                context[
                    "zone_criticality"
                ]
            )

            print(
                "Data center:",
                context[
                    "data_center"
                ]
            )


        print(
            "\n============================================"
        )
        print(
            "DC-GUARDIAN SSH EVENT "
            "INGESTION PASSED"
        )
        print(
            "============================================"
        )


    finally:

        driver.close()