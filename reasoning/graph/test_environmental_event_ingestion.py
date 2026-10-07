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

from evidence.environmental_monitoring.src.sensor_monitor import (
    assess_sensor_reading,
)

from evidence.environmental_monitoring.src.hardware_monitor import (
    assess_hardware_environment,
)

from environmental_event_adapter import (
    adapt_environmental_assessment,
)

from topology_mapper import (
    map_environmental_event_to_scenario,
)

from ingest_event import (
    create_driver,
    ingest_environmental_event,
    NEO4J_DATABASE,
)


# ============================================================
# Shared scenario
# ============================================================

SCENARIO_ID = (
    "SCENARIO-ENV-GRAPH-001"
)


# ============================================================
# Helper
# ============================================================

def prepare_event(
    assessment,
    *,
    event_id,
    timestamp,
    hard_drive_target_name=None,
):

    normalized = (
        adapt_environmental_assessment(
            assessment,

            dataset_name=
                "DC-Guardian Environmental "
                "Graph Integration Test",

            source_type=
                "CONTROLLED_TEST",

            event_id=
                event_id,
        )
    )


    mapped = (
        map_environmental_event_to_scenario(
            normalized,

            scenario_id=
                SCENARIO_ID,

            scenario_timestamp=
                timestamp,

            hard_drive_target_name=
                hard_drive_target_name,
        )
    )


    return mapped


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":

    print(
        "\n============================================"
    )
    print(
        "DC-GUARDIAN ENVIRONMENTAL EVENT INGESTION"
    )
    print(
        "============================================"
    )


    driver = create_driver()


    try:

        print(
            "PASS: Connected to Neo4j."
        )


        # ====================================================
        # Clean only previous environmental test artifacts
        # ====================================================

        with driver.session(
            database=NEO4J_DATABASE
        ) as session:

            session.run(
                """
                MATCH (e:Event {
                    scenario_id: $scenario_id
                })

                DETACH DELETE e
                """,

                scenario_id=
                    SCENARIO_ID,
            ).consume()


            session.run(
                """
                MATCH (a:Asset {
                    asset_id: $asset_id
                })

                DETACH DELETE a
                """,

                asset_id=
                    "DRV-ENV-GRAPH-001",
            ).consume()


        print(
            "PASS: Previous environmental "
            "test artifacts cleared."
        )


        # ====================================================
        # 1. Dedicated environmental sensor
        # ====================================================

        sensor_assessment = (
            assess_sensor_reading(
                sensor_id=
                    "SEN-B-01",

                observation_timestamp=
                    "2026-09-18T12:03:00Z",

                temperature_c=
                    42.5,

                humidity_pct=
                    48.0,
            )
        )


        sensor_event = prepare_event(
            sensor_assessment,

            event_id=
                "EVT-ENV-GRAPH-SENSOR-001",

            timestamp=
                "2026-09-18T12:03:00Z",
        )


        sensor_result = (
            ingest_environmental_event(
                sensor_event,
                driver,
            )
        )


        assert (
            sensor_result[
                "target_kind"
            ]
            == "SENSOR"
        )


        assert (
            sensor_result[
                "target_id"
            ]
            == "SEN-B-01"
        )


        print(
            "PASS: Dedicated sensor "
            "event ingested."
        )


        # ====================================================
        # 2. Server environmental telemetry
        # ====================================================

        server_assessment = (
            assess_hardware_environment(
                asset_id=
                    "SRV-B1-01",

                asset_type=
                    "SERVER",

                observation_timestamp=
                    "2026-09-18T12:04:00Z",

                temperature_c=
                    40.0,
            )
        )


        server_event = prepare_event(
            server_assessment,

            event_id=
                "EVT-ENV-GRAPH-SERVER-001",

            timestamp=
                "2026-09-18T12:04:00Z",
        )


        server_result = (
            ingest_environmental_event(
                server_event,
                driver,
            )
        )


        assert (
            server_result[
                "target_kind"
            ]
            == "SERVER"
        )


        assert (
            server_result[
                "target_id"
            ]
            == "SRV-B1-01"
        )


        print(
            "PASS: Server telemetry "
            "event ingested."
        )


        # ====================================================
        # 3. Cooling equipment telemetry
        # ====================================================

        cooling_assessment = (
            assess_hardware_environment(
                asset_id=
                    "CHILLER-C1",

                asset_type=
                    "COOLING_SYSTEM",

                observation_timestamp=
                    "2026-09-18T12:05:00Z",

                temperature_c=
                    38.0,
            )
        )


        cooling_event = prepare_event(
            cooling_assessment,

            event_id=
                "EVT-ENV-GRAPH-COOLING-001",

            timestamp=
                "2026-09-18T12:05:00Z",
        )


        cooling_result = (
            ingest_environmental_event(
                cooling_event,
                driver,
            )
        )


        assert (
            cooling_result[
                "target_kind"
            ]
            == "EQUIPMENT"
        )


        assert (
            cooling_result[
                "target_id"
            ]
            == "CHILLER-C1"
        )


        print(
            "PASS: Cooling telemetry "
            "event ingested."
        )


        # ====================================================
        # 4. Hard-drive environmental telemetry
        # ====================================================

        drive_assessment = (
            assess_hardware_environment(
                asset_id=
                    "DRV-ENV-GRAPH-001",

                asset_type=
                    "HARD_DRIVE",

                observation_timestamp=
                    "2026-09-18T12:06:00Z",

                temperature_c=
                    41.0,
            )
        )


        drive_event = prepare_event(
            drive_assessment,

            event_id=
                "EVT-ENV-GRAPH-DRIVE-001",

            timestamp=
                "2026-09-18T12:06:00Z",

            hard_drive_target_name=
                "ZONE_B_CRITICAL_STORAGE",
        )


        drive_result = (
            ingest_environmental_event(
                drive_event,
                driver,
            )
        )


        assert (
            drive_result[
                "target_kind"
            ]
            == "ASSET"
        )


        assert (
            drive_result[
                "target_id"
            ]
            == "DRV-ENV-GRAPH-001"
        )


        print(
            "PASS: Hard-drive environmental "
            "event ingested."
        )


        # ====================================================
        # 5. Repeat all four -> idempotency
        # ====================================================

        for event in [
            sensor_event,
            server_event,
            cooling_event,
            drive_event,
        ]:

            ingest_environmental_event(
                event,
                driver,
            )


        print(
            "PASS: Repeated environmental "
            "ingestion completed."
        )


        # ====================================================
        # Verify graph
        # ====================================================

        with driver.session(
            database=NEO4J_DATABASE
        ) as session:


            # =================================================
            # Sensor path
            # =================================================

            context = session.run(
                """
                MATCH
                    (e:Event {
                        event_id:
                            $event_id
                    })
                    -[:TARGETS]->
                    (sensor:Sensor)
                    -[:MONITORS]->
                    (zone:Zone)

                RETURN
                    e.state
                        AS state,

                    e.temperature_c
                        AS temperature_c,

                    sensor.sensor_id
                        AS sensor_id,

                    zone.zone_id
                        AS zone_id
                """,

                event_id=
                    sensor_result[
                        "event_id"
                    ],
            ).single()


            if context is None:

                raise AssertionError(
                    "Environmental sensor graph "
                    "path not found."
                )


            assert (
                context[
                    "sensor_id"
                ]
                == "SEN-B-01"
            )


            assert (
                context[
                    "zone_id"
                ]
                == "ZONE-B"
            )


            assert abs(
                context[
                    "temperature_c"
                ]
                - 42.5
            ) < 1e-9


            print(
                "PASS: Event -> Sensor -> "
                "MONITORS -> Zone path verified."
            )


            # =================================================
            # Server path
            # =================================================

            context = session.run(
                """
                MATCH
                    (e:Event {
                        event_id:
                            $event_id
                    })
                    -[:TARGETS]->
                    (server:Server)
                    -[:LOCATED_IN]->
                    (rack:Rack)
                    -[:LOCATED_IN]->
                    (zone:Zone)

                RETURN
                    server.server_id
                        AS server_id,

                    rack.rack_id
                        AS rack_id,

                    zone.zone_id
                        AS zone_id
                """,

                event_id=
                    server_result[
                        "event_id"
                    ],
            ).single()


            if context is None:

                raise AssertionError(
                    "Environmental server graph "
                    "path not found."
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


            print(
                "PASS: Event -> Server -> "
                "Rack -> Zone path verified."
            )


            # =================================================
            # Cooling equipment path
            # =================================================

            context = session.run(
                """
                MATCH
                    (e:Event {
                        event_id:
                            $event_id
                    })
                    -[:TARGETS]->
                    (equipment:Equipment)
                    -[:LOCATED_IN]->
                    (zone:Zone)

                RETURN
                    equipment.equipment_id
                        AS equipment_id,

                    zone.zone_id
                        AS zone_id
                """,

                event_id=
                    cooling_result[
                        "event_id"
                    ],
            ).single()


            if context is None:

                raise AssertionError(
                    "Environmental equipment graph "
                    "path not found."
                )


            assert (
                context[
                    "equipment_id"
                ]
                == "CHILLER-C1"
            )


            assert (
                context[
                    "zone_id"
                ]
                == "ZONE-C"
            )


            print(
                "PASS: Event -> Equipment -> "
                "Zone path verified."
            )


            # =================================================
            # Hard-drive path
            # =================================================

            drive_context = session.run(
                """
                MATCH
                    (e:Event {
                        event_id:
                            $event_id
                    })
                    -[:TARGETS]->
                    (asset:Asset)
                    -[:HOSTED_BY]->
                    (server:Server)
                    -[:LOCATED_IN]->
                    (rack:Rack)
                    -[:LOCATED_IN]->
                    (zone:Zone)

                RETURN
                    e.state
                        AS state,

                    e.temperature_c
                        AS temperature_c,

                    asset.asset_id
                        AS asset_id,

                    server.server_id
                        AS server_id,

                    rack.rack_id
                        AS rack_id,

                    zone.zone_id
                        AS zone_id
                """,

                event_id=
                    drive_result[
                        "event_id"
                    ],
            ).single()


            if drive_context is None:

                raise AssertionError(
                    "Environmental drive graph "
                    "path not found."
                )


            assert (
                drive_context[
                    "asset_id"
                ]
                == "DRV-ENV-GRAPH-001"
            )


            assert (
                drive_context[
                    "server_id"
                ]
                == "SRV-B1-01"
            )


            assert (
                drive_context[
                    "rack_id"
                ]
                == "RACK-B1"
            )


            assert (
                drive_context[
                    "zone_id"
                ]
                == "ZONE-B"
            )


            print(
                "PASS: Event -> Drive -> Server -> "
                "Rack -> Zone path verified."
            )


            # =================================================
            # Idempotency
            # =================================================

            record = session.run(
                """
                MATCH (e:Event {
                    scenario_id:
                        $scenario_id
                })

                RETURN
                    count(e)
                        AS event_count
                """,

                scenario_id=
                    SCENARIO_ID,
            ).single()


            assert (
                record[
                    "event_count"
                ]
                == 4
            )


            print(
                "PASS: Environmental events "
                "are idempotent."
            )


            # =================================================
            # Display
            # =================================================

            print(
                "\n============================================"
            )
            print(
                "ENVIRONMENTAL -> PHYSICAL CONTEXT"
            )
            print(
                "============================================"
            )


            print(
                "Dedicated sensor:"
            )

            print(
                "  SEN-B-01 -> ZONE-B"
            )


            print(
                "Server telemetry:"
            )

            print(
                "  SRV-B1-01 -> "
                "RACK-B1 -> ZONE-B"
            )


            print(
                "Cooling telemetry:"
            )

            print(
                "  CHILLER-C1 -> ZONE-C"
            )


            print(
                "Drive telemetry:"
            )

            print(
                "  DRV-ENV-GRAPH-001 -> "
                "SRV-B1-01 -> RACK-B1 -> ZONE-B"
            )


        print(
            "\n============================================"
        )
        print(
            "ENVIRONMENTAL EVENT INGESTION "
            "CONTRACT SUMMARY"
        )
        print(
            "============================================"
        )


        print(
            "PASS: Dedicated sensor ingestion."
        )

        print(
            "PASS: Server telemetry ingestion."
        )

        print(
            "PASS: Cooling telemetry ingestion."
        )

        print(
            "PASS: Hard-drive telemetry ingestion."
        )

        print(
            "PASS: Environmental measurements preserved."
        )

        print(
            "PASS: Topology relationships reused."
        )

        print(
            "PASS: Ingestion idempotent."
        )


        print(
            "\n============================================"
        )
        print(
            "DC-GUARDIAN ENVIRONMENTAL "
            "EVENT INGESTION PASSED"
        )
        print(
            "============================================"
        )


    finally:

        driver.close()

