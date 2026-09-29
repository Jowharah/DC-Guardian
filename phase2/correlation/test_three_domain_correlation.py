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
    PROJECT_ROOT / "phase2" / "adapters",
    PROJECT_ROOT / "phase2" / "topology",
    PROJECT_ROOT / "phase2" / "graph",
    PROJECT_ROOT / "phase2" / "correlation",
]:

    if str(directory) not in sys.path:

        sys.path.insert(
            0,
            str(directory)
        )


# ============================================================
# Phase 1
# ============================================================

from phase1.environmental_monitoring.src.sensor_monitor import (
    assess_sensor_reading,
)


# ============================================================
# Phase 2 adapters
# ============================================================

from ssh_event_adapter import (
    adapt_ssh_assessment,
)

from maintenance_event_adapter import (
    adapt_maintenance_assessment,
)

from environmental_event_adapter import (
    adapt_environmental_assessment,
)


# ============================================================
# Topology
# ============================================================

from topology_mapper import (
    map_ssh_event_to_scenario,
    map_maintenance_event_to_scenario,
    map_environmental_event_to_scenario,
)


# ============================================================
# Graph
# ============================================================

from ingest_event import (
    create_driver,
    ingest_ssh_event,
    ingest_maintenance_event,
    ingest_environmental_event,
    NEO4J_DATABASE,
)


# ============================================================
# Correlation
# ============================================================

from correlation_engine import (
    find_cross_domain_correlations,
    find_multi_domain_correlations,
)


# ============================================================
# Scenario
# ============================================================

SCENARIO_ID = (
    "SCENARIO-CORR-3D-001"
)


# ============================================================
# Controlled SSH assessment
# ============================================================

