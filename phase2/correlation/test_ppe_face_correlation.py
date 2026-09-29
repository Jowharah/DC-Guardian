"""
DC-Guardian Phase 2
PPE Safety + Physical-Security Correlation Contract

Positive:
    PPE_NON_COMPLIANT
        -> CAM-B-01
        -> ZONE-B

    P003 recognized at CAM-B-01
        -> ZONE-B
        -> UNAUTHORIZED

Expected:
    SAFETY + PHYSICAL_SECURITY
    strongest truthful common scope = ZONE
    shared entity = ZONE-B

IMPORTANT:
    This correlation establishes shared physical context
    and temporal proximity.

    It does NOT establish that the recognized Face identity
    is the same anonymous person_index observed by PPE.

Negative controls:
    PPE_COMPLIANT does not correlate.
    NO_PERSON_DETECTED does not correlate.
    AUTHORIZED Face does not correlate.
    AUTHORIZATION_UNKNOWN Face does not correlate.
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
# Imports
# ============================================================

from face_event_adapter import (
    adapt_face_assessment,
)

from ppe_event_adapter import (
    adapt_ppe_assessment,
)

from topology_mapper import (
    map_face_event_to_scenario,
    map_ppe_event_to_scenario,
)

from ingest_event import (
    create_driver,
    ingest_face_event,
    ingest_ppe_event,
    NEO4J_DATABASE,
)

from correlation_engine import (
    find_cross_domain_correlations,
    resolve_event_contexts,
)


# ============================================================
# Constants
# ============================================================

SCENARIO_ID = (
    "SCENARIO-CORR-PPE-FACE-001"
)

PPE_EVENT_ID = (
    "EVT-CORR-PPE-FACE-PPE-001"
)

FACE_EVENT_ID = (
    "EVT-CORR-PPE-FACE-P003"
)


# ============================================================
# PPE assessment builders
# ============================================================

def make_ppe_person(
    index,
    status,
    detected,
    not_detected,
):

    return {
        "person_index":
            index,

        "status":
            status,

        "required_ppe": [
            "helmet",
            "safety-vest",
        ],

        "required_ppe_detected":
            detected,

        "required_ppe_not_detected":
            not_detected,

        "optional_ppe_detected":
            [],

        "all_associated_classes":
            list(
                detected
            ),
    }


def make_ppe_assessment(
    status,
):

    if status == "NON_COMPLIANT":

        people = [
            make_ppe_person(
                0,
                "NON_COMPLIANT",
                [
                    "helmet",
                ],
                [
                    "safety-vest",
                ],
            )
        ]


    elif status == "COMPLIANT":

        people = [
            make_ppe_person(
                0,
                "COMPLIANT",
                [
                    "helmet",
                    "safety-vest",
                ],
                [],
            )
        ]


    elif status == "NO_PERSON":

        people = []


    else:

        raise ValueError(
            f"Unsupported controlled PPE status: {status}"
        )


    return {
        "domain":
            "PHYSICAL_SECURITY",

        "event_type":
            "PPE_COMPLIANCE_ASSESSMENT",

        "model_family":
            "YOLOv8",

        "architecture":
            "YOLOv8n",

        "model_weights":
            "ppe_yolov8_best.pt",

        "detector_configuration":
            "PPE-v1",

        "detector_configuration_frozen":
            True,

        "policy_version":
            "PPE-POLICY-v1",

        "policy_name":
            "BASELINE_DC_MAINTENANCE",

        "policy_frozen":
            True,

        "policy_source":
            "project_defined_baseline",

        "required_ppe": [
            "helmet",
            "safety-vest",
        ],

        "confidence_threshold":
            0.25,

        "iou_threshold":
            0.70,

        "association_method":
            "object_containment",

        "association_minimum_containment":
            0.50,

        "person_assignment":
            "strongest_eligible_match",

        "person_detected":
            bool(
                people
            ),

        "person_count":
            len(
                people
            ),

        "overall_status":
            status,

        "people":
            people,

        "detections":
            [],

        "unassigned_detections":
            [],

        "latency_ms":
            100.0,
    }


# ============================================================
# Face assessment
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
            f"{person_id}_ppe_face_correlation.jpg",

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
# PPE preparation
# ============================================================

def prepare_ppe_event(
    status,
    *,
    event_id,
    scenario_id,
    timestamp,
    camera_id="CAM-B-01",
):

    event = adapt_ppe_assessment(
        make_ppe_assessment(
            status
        ),

        dataset_name=
            "DC-Guardian Controlled PPE Dataset v1",

        source_type=
            "CONTROLLED_TEST",

        event_id=
            event_id,

        timestamp=
            timestamp,
    )


    return map_ppe_event_to_scenario(
        event,

        scenario_id=
            scenario_id,

        scenario_timestamp=
            timestamp,

        camera_id=
            camera_id,
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
# Cleanup
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
        "DC-GUARDIAN PPE + FACE CORRELATION TEST"
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
        # Positive
        # ====================================================

        clear_scenario(
            driver,
            SCENARIO_ID,
        )


        ppe_event = prepare_ppe_event(
            "NON_COMPLIANT",

            event_id=
                PPE_EVENT_ID,

            scenario_id=
                SCENARIO_ID,

            timestamp=
                "2026-09-27T11:00:00Z",
        )


        face_event = prepare_face_event(
            "P003",

            event_id=
                FACE_EVENT_ID,

            scenario_id=
                SCENARIO_ID,

            timestamp=
                "2026-09-27T11:03:00Z",
        )


        ppe_result = ingest_ppe_event(
            ppe_event,
            driver,
        )


        face_result = ingest_face_event(
            face_event,
            driver,
        )


        assert (
            ppe_result[
                "state"
            ]
            == "PPE_NON_COMPLIANT"
        )


        assert (
            face_result[
                "authorization_status"
            ]
            == "UNAUTHORIZED"
        )


        print(
            "PASS: PPE non-compliance event ingested."
        )

        print(
            "PASS: Unauthorized Face event ingested."
        )


        # ====================================================
        # Contexts
        # ====================================================

        contexts = resolve_event_contexts(
            driver,

            scenario_id=
                SCENARIO_ID,
        )


        safety_contexts = [
            context
            for context in contexts
            if (
                context[
                    "domain"
                ]
                == "SAFETY"
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


        assert len(
            safety_contexts
        ) == 1


        assert len(
            physical_contexts
        ) == 1


        safety_context = (
            safety_contexts[
                0
            ]
        )

        physical_context = (
            physical_contexts[
                0
            ]
        )


        for context in [
            safety_context,
            physical_context,
        ]:

            assert (
                context[
                    "server_id"
                ]
                is None
            )

            assert (
                context[
                    "rack_id"
                ]
                is None
            )

            assert (
                context[
                    "zone_id"
                ]
                == "ZONE-B"
            )

            assert (
                context[
                    "topology_origin"
                ]
                == "CAMERA"
            )


        print(
            "PASS: PPE context remains truthfully "
            "ZONE scoped."
        )

        print(
            "PASS: Face context remains truthfully "
            "ZONE scoped."
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
                "Expected exactly one PPE-Face "
                "correlation; "
                f"found {len(correlations)}."
            )


        correlation = correlations[
            0
        ]


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


        safety_evidence = next(
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
            safety_evidence[
                "state"
            ]
            == "PPE_NON_COMPLIANT"
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
            "PASS: PPE + Face correlation detected."
        )

        print(
            "PASS: Correlation scope = ZONE."
        )

        print(
            "PASS: Shared entity = ZONE-B."
        )

        print(
            "PASS: Domains = SAFETY + "
            "PHYSICAL_SECURITY."
        )


        print(
            "PASS: Correlation does not claim "
            "PPE person_index equals Face identity."
        )


        # ====================================================
        # Negative 1: COMPLIANT PPE
        # ====================================================

        compliant_scenario = (
            "SCENARIO-CORR-PPE-COMPLIANT"
        )


        clear_scenario(
            driver,
            compliant_scenario,
        )


        compliant_ppe = prepare_ppe_event(
            "COMPLIANT",

            event_id=
                "EVT-CORR-PPE-COMPLIANT",

            scenario_id=
                compliant_scenario,

            timestamp=
                "2026-09-27T12:00:00Z",
        )


        unauthorized_face = prepare_face_event(
            "P003",

            event_id=
                "EVT-CORR-PPE-COMPLIANT-FACE",

            scenario_id=
                compliant_scenario,

            timestamp=
                "2026-09-27T12:03:00Z",
        )


        ingest_ppe_event(
            compliant_ppe,
            driver,
        )

        ingest_face_event(
            unauthorized_face,
            driver,
        )


        assert (
            find_cross_domain_correlations(
                driver,

                scenario_id=
                    compliant_scenario,

                window_minutes=
                    15,
            )
            == []
        )


        print(
            "\nPASS: COMPLIANT PPE does not correlate."
        )


        # ====================================================
        # Negative 2: NO_PERSON
        # ====================================================

        no_person_scenario = (
            "SCENARIO-CORR-PPE-NO-PERSON"
        )


        clear_scenario(
            driver,
            no_person_scenario,
        )


        no_person_ppe = prepare_ppe_event(
            "NO_PERSON",

            event_id=
                "EVT-CORR-PPE-NO-PERSON",

            scenario_id=
                no_person_scenario,

            timestamp=
                "2026-09-27T13:00:00Z",
        )


        no_person_face = prepare_face_event(
            "P003",

            event_id=
                "EVT-CORR-PPE-NO-PERSON-FACE",

            scenario_id=
                no_person_scenario,

            timestamp=
                "2026-09-27T13:03:00Z",
        )


        ingest_ppe_event(
            no_person_ppe,
            driver,
        )

        ingest_face_event(
            no_person_face,
            driver,
        )


        assert (
            find_cross_domain_correlations(
                driver,

                scenario_id=
                    no_person_scenario,

                window_minutes=
                    15,
            )
            == []
        )


        print(
            "PASS: NO_PERSON PPE does not correlate."
        )


        # ====================================================
        # Negative 3: AUTHORIZED Face
        # ====================================================

        authorized_scenario = (
            "SCENARIO-CORR-PPE-FACE-AUTHORIZED"
        )


        clear_scenario(
            driver,
            authorized_scenario,
        )


        authorized_ppe = prepare_ppe_event(
            "NON_COMPLIANT",

            event_id=
                "EVT-CORR-PPE-FACE-AUTH-PPE",

            scenario_id=
                authorized_scenario,

            timestamp=
                "2026-09-27T14:00:00Z",
        )


        authorized_face = prepare_face_event(
            "P001",

            event_id=
                "EVT-CORR-PPE-FACE-AUTH-P001",

            scenario_id=
                authorized_scenario,

            timestamp=
                "2026-09-27T14:03:00Z",
        )


        ingest_ppe_event(
            authorized_ppe,
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


        assert (
            find_cross_domain_correlations(
                driver,

                scenario_id=
                    authorized_scenario,

                window_minutes=
                    15,
            )
            == []
        )


        print(
            "PASS: AUTHORIZED Face does not correlate."
        )


        # ====================================================
        # Negative 4: AUTHORIZATION_UNKNOWN
        # ====================================================

        unknown_auth_scenario = (
            "SCENARIO-CORR-PPE-FACE-AUTH-UNKNOWN"
        )


        clear_scenario(
            driver,
            unknown_auth_scenario,
        )


        unknown_auth_ppe = prepare_ppe_event(
            "NON_COMPLIANT",

            event_id=
                "EVT-CORR-PPE-FACE-AUTH-UNKNOWN-PPE",

            scenario_id=
                unknown_auth_scenario,

            timestamp=
                "2026-09-27T15:00:00Z",
        )


        unknown_auth_face = prepare_face_event(
            "P004",

            event_id=
                "EVT-CORR-PPE-FACE-AUTH-P004",

            scenario_id=
                unknown_auth_scenario,

            timestamp=
                "2026-09-27T15:03:00Z",
        )


        ingest_ppe_event(
            unknown_auth_ppe,
            driver,
        )


        p004_result = ingest_face_event(
            unknown_auth_face,
            driver,
        )


        assert (
            p004_result[
                "authorization_status"
            ]
            == "AUTHORIZATION_UNKNOWN"
        )


        assert (
            find_cross_domain_correlations(
                driver,

                scenario_id=
                    unknown_auth_scenario,

                window_minutes=
                    15,
            )
            == []
        )


        print(
            "PASS: AUTHORIZATION_UNKNOWN Face "
            "does not correlate."
        )


        # ====================================================
        # Negative 5: Temporal separation
        # ====================================================

        temporal_scenario = (
            "SCENARIO-CORR-PPE-FACE-TEMPORAL"
        )


        clear_scenario(
            driver,
            temporal_scenario,
        )


        temporal_ppe = prepare_ppe_event(
            "NON_COMPLIANT",

            event_id=
                "EVT-CORR-PPE-FACE-TEMP-PPE",

            scenario_id=
                temporal_scenario,

            timestamp=
                "2026-09-27T16:00:00Z",
        )


        temporal_face = prepare_face_event(
            "P003",

            event_id=
                "EVT-CORR-PPE-FACE-TEMP-FACE",

            scenario_id=
                temporal_scenario,

            timestamp=
                "2026-09-27T16:30:00Z",
        )


        ingest_ppe_event(
            temporal_ppe,
            driver,
        )

        ingest_face_event(
            temporal_face,
            driver,
        )


        assert (
            find_cross_domain_correlations(
                driver,

                scenario_id=
                    temporal_scenario,

                window_minutes=
                    15,
            )
            == []
        )


        print(
            "PASS: Events outside temporal window "
            "do not correlate."
        )


        # ====================================================
        # Empty
        # ====================================================

        empty = (
            find_cross_domain_correlations(
                driver,

                scenario_id=
                    "SCENARIO-CORR-PPE-FACE-EMPTY",

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
            "PPE + FACE CORRELATION CONTRACT SUMMARY"
        )
        print(
            "============================================"
        )

        print(
            "PASS: SAFETY participates in correlation."
        )

        print(
            "PASS: PPE_NON_COMPLIANT is eligible."
        )

        print(
            "PASS: PPE_COMPLIANT is excluded."
        )

        print(
            "PASS: NO_PERSON_DETECTED is excluded."
        )

        print(
            "PASS: UNAUTHORIZED Face is eligible."
        )

        print(
            "PASS: AUTHORIZED Face is excluded."
        )

        print(
            "PASS: AUTHORIZATION_UNKNOWN is excluded."
        )

        print(
            "PASS: Both camera observations contribute "
            "truthful Zone context."
        )

        print(
            "PASS: Strongest truthful common scope "
            "selected."
        )

        print(
            "PASS: Temporal constraint preserved."
        )

        print(
            "PASS: Scenario identity preserved."
        )

        print(
            "PASS: No cross-model person identity "
            "claim introduced."
        )


        print(
            "\n============================================"
        )
        print(
            "DC-GUARDIAN PPE + FACE "
            "CORRELATION PASSED"
        )
        print(
            "============================================"
        )


    finally:

        driver.close()