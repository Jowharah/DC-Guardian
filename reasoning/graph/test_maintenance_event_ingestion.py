from pathlib import Path
import sys


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)


for directory in [
    PROJECT_ROOT / "reasoning" / "adapters",
    PROJECT_ROOT / "reasoning" / "topology",
    PROJECT_ROOT / "reasoning" / "graph",
]:

    if str(directory) not in sys.path:
        sys.path.insert(
            0,
            str(directory)
        )


from maintenance_event_adapter import (
    adapt_maintenance_assessment,
)

from topology_mapper import (
    map_maintenance_event_to_scenario,
)

from ingest_event import (
    create_driver,
    ingest_maintenance_event,
    NEO4J_DATABASE,
)


assessment = {
    "domain":
        "MAINTENANCE",

    "event_type":
        "STORAGE_FAILURE_RISK_ASSESSMENT",

    "model_name":
        "DC_Guardian_Temporal_RF_v2",

    "asset_type":
        "HARD_DRIVE",

    "serial_number":
        "DRV-MAINT-GRAPH-001",

    "observation_timestamp":
        "2026-03-20T00:00:00Z",

    "assessment":
        "AT_RISK",

    "failure_probability":
        0.714008,

    "operating_threshold":
        0.45,

    "failure_horizon_days":
        7,

    "evidence": {
        "smart_5_raw":
            20.0,

        "smart_198_raw":
            2.0,

        "smart_194_raw":
            35.0,

        "smart_5_delta_7":
            20.0,

        "smart_198_delta_7":
            2.0,

        "temperature_7obs_mean":
            33.8571428571,
    },
}


