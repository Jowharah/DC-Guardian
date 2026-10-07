"""Real Reasoning vertical slice for controlled PPE + Face evidence.

Uses the existing adapters, topology mapping, Neo4j ingestion, authorization
resolution, and deterministic correlation implementation. Evidence inputs are
controlled frozen assessment-shaped records; no neural model is loaded here.
"""

from __future__ import annotations

from reasoning.adapters.face_event_adapter import adapt_face_assessment
from reasoning.adapters.ppe_event_adapter import adapt_ppe_assessment
from reasoning.correlation.correlation_engine import (
    find_cross_domain_correlations,
    resolve_event_contexts,
)
from reasoning.graph.ingest_event import (
    NEO4J_DATABASE,
    create_driver,
    ingest_face_event,
    ingest_ppe_event,
)
from reasoning.topology.topology_mapper import (
    map_face_event_to_scenario,
    map_ppe_event_to_scenario,
)


def _face_assessment(person_id: str) -> dict:
    return {
        "domain": "PHYSICAL_SECURITY",
        "event_type": "FACE_IDENTIFICATION_ASSESSMENT",
        "image": f"{person_id}_integration.jpg",
        "model_name": "ArcFace",
        "detector_backend": "retinaface",
        "distance_metric": "cosine",
        "threshold": 0.50,
        "threshold_source": "validation_only",
        "configuration_frozen": True,
        "person_id": person_id,
        "recognition_status": "RECOGNIZED",
        "face_detected": True,
        "face_count": 1,
        "distance": 0.25,
        "similarity": 0.75,
        "nearest_employee_id": person_id,
        "face_confidence": 1.0,
        "facial_area": None,
        "latency_ms": 100.0,
    }


def _ppe_assessment() -> dict:
    return {
        "domain": "PHYSICAL_SECURITY",
        "event_type": "PPE_COMPLIANCE_ASSESSMENT",
        "model_family": "YOLOv8",
        "architecture": "YOLOv8n",
        "model_weights": "ppe_yolov8_best.pt",
        "detector_configuration": "PPE-v1",
        "detector_configuration_frozen": True,
        "policy_version": "PPE-POLICY-v1",
        "policy_name": "BASELINE_DC_MAINTENANCE",
        "policy_frozen": True,
        "policy_source": "project_defined_baseline",
        "required_ppe": ["helmet", "safety-vest"],
        "confidence_threshold": 0.25,
        "iou_threshold": 0.70,
        "association_method": "object_containment",
        "association_minimum_containment": 0.50,
        "person_assignment": "strongest_eligible_match",
        "person_detected": True,
        "person_count": 1,
        "overall_status": "NON_COMPLIANT",
        "people": [{
            "person_index": 0,
            "status": "NON_COMPLIANT",
            "required_ppe": ["helmet", "safety-vest"],
            "required_ppe_detected": ["helmet"],
            "required_ppe_not_detected": ["safety-vest"],
            "optional_ppe_detected": [],
            "all_associated_classes": ["helmet"],
        }],
        "detections": [],
        "unassigned_detections": [],
        "latency_ms": 100.0,
    }


def _clear(driver, scenario_id: str) -> None:
    with driver.session(database=NEO4J_DATABASE) as session:
        session.run(
            "MATCH (event:Event) WHERE event.scenario_id = $scenario_id "
            "DETACH DELETE event",
            scenario_id=scenario_id,
        ).consume()


def run_real_ppe_face_reasoning(
    *,
    scenario_id: str,
    person_id: str = "P003",
    camera_id: str = "CAM-B-01",
) -> dict:
    ppe_time = "2026-10-06T12:00:00Z"
    face_time = "2026-10-06T12:03:00Z"

    ppe_event = adapt_ppe_assessment(
        _ppe_assessment(),
        dataset_name="DC-Guardian Controlled PPE Dataset v1",
        source_type="CONTROLLED_TEST",
        event_id=f"{scenario_id}-PPE",
        timestamp=ppe_time,
    )
    ppe_event = map_ppe_event_to_scenario(
        ppe_event,
        scenario_id=scenario_id,
        scenario_timestamp=ppe_time,
        camera_id=camera_id,
    )

    face_event = adapt_face_assessment(
        _face_assessment(person_id),
        dataset_name="DC-Guardian Controlled Face Dataset v1",
        source_type="CONTROLLED_TEST",
        event_id=f"{scenario_id}-FACE",
        timestamp=face_time,
    )
    face_event = map_face_event_to_scenario(
        face_event,
        scenario_id=scenario_id,
        scenario_timestamp=face_time,
        camera_id=camera_id,
    )

    driver = create_driver()
    try:
        _clear(driver, scenario_id)
        ppe_ingest = ingest_ppe_event(ppe_event, driver)
        face_ingest = ingest_face_event(face_event, driver)

        if ppe_ingest["state"] != "PPE_NON_COMPLIANT":
            raise RuntimeError("Expected PPE_NON_COMPLIANT after ingestion.")
        if face_ingest["authorization_status"] != "UNAUTHORIZED":
            raise RuntimeError("Expected graph-derived UNAUTHORIZED Face status.")

        contexts = resolve_event_contexts(driver, scenario_id=scenario_id)
        correlations = find_cross_domain_correlations(
            driver,
            scenario_id=scenario_id,
            window_minutes=15,
        )
        if len(correlations) != 1:
            raise RuntimeError(
                f"Expected one PPE/Face correlation, found {len(correlations)}."
            )
        correlation = correlations[0]
        domains = sorted({x["domain"] for x in correlation["events"]})
        if domains != ["PHYSICAL_SECURITY", "SAFETY"]:
            raise RuntimeError(f"Unexpected correlated domains: {domains}")

        return {
            "scenario_id": scenario_id,
            "domains": domains,
            "correlation": correlation,
            "contexts": contexts,
            "shared_scope": correlation["scope"],
            "shared_entity": correlation["shared_entity_id"],
            "authorization_status": face_ingest["authorization_status"],
            "identity_link_established": False,
            "evidence_events": [ppe_event, face_event],
        }
    finally:
        driver.close()

