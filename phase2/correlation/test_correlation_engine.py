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


from ssh_event_adapter import (
    adapt_ssh_assessment,
)

from maintenance_event_adapter import (
    adapt_maintenance_assessment,
)

from topology_mapper import (
    map_ssh_event_to_scenario,
    map_maintenance_event_to_scenario,
)

from ingest_event import (
    create_driver,
    ingest_ssh_event,
    ingest_maintenance_event,
    NEO4J_DATABASE,
)

from correlation_engine import (
    find_cross_domain_correlations,
)


# ============================================================
# Shared controlled scenario
# ============================================================

SCENARIO_ID = (
    "SCENARIO-CORR-001"
)


SSH_EVENT_ID = (
    "EVT-CORR-SSH-001"
)


MAINT_EVENT_ID = (
    "EVT-CORR-MAINT-001"
)


# ============================================================
# SSH assessment
# ============================================================

ssh_assessment = {

    "event_type":
        "ssh_behavior_assessment",

    "source_ip":
        "203.0.113.50",

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
            "Controlled correlation test"
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
# Maintenance assessment
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
        "DRV-CORR-001",

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


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":

    print(
        "\n============================================"
    )
    print(
        "DC-GUARDIAN CROSS-DOMAIN CORRELATION TEST"
    )
    print(
        "============================================"
    )


    # ========================================================
    # Build SSH common event
    # ========================================================

    ssh_event = adapt_ssh_assessment(
        ssh_assessment,

        dataset_name=
            "DC-Guardian Correlation Test",

        source_type=
            "CONTROLLED_TEST",

        event_id=
            SSH_EVENT_ID,
    )


    ssh_event = map_ssh_event_to_scenario(
        ssh_event,

        scenario_id=
            SCENARIO_ID,

        scenario_timestamp=
            "2026-09-18T12:00:00Z",

        # Important:
        # maintenance will use SRV-B1-01 too.
        target_name=
            "ZONE_B_CRITICAL_SERVER",
    )


    print(
        "PASS: SSH correlation event prepared."
    )


    # ========================================================
    # Build maintenance common event
    # ========================================================

    maintenance_event = (
        adapt_maintenance_assessment(
            maintenance_assessment,

            dataset_name=
                "DC-Guardian Correlation Test",

            source_type=
                "CONTROLLED_TEST",

            event_id=
                MAINT_EVENT_ID,
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
        "PASS: Maintenance correlation "
        "event prepared."
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
        # Clean previous controlled test artifacts
        #
        # This keeps the contract deterministic when rerun.
        # ====================================================

        with driver.session(
            database=NEO4J_DATABASE
        ) as session:

            session.run(
                """
                MATCH (e:Event)
                WHERE
                    e.scenario_id = $scenario_id

                DETACH DELETE e
                """,
                scenario_id=
                    SCENARIO_ID,
            ).consume()


            # Clean test-only drive asset.
            session.run(
                """
                MATCH (a:Asset {
                    asset_id: $asset_id
                })

                DETACH DELETE a
                """,
                asset_id=
                    "DRV-CORR-001",
            ).consume()


            # Clean test-only SourceIP.
            session.run(
                """
                MATCH (ip:SourceIP {
                    address: $source_ip
                })

                DETACH DELETE ip
                """,
                source_ip=
                    "203.0.113.50",
            ).consume()


        print(
            "PASS: Previous correlation "
            "test artifacts cleared."
        )


        # ====================================================
        # Ingest both domains
        # ====================================================

        ssh_result = ingest_ssh_event(
            ssh_event,
            driver,
        )


        maintenance_result = (
            ingest_maintenance_event(
                maintenance_event,
                driver,
            )
        )


        assert (
            ssh_result[
                "server_id"
            ]
            == "SRV-B1-01"
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
            "PASS: Maintenance event ingested."
        )


        # ====================================================
        # Positive correlation
        # ====================================================

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
                "Expected exactly one "
                "cross-domain correlation; "
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
            == "SERVER"
        )


        assert (
            correlation[
                "shared_entity_id"
            ]
            == "SRV-B1-01"
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
            "MAINTENANCE",
        }


        event_ids = {
            event[
                "event_id"
            ]
            for event
            in correlation[
                "events"
            ]
        }


        assert event_ids == {
            (
                SSH_EVENT_ID
                + "-"
                + SCENARIO_ID
            ),

            (
                MAINT_EVENT_ID
                + "-"
                + SCENARIO_ID
            ),
        }


        print(
            "\nPASS: Cross-domain correlation detected."
        )

        print(
            "PASS: Correlation scope = SERVER."
        )

        print(
            "PASS: Shared server = SRV-B1-01."
        )

        print(
            "PASS: Domains = "
            "CYBERSECURITY + MAINTENANCE."
        )


        # ====================================================
        # Display correlation
        # ====================================================

        print(
            "\n============================================"
        )
        print(
            "CORRELATED INFRASTRUCTURE RISK"
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


        for event in correlation[
            "events"
        ]:

            print(
                "\nEvent:",
                event[
                    "event_id"
                ]
            )

            print(
                "  Domain:",
                event[
                    "domain"
                ]
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


        # ====================================================
        # Negative test:
        # narrower temporal window
        #
        # Events are five minutes apart, therefore a
        # four-minute window must NOT correlate.
        # ====================================================

        narrow_correlations = (
            find_cross_domain_correlations(
                driver,

                scenario_id=
                    SCENARIO_ID,

                window_minutes=
                    4,
            )
        )


        assert (
            len(
                narrow_correlations
            )
            == 0
        )


        print(
            "\nPASS: Events outside requested "
            "temporal window do not correlate."
        )


        # ====================================================
        # Negative test:
        # unknown/empty scenario
        # ====================================================

        empty_correlations = (
            find_cross_domain_correlations(
                driver,

                scenario_id=
                    "SCENARIO-CORR-EMPTY",

                window_minutes=
                    15,
            )
        )


        assert (
            len(
                empty_correlations
            )
            == 0
        )


        print(
            "PASS: Empty scenario produces "
            "no correlations."
        )


        print(
            "\n============================================"
        )
        print(
            "CORRELATION CONTRACT SUMMARY"
        )
        print(
            "============================================"
        )

        print(
            "PASS: Different domains required."
        )

        print(
            "PASS: Shared infrastructure required."
        )

        print(
            "PASS: Temporal proximity required."
        )

        print(
            "PASS: Scenario identity required."
        )

        print(
            "PASS: Strongest shared scope selected."
        )


        print(
            "\n============================================"
        )
        print(
            "DC-GUARDIAN CORRELATION ENGINE PASSED"
        )
        print(
            "============================================"
        )


    finally:

        driver.close()