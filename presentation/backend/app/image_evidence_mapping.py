"""Controlled image observation metadata and bounded Neo4j projection.

This is a provenance-aware graph projection, not a validated Common Event
adapter, correlation result, or Decision. Camera/time are operator declarations.
"""
from datetime import datetime,timezone
from pathlib import Path
import json
from reasoning.topology.topology_mapper import load_topology,build_camera_index
from reasoning.graph.ingest_event import create_driver,NEO4J_DATABASE

def validate_metadata(value,zone):
    if not isinstance(value,dict):
        raise ValueError("Image metadata must be an object")
    camera=value.get("camera_id")
    timestamp=value.get("captured_at")
    if not isinstance(camera,str) or not isinstance(timestamp,str):
        raise ValueError("camera_id and captured_at are required")
    camera_info=build_camera_index(load_topology()).get(camera)
    if not camera_info or camera_info["zone_id"]!=zone:
        raise ValueError("Camera not in selected zone topology")
    try:
        parsed=datetime.fromisoformat(timestamp.replace("Z","+00:00"))
    except ValueError as exc:
        raise ValueError("Invalid ISO-8601 capture timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError("Capture timestamp requires timezone")
    if parsed.astimezone(timezone.utc)>datetime.now(timezone.utc):
        raise ValueError("Capture timestamp cannot be in the future")
    return {"camera_id":camera,"zone_id":zone,
            "captured_at":parsed.astimezone(timezone.utc).isoformat(),
            "provenance":"OPERATOR_DECLARED_UNVERIFIED"}

def project_observation(kind,observation_id,assessment,metadata):
    if kind not in ("ppe","face"):
        raise ValueError("Unsupported image Evidence domain")
    state=assessment["overall_status"] if kind=="ppe" else assessment["recognition_status"]
    domain="SAFETY" if kind=="ppe" else "PHYSICAL_SECURITY"
    event_type="PPE_COMPLIANCE_ASSESSMENT" if kind=="ppe" else "FACE_IDENTIFICATION_ASSESSMENT"
    event_id="IMG-EVT-"+observation_id
    driver=create_driver()
    try:
        with driver.session(database=NEO4J_DATABASE) as session:
            result=session.run("""
              MATCH (camera:Camera {camera_id:$camera_id})
              MERGE (event:Event {event_id:$event_id})
              SET event.domain=$domain,event.event_type=$event_type,
                  event.state=$state,event.timestamp=datetime($timestamp),
                  event.original_event_id=$observation_id,
                  event.source_type='OPERATOR_UPLOADED_IMAGE',
                  event.provenance_status='OPERATOR_DECLARED_UNVERIFIED'
              MERGE (event)-[:OBSERVED_BY]->(camera)
              RETURN event.event_id AS id
            """,camera_id=metadata["camera_id"],event_id=event_id,
                domain=domain,event_type=event_type,state=state,
                timestamp=metadata["captured_at"],observation_id=observation_id).single()
            if result is None:
                raise ValueError("Declared camera is not present in Neo4j")
    finally:
        driver.close()
    return {"event_id":event_id,"graph_status":"PROJECTED",
            "provenance_status":"OPERATOR_DECLARED_UNVERIFIED",
            "correlation_status":"NOT_RUN","decision_status":"NOT_RUN"}