ssh_assessment = {

    "event_type":
        "ssh_behavior_assessment",

    "source_ip":
        "203.0.113.77",

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
            "Three-domain controlled test"
        ],
    },

    "isolation_forest": {
        "prediction":
            "NORMAL",

        "anomalous":
            False,

        "anomaly_score":
            -0.10,
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
# Controlled maintenance assessment
# ============================================================

maintenance_assessment = {

    "domain":
        "MAINTENANCE",

    "event_type":
        "STORAGE_FAILURE_RISK_ASSESSMENT",

    "model_name":
        "DC_Guardian_Temporal_RF_v2",

    "asset_type":
        "HARD_DRIVE",

    "serial_number":
        "DRV-CORR-3D-001",

    "observation_timestamp":
        "2026-09-18T12:05:00Z",

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


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":

    print(
        "\n============================================"
    )
    print(
        "DC-GUARDIAN THREE-DOMAIN CORRELATION TEST"
    )
    print(
        "============================================"
    )


    # ========================================================
    # Cybersecurity event
    #
    # 12:00 -> SRV-B1-01
    # ========================================================

    cyber_event = adapt_ssh_assessment(
        ssh_assessment,

        dataset_name=
            "DC-Guardian Three-Domain Test",

        source_type=
            "CONTROLLED_TEST",

        event_id=
            "EVT-CORR-3D-SSH-001",
    )


    cyber_event = map_ssh_event_to_scenario(
        cyber_event,

        scenario_id=
            SCENARIO_ID,

        scenario_timestamp=
            "2026-09-18T12:00:00Z",

        target_name=
            "ZONE_B_CRITICAL_SERVER",
    )


    print(
        "PASS: Cybersecurity event prepared."
    )


    # ========================================================
    # Environmental event
    #
    # 12:03 -> SEN-B-01 -> ZONE-B
    # ========================================================

    environmental_assessment = (
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


    environmental_event = (
        adapt_environmental_assessment(
            environmental_assessment,

            dataset_name=
                "DC-Guardian Three-Domain Test",

            source_type=
                "CONTROLLED_TEST",

            event_id=
                "EVT-CORR-3D-ENV-001",
        )
    )


    environmental_event = (
        map_environmental_event_to_scenario(
            environmental_event,

            scenario_id=
                SCENARIO_ID,

            scenario_timestamp=
                "2026-09-18T12:03:00Z",
        )
    )


    print(
        "PASS: Environmental sensor "
        "event prepared."
    )


    # ========================================================
    # Maintenance event
    #
    # 12:05 -> drive -> SRV-B1-01
    # ========================================================

    maintenance_event = (
        adapt_maintenance_assessment(
            maintenance_assessment,

            dataset_name=
                "DC-Guardian Three-Domain Test",

            source_type=
                "CONTROLLED_TEST",

            event_id=
                "EVT-CORR-3D-MAINT-001",
        )
    )


    maintenance_event = (
        map_maintenance_event_to_scenario(
            maintenance_event,

            scenario_id=
                SCENARIO_ID,

            scenario_timestamp=
                "2026-09-18T12:05:00Z",

            target_name=
                "ZONE_B_CRITICAL_STORAGE",
        )
    )


    print(
        "PASS: Maintenance event prepared."
    )


    # ========================================================
    # Neo4j
    # ========================================================

    driver = create_driver()


    try:

        print(
            "PASS: Connected to Neo4j."
        )


        # ====================================================
        # Clean previous test artifacts only
        # ====================================================

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
                    asset_id:
                        "DRV-CORR-3D-001"
                })

                DETACH DELETE a
                """
            ).consume()


            session.run(
                """
                MATCH (ip:SourceIP {
                    address:
                        "203.0.113.77"
                })

                DETACH DELETE ip
                """
            ).consume()


        print(
            "PASS: Previous three-domain "
            "test artifacts cleared."
        )


        # ====================================================
        # Ingest all three domains
        # ====================================================

        cyber_result = ingest_ssh_event(
            cyber_event,
            driver,
        )


        environmental_result = (
            ingest_environmental_event(
                environmental_event,
                driver,
            )
        )


        maintenance_result = (
            ingest_maintenance_event(
                maintenance_event,
                driver,
            )
        )


        assert (
            cyber_result[
                "server_id"
            ]
            == "SRV-B1-01"
        )


        assert (
            environmental_result[
                "target_id"
            ]
            == "SEN-B-01"
        )


        assert (
            maintenance_result[
                "server_id"
            ]
            == "SRV-B1-01"
        )


        print(
            "PASS: Cybersecurity event ingested."
        )

        print(
            "PASS: Environmental event ingested."
        )

        print(
            "PASS: Maintenance event ingested."
        )


        # ====================================================
        # Resolve contexts
        # ====================================================

        from correlation_engine import (
            resolve_event_contexts,
        )


        contexts = resolve_event_contexts(
            driver,

            scenario_id=
                SCENARIO_ID,
        )


        assert (
            len(
                contexts
            )
            == 3
        )


        context_by_domain = {
            item[
                "domain"
            ]:
                item

            for item in contexts
        }


        cyber_context = (
            context_by_domain[
                "CYBERSECURITY"
            ]
        )


        env_context = (
            context_by_domain[
                "ENVIRONMENTAL"
            ]
        )


        maintenance_context = (
            context_by_domain[
                "MAINTENANCE"
            ]
        )


        assert (
            cyber_context[
                "server_id"
            ]
            == "SRV-B1-01"
        )


        assert (
            cyber_context[
                "rack_id"
            ]
            == "RACK-B1"
        )


        assert (
            cyber_context[
                "zone_id"
            ]
            == "ZONE-B"
        )


        assert (
            maintenance_context[
                "server_id"
            ]
            == "SRV-B1-01"
        )


        assert (
            maintenance_context[
                "zone_id"
            ]
            == "ZONE-B"
        )


        # Dedicated sensor must NOT inherit server/rack.

        assert (
            env_context[
                "server_id"
            ]
            is None
        )


        assert (
            env_context[
                "rack_id"
            ]
            is None
        )


        assert (
            env_context[
                "zone_id"
            ]
            == "ZONE-B"
        )


        assert (
            env_context[
                "topology_origin"
            ]
            == "SENSOR"
        )


        assert (
            env_context[
                "evidence_independence"
            ]
            == "INDEPENDENT"
        )


        print(
            "\nPASS: All three event contexts resolved."
        )

        print(
            "PASS: Sensor remains truthfully "
            "ZONE scoped."
        )

        print(
            "PASS: External sensor marked "
            "INDEPENDENT evidence."
        )


        # ====================================================
        # Multi-domain correlation
        # ====================================================

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
            "\nPASS: Three-domain correlation detected."
        )

        print(
            "PASS: Strongest common scope = ZONE."
        )

        print(
            "PASS: Shared infrastructure = ZONE-B."
        )

        print(
            "PASS: Domain count = 3."
        )


        # ====================================================
        # Pairwise relationships remain available
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
                "Cybersecurity-maintenance "
                "pairwise correlation missing."
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
            "PASS: Cyber + maintenance retain "
            "stronger SERVER relationship."
        )


        # ====================================================
        # Narrow temporal window negative test
        #
        # 12:00 -> 12:05 span = 5 minutes.
        # A four-minute multi-domain window must reject.
        # ====================================================

        narrow = (
            find_multi_domain_correlations(
                driver,

                scenario_id=
                    SCENARIO_ID,

                window_minutes=
                    4,

                minimum_domains=
                    3,
            )
        )


        assert (
            len(
                narrow
            )
            == 0
        )


        print(
            "PASS: Three-domain correlation "
            "respects temporal window."
        )


        # ====================================================
        # Display
        # ====================================================

        print(
            "\n============================================"
        )
        print(
            "THREE-DOMAIN INFRASTRUCTURE CORRELATION"
        )
        print(
            "============================================"
        )


        print(
            "Scenario:",
            correlation[
                "scenario_id"
            ]
        )


        print(
            "Type:",
            correlation[
                "correlation_type"
            ]
        )


        print(
            "Scope:",
            correlation[
                "scope"
            ]
        )


        print(
            "Shared entity:",
            correlation[
                "shared_entity_id"
            ]
        )


        print(
            "Domains:",
            ", ".join(
                correlation[
                    "domains"
                ]
            )
        )


        print(
            "Events:",
            correlation[
                "event_count"
            ]
        )


        for event in correlation[
            "events"
        ]:

            print(
                "\n",
                event[
                    "domain"
                ],
                sep="",
            )


            print(
                "  State:",
                event[
                    "state"
                ]
            )


            print(
                "  Timestamp:",
                event[
                    "timestamp"
                ]
            )


            print(
                "  Evidence independence:",
                event[
                    "evidence_independence"
                ]
            )


            print(
                "  Server:",
                event[
                    "server_id"
                ]
            )


            print(
                "  Rack:",
                event[
                    "rack_id"
                ]
            )


            print(
                "  Zone:",
                event[
                    "zone_id"
                ]
            )


        print(
            "\nSupporting stronger relationship:"
        )

        print(
            "  CYBERSECURITY + MAINTENANCE"
        )

        print(
            "  Scope: SERVER"
        )

        print(
            "  Shared entity: SRV-B1-01"
        )


        print(
            "\n============================================"
        )
        print(
            "THREE-DOMAIN CORRELATION "
            "CONTRACT SUMMARY"
        )
        print(
            "============================================"
        )


        print(
            "PASS: Cybersecurity integrated."
        )

        print(
            "PASS: Maintenance integrated."
        )

        print(
            "PASS: Environmental sensor integrated."
        )

        print(
            "PASS: Independent sensor evidence preserved."
        )

        print(
            "PASS: Strongest truthful common scope selected."
        )

        print(
            "PASS: Stronger pairwise topology preserved."
        )

        print(
            "PASS: Temporal constraint preserved."
        )


        print(
            "\n============================================"
        )
        print(
            "DC-GUARDIAN THREE-DOMAIN "
            "CORRELATION PASSED"
        )
        print(
            "============================================"
        )


    finally:

        driver.close()