if __name__ == "__main__":

    print(
        "\n============================================"
    )
    print(
        "DC-GUARDIAN MAINTENANCE EVENT INGESTION"
    )
    print(
        "============================================"
    )


    # ========================================================
    # Evidence layer -> Common Event
    # ========================================================

    normalized = adapt_maintenance_assessment(
        assessment,

        dataset_name=
            "DC-Guardian Maintenance Integration Test",

        source_type=
            "CONTROLLED_TEST",

        event_id=
            "EVT-MAINT-INTEGRATION-001",
    )


    print(
        "\nPASS: Common maintenance event generated."
    )


    # ========================================================
    # Common Event -> synthetic topology
    # ========================================================

    mapped = map_maintenance_event_to_scenario(
        normalized,

        scenario_id=
            "SCENARIO-MAINT-001",

        scenario_timestamp=
            "2026-09-18T12:05:00Z",

        target_name=
            "ZONE_B_CRITICAL_STORAGE",
    )


    print(
        "PASS: Maintenance topology mapping applied."
    )


    # ========================================================
    # Neo4j
    # ========================================================

    driver = create_driver()


    try:

        print(
            "PASS: Connected to Neo4j."
        )


        result = ingest_maintenance_event(
            mapped,
            driver,
        )


        assert (
            result[
                "asset_id"
            ]
            == "DRV-MAINT-GRAPH-001"
        )


        assert (
            result[
                "server_id"
            ]
            == "SRV-B1-01"
        )


        print(
            "PASS: Maintenance event ingested."
        )


        # ====================================================
        # Repeat ingestion -> idempotency
        # ====================================================

        second = ingest_maintenance_event(
            mapped,
            driver,
        )


        assert (
            second[
                "event_id"
            ]
            == result[
                "event_id"
            ]
        )


        print(
            "PASS: Repeated event ingestion "
            "is idempotent."
        )


        with driver.session(
            database=NEO4J_DATABASE
        ) as session:


            # =================================================
            # Full maintenance -> physical path
            # =================================================

            context  = session.run(
                """
                MATCH
                    (e:Event {
                        event_id: $event_id
                    })
                    -[:TARGETS]->
                    (a:Asset)
                    -[:HOSTED_BY]->
                    (s:Server)
                    -[:LOCATED_IN]->
                    (r:Rack)
                    -[:LOCATED_IN]->
                    (z:Zone)
                    -[:PART_OF]->
                    (dc:DataCenter)

                RETURN
                    e.event_id
                        AS event_id,

                    e.state
                        AS state,

                    e.score
                        AS score,

                    e.failure_probability
                        AS failure_probability,

                    e.failure_horizon_days
                        AS failure_horizon_days,

                    a.asset_id
                        AS asset_id,

                    a.asset_type
                        AS asset_type,

                    s.server_id
                        AS server_id,

                    r.rack_id
                        AS rack_id,

                    z.zone_id
                        AS zone_id,

                    dc.data_center_id
                        AS data_center_id
                """,
                event_id=result[
                    "event_id"
                ],
            ).single()


            if context is None:

                raise AssertionError(
                    "Maintenance -> physical "
                    "graph path not found."
                )


            assert (
                context[
                    "asset_id"
                ]
                == "DRV-MAINT-GRAPH-001"
            )

            assert (
                context[
                    "asset_type"
                ]
                == "HARD_DRIVE"
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
                    "zone_id"
                ]
                == "ZONE-B"
            )

            assert (
                context[
                    "data_center_id"
                ]
                == "DC-01"
            )

            assert abs(
                context[
                    "failure_probability"
                ]
                - 0.714008
            ) < 1e-9


            print(
                "PASS: Event -> Drive -> Server -> "
                "Rack -> Zone -> DC path verified."
            )


            # =================================================
            # Idempotency counts
            # =================================================

            record = session.run(
                """
                MATCH (e:Event {
                    event_id: $event_id
                })

                OPTIONAL MATCH
                    (e)-[t:TARGETS]->(:Asset)

                RETURN
                    count(DISTINCT e)
                        AS event_count,

                    count(t)
                        AS target_count
                """,
                event_id=result[
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
                    "target_count"
                ]
                == 1
            )


            print(
                "PASS: Event and TARGETS "
                "relationship are idempotent."
            )


            # =================================================
            # Asset hosting relationship
            # =================================================

            record = session.run(
                """
                MATCH
                    (a:Asset {
                        asset_id: $asset_id
                    })
                    -[h:HOSTED_BY]->
                    (s:Server)

                RETURN
                    count(h)
                        AS hosted_by_count,

                    collect(
                        s.server_id
                    )
                        AS servers
                """,
                asset_id=
                    "DRV-MAINT-GRAPH-001",
            ).single()


            assert (
                record[
                    "hosted_by_count"
                ]
                == 1
            )

            assert (
                record[
                    "servers"
                ]
                == [
                    "SRV-B1-01"
                ]
            )


            print(
                "PASS: Drive HOSTED_BY "
                "server relationship verified."
            )


            # =================================================
            # Display
            # =================================================

            print(
                "\n============================================"
            )

            print(
                "MAINTENANCE -> PHYSICAL CONTEXT"
            )

            print(
                "============================================"
            )


            print(
                "Assessment:",
                context[
                    "state"
                ]
            )


            print(
                "Failure probability:",
                context[
                    "failure_probability"
                ]
            )


            print(
                "Failure horizon:",
                context[
                    "failure_horizon_days"
                ],
                "days"
            )


            print(
                "Drive:",
                context[
                    "asset_id"
                ]
            )


            print(
                "Server:",
                context[
                    "server_id"
                ]
            )


            print(
                "Rack:",
                context[
                    "rack_id"
                ]
            )


            print(
                "Zone:",
                context[
                    "zone_id"
                ]
            )


            print(
                "Data center:",
                context[
                    "data_center_id"
                ]
            )


        print(
            "\n============================================"
        )
        print(
            "DC-GUARDIAN MAINTENANCE "
            "EVENT INGESTION PASSED"
        )
        print(
            "============================================"
        )


    finally:

        driver.close()
