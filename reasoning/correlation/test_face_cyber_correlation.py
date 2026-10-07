"""
DC-Guardian Phase 2
Physical-Security + Cybersecurity Correlation Contract

Positive:
    P003 recognized at CAM-B-01
        -> ZONE-B
        -> UNAUTHORIZED

    SSH HIGH_CONFIDENCE_ANOMALY
        -> SRV-B1-01
        -> RACK-B1
        -> ZONE-B

Expected:
    PHYSICAL_SECURITY + CYBERSECURITY
    strongest truthful common scope = ZONE
    shared entity = ZONE-B

Negative controls:
    AUTHORIZED access does not correlate.
    AUTHORIZATION_UNKNOWN does not correlate.
    Events outside temporal window do not correlate.
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
    PROJECT_ROOT,
    PROJECT_ROOT / "reasoning" / "adapters",
    PROJECT_ROOT / "reasoning" / "topology",
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

from ssh_event_adapter import (
    adapt_ssh_assessment,
)

from face_event_adapter import (
    adapt_face_assessment,
)

from topology_mapper import (
    map_ssh_event_to_scenario,
    map_face_event_to_scenario,
)

from ingest_event import (
    create_driver,
    ingest_ssh_event,
    ingest_face_event,
    NEO4J_DATABASE,
)

from correlation_engine import (
    find_cross_domain_correlations,
    resolve_event_contexts,
)


# ============================================================
# Scenario constants
# ============================================================

SCENARIO_ID = (
    "SCENARIO-CORR-FACE-CYBER-001"
)

SSH_EVENT_ID = (
    "EVT-CORR-FACE-CYBER-SSH-001"
)

FACE_EVENT_ID = (
    "EVT-CORR-FACE-CYBER-P003"
)


# ============================================================
# Controlled SSH assessment
#
# Uses the same contract shape as the existing passing
# test_correlation_engine.py.
# ============================================================

ssh_assessment = {

    "event_type":
        "ssh_behavior_assessment",

    "source_ip":
        "203.0.113.60",

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
            "Controlled Face-Cyber correlation test"
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
# Controlled Face assessment
# ============================================================

def make_face_assessment(
    person_id,
):

    return {
        "domain":
            "PHYSICAL_SECURITY",

        "event_type":
            "FACE_IDENTIFICATION_ASSESSMENT",

        "image":
            f"{person_id}_correlation.jpg",

        "model_name":
            "ArcFace",

        "detector_backend":
            "retinaface",

        "distance_metric":
            "cosine",

        "threshold":
            0.50,

        "threshold_source":
            "validation_only",

        "configuration_frozen":
            True,

        "person_id":
            person_id,

        "recognition_status":
            "RECOGNIZED",

        "face_detected":
            True,

        "face_count":
            1,

        "distance":
            0.25,

        "similarity":
            0.75,

        "nearest_employee_id":
            person_id,

        "face_confidence":
            1.0,

        "facial_area":
            None,

        "latency_ms":
            100.0,
    }


# ============================================================
# SSH preparation
# ============================================================

def prepare_ssh_event(
    *,
    scenario_id,
    timestamp,
):

    event = adapt_ssh_assessment(
        ssh_assessment,

        dataset_name=
            "DC-Guardian Face-Cyber Correlation Test",

        source_type=
            "CONTROLLED_TEST",

        event_id=
            SSH_EVENT_ID,
    )


    return map_ssh_event_to_scenario(
        event,

        scenario_id=
            scenario_id,

        scenario_timestamp=
            timestamp,

        target_name=
            "ZONE_B_CRITICAL_SERVER",
    )


# ============================================================
# Face preparation
# ============================================================

def prepare_face_event(
    person_id,
    *,
    event_id,
    scenario_id,
    timestamp,
    camera_id="CAM-B-01",
):

    event = adapt_face_assessment(
        make_face_assessment(
            person_id
        ),

        dataset_name=
            "DC-Guardian Controlled Face Dataset v1",

        source_type=
            "CONTROLLED_TEST",

        event_id=
            event_id,

        timestamp=
            timestamp,
    )


    return map_face_event_to_scenario(
        event,

        scenario_id=
            scenario_id,

        scenario_timestamp=
            timestamp,

        camera_id=
            camera_id,
    )


# ============================================================
# Cleanup helper
# ============================================================

def clear_scenario(
    driver,
    scenario_id,
):

    with driver.session(
        database=NEO4J_DATABASE
    ) as session:

        session.run(
            """
            MATCH (event:Event)
            WHERE event.scenario_id = $scenario_id
            DETACH DELETE event
            """,

            scenario_id=
                scenario_id,
        ).consume()


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":

    print(
        "\n============================================"
    )
    print(
        "DC-GUARDIAN FACE + CYBER CORRELATION TEST"
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
        # Positive scenario
        #
        # P003 is authorized only for ZONE-C.
        # CAM-B-01 observes ZONE-B.
        # ====================================================

        clear_scenario(
            driver,
            SCENARIO_ID,
        )


        ssh_event = prepare_ssh_event(
            scenario_id=
                SCENARIO_ID,

            timestamp=
                "2026-09-24T16:03:00Z",
        )


        face_event = prepare_face_event(
            "P003",

            event_id=
                FACE_EVENT_ID,

            scenario_id=
                SCENARIO_ID,

            timestamp=
                "2026-09-24T16:00:00Z",
        )


        print(
            "PASS: SSH correlation event prepared."
        )

        print(
            "PASS: Face correlation event prepared."
        )


        ssh_result = ingest_ssh_event(
            ssh_event,
            driver,
        )


        face_result = ingest_face_event(
            face_event,
            driver,
        )


        assert (
            ssh_result[
                "server_id"
            ]
            == "SRV-B1-01"
        )


        assert (
            face_result[
                "authorization_status"
            ]
            == "UNAUTHORIZED"
        )


        print(
            "PASS: Cybersecurity event ingested."
        )

        print(
            "PASS: Unauthorized physical-security "
            "event ingested."
        )


        # ====================================================
        # Context resolution
        # ====================================================

        contexts = resolve_event_contexts(
            driver,

            scenario_id=
                SCENARIO_ID,
        )


        cyber_contexts = [
            context
            for context in contexts
            if (
                context[
                    "domain"
                ]
                == "CYBERSECURITY"
            )
        ]


        physical_contexts = [
            context
            for context in contexts
            if (
                context[
                    "domain"
                ]
                == "PHYSICAL_SECURITY"
            )
        ]


        assert (
            len(
                cyber_contexts
            )
            == 1
        )


        assert (
            len(
                physical_contexts
            )
            == 1
        )


        cyber_context = (
            cyber_contexts[
                0
            ]
        )

        physical_context = (
            physical_contexts[
                0
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
            physical_context[
                "server_id"
            ]
            is None
        )

        assert (
            physical_context[
                "rack_id"
            ]
            is None
        )

        assert (
            physical_context[
                "zone_id"
            ]
            == "ZONE-B"
        )

        assert (
            physical_context[
                "topology_origin"
            ]
            == "CAMERA"
        )

        assert (
            physical_context[
                "authorization_status"
            ]
            == "UNAUTHORIZED"
        )


        print(
            "PASS: Cybersecurity context resolved "
            "to SRV-B1-01 / RACK-B1 / ZONE-B."
        )

        print(
            "PASS: Physical-security context remains "
            "truthfully ZONE scoped."
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


        if (
            len(
                correlations
            )
            != 1
        ):

            raise AssertionError(
                "Expected exactly one Face-Cyber "
                "correlation; "
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
            "CYBERSECURITY",
            "PHYSICAL_SECURITY",
        }


        physical_evidence = next(
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
            physical_evidence[
                "state"
            ]
            == "RECOGNIZED_PERSON"
        )


        assert (
            physical_evidence[
                "authorization_status"
            ]
            == "UNAUTHORIZED"
        )


        print()
        print(
            "PASS: Face + Cyber correlation detected."
        )

        print(
            "PASS: Correlation scope = ZONE."
        )

        print(
            "PASS: Shared entity = ZONE-B."
        )

        print(
            "PASS: Domains = PHYSICAL_SECURITY + "
            "CYBERSECURITY."
        )


        # ====================================================
        # Display
        # ====================================================

        print(
            "\n============================================"
        )
        print(
            "FACE + CYBER INFRASTRUCTURE CORRELATION"
        )
        print(
            "============================================"
        )


        print(
            "Scenario:",
            correlation[
                "scenario_id"
            ],
        )

        print(
            "Scope:",
            correlation[
                "scope"
            ],
        )

        print(
            "Shared entity:",
            correlation[
                "shared_entity_id"
            ],
        )


        for event in correlation[
            "events"
        ]:

            print()

            print(
                "Event:",
                event[
                    "event_id"
                ],
            )

            print(
                "  Domain:",
                event[
                    "domain"
                ],
            )

            print(
                "  State:",
                event[
                    "state"
                ],
            )

            print(
                "  Authorization:",
                event.get(
                    "authorization_status"
                ),
            )

            print(
                "  Timestamp:",
                event[
                    "timestamp"
                ],
            )


        # ====================================================
        # Negative 1:
        # Authorized P001 must not correlate.
        # ====================================================

        authorized_scenario = (
            "SCENARIO-CORR-FACE-AUTHORIZED"
        )


        clear_scenario(
            driver,
            authorized_scenario,
        )


        authorized_ssh = prepare_ssh_event(
            scenario_id=
                authorized_scenario,

            timestamp=
                "2026-09-24T17:03:00Z",
        )


        authorized_face = prepare_face_event(
            "P001",

            event_id=
                "EVT-CORR-FACE-AUTH-P001",

            scenario_id=
                authorized_scenario,

            timestamp=
                "2026-09-24T17:00:00Z",
        )


        ingest_ssh_event(
            authorized_ssh,
            driver,
        )


        authorized_result = (
            ingest_face_event(
                authorized_face,
                driver,
            )
        )


        assert (
            authorized_result[
                "authorization_status"
            ]
            == "AUTHORIZED"
        )


        authorized_correlations = (
            find_cross_domain_correlations(
                driver,

                scenario_id=
                    authorized_scenario,

                window_minutes=
                    15,
            )
        )


        assert (
            authorized_correlations
            == []
        )


        print(
            "\nPASS: AUTHORIZED Face observation "
            "does not correlate."
        )


        # ====================================================
        # Negative 2:
        # P004 has no topology Person record.
        # ====================================================

        unknown_auth_scenario = (
            "SCENARIO-CORR-FACE-AUTH-UNKNOWN"
        )


        clear_scenario(
            driver,
            unknown_auth_scenario,
        )


        p004_ssh = prepare_ssh_event(
            scenario_id=
                unknown_auth_scenario,

            timestamp=
                "2026-09-24T18:03:00Z",
        )


        p004_face = prepare_face_event(
            "P004",

            event_id=
                "EVT-CORR-FACE-AUTH-P004",

            scenario_id=
                unknown_auth_scenario,

            timestamp=
                "2026-09-24T18:00:00Z",
        )


        ingest_ssh_event(
            p004_ssh,
            driver,
        )


        p004_result = (
            ingest_face_event(
                p004_face,
                driver,
            )
        )


        assert (
            p004_result[
                "authorization_status"
            ]
            == "AUTHORIZATION_UNKNOWN"
        )


        p004_correlations = (
            find_cross_domain_correlations(
                driver,

                scenario_id=
                    unknown_auth_scenario,

                window_minutes=
                    15,
            )
        )


        assert (
            p004_correlations
            == []
        )


        print(
            "PASS: AUTHORIZATION_UNKNOWN Face "
            "observation does not correlate."
        )


        # ====================================================
        # Negative 3:
        # temporal separation
        # ====================================================

        temporal_scenario = (
            "SCENARIO-CORR-FACE-TEMPORAL"
        )


        clear_scenario(
            driver,
            temporal_scenario,
        )


        temporal_face = prepare_face_event(
            "P003",

            event_id=
                "EVT-CORR-FACE-TEMP-P003",

            scenario_id=
                temporal_scenario,

            timestamp=
                "2026-09-24T19:00:00Z",
        )


        temporal_ssh = prepare_ssh_event(
            scenario_id=
                temporal_scenario,

            timestamp=
                "2026-09-24T19:30:00Z",
        )


        ingest_face_event(
            temporal_face,
            driver,
        )


        ingest_ssh_event(
            temporal_ssh,
            driver,
        )


        temporal_correlations = (
            find_cross_domain_correlations(
                driver,

                scenario_id=
                    temporal_scenario,

                window_minutes=
                    15,
            )
        )


        assert (
            temporal_correlations
            == []
        )


        print(
            "PASS: Events outside temporal window "
            "do not correlate."
        )


        # ====================================================
        # Empty scenario
        # ====================================================

        empty = (
            find_cross_domain_correlations(
                driver,

                scenario_id=
                    "SCENARIO-CORR-FACE-EMPTY",

                window_minutes=
                    15,
            )
        )


        assert empty == []


        print(
            "PASS: Empty scenario produces "
            "no correlations."
        )


        # ====================================================
        # Summary
        # ====================================================

        print(
            "\n============================================"
        )
        print(
            "FACE + CYBER CORRELATION CONTRACT SUMMARY"
        )
        print(
            "============================================"
        )

        print(
            "PASS: Physical Security participates "
            "in correlation."
        )

        print(
            "PASS: UNAUTHORIZED access is eligible."
        )

        print(
            "PASS: AUTHORIZED access is excluded."
        )

        print(
            "PASS: AUTHORIZATION_UNKNOWN is excluded."
        )

        print(
            "PASS: Camera contributes truthful "
            "Zone context."
        )

        print(
            "PASS: Strongest truthful common "
            "scope selected."
        )

        print(
            "PASS: Temporal constraint preserved."
        )

        print(
            "PASS: Scenario identity preserved."
        )


        print(
            "\n============================================"
        )
        print(
            "DC-GUARDIAN FACE + CYBER "
            "CORRELATION PASSED"
        )
        print(
            "============================================"
        )


    finally:

        driver.close()
