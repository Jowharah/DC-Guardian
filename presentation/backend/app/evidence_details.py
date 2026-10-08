"""Persist allowlisted, domain-specific controlled Evidence details separately from incident summaries."""
import json
import sqlite3
from presentation.backend.app.incident_store import _db_path
from presentation.backend.app.authorization import Permission

DOMAIN_PERMISSIONS = {
    "CYBERSECURITY": Permission.SSH_DETAIL,
    "ENVIRONMENTAL": Permission.ENVIRONMENT_DETAIL,
    "MAINTENANCE": Permission.MAINTENANCE_DETAIL,
    "SAFETY": Permission.CAMERA_DETAIL,
    "PHYSICAL_SECURITY": Permission.PERSON_DETAIL,
}
# Explicitly selected data fields. Never serialize arbitrary source payloads.
DETAIL_FIELDS = {
    "CYBERSECURITY": {"behavior": ("failed_login_count","successful_login_count","invalid_user_count","unique_users","root_attempt_ratio","failure_ratio","breakin_warning_count"),
                      "rule": ("prediction","triggered_rules","score"),
                      "isolation_forest": ("prediction","anomaly_score"),
                      "autoencoder": ("prediction","reconstruction_error","threshold")},
    "ENVIRONMENTAL": {"measurements": ("temperature_c","humidity_pct"),
                      "environmental": ("thresholds","high_temperature_threshold_c","low_temperature_threshold_c","high_humidity_threshold_pct","low_humidity_threshold_pct")},
    "MAINTENANCE": {"smart": ("smart_5_raw","smart_198_raw","smart_194_raw","smart_5_delta_7","smart_198_delta_7","temperature_7obs_mean")},
}

def _select(mapping: dict, names: tuple[str, ...]) -> dict:
    return {name: mapping[name] for name in names if name in mapping and isinstance(mapping[name], (str,int,float,bool,list,dict))}

def project_evidence(event: dict) -> dict:
    domain = event["domain"]
    evidence = event.get("evidence") or {}
    details = {}
    for group, names in DETAIL_FIELDS.get(domain, {}).items():
        source = evidence.get(group)
        if isinstance(source, dict):
            details[group] = _select(source, names)
    if domain == "SAFETY":
        details["compliance"] = _select(evidence, ("ppe_status", "person_detected", "person_count", "required_ppe", "required_ppe_not_detected_semantics", "policy_version"))
        details["detector"] = _select(evidence, ("model_family", "architecture", "confidence_threshold", "iou_threshold", "association_method"))
        people = evidence.get("people")
        details["people"] = [_select(p, ("person_index", "status", "required_ppe_detected", "required_ppe_not_detected")) for p in people[:20] if isinstance(p, dict)] if isinstance(people, list) else []
        details["image_available"] = False
        details["image_note"] = "Controlled assessment: no source image was supplied."
    if domain == "PHYSICAL_SECURITY":
        details["recognition"] = _select(evidence, ("recognition_status", "face_detected", "face_count", "distance", "similarity", "threshold", "threshold_source", "detector_backend", "distance_metric", "authorization_evaluated"))
        details["identity"] = _select(evidence, ("person_id", "nearest_employee_id"))
        details["image_available"] = False
        details["image_note"] = "Controlled assessment: no source image was supplied."
    if domain == "MAINTENANCE":
        details["risk"] = _select(evidence, ("failure_probability","operating_threshold","failure_horizon_days","serial_number"))
    if domain == "CYBERSECURITY":
        details["detector_votes"] = evidence.get("detector_votes")
        details["detector_combination"] = evidence.get("detector_combination")
        details["source_ip"] = (event.get("entities") or {}).get("source_ip")
    return {"event_id": event["event_id"], "domain": domain,
            "source_type": (event.get("provenance") or {}).get("source_type"),
            "details": details, "availability": "STRUCTURED_ASSESSMENT_ONLY"}

def store_evidence(scenario_id: str, events: list[dict]) -> None:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path, timeout=10) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS evidence_details (scenario_id TEXT NOT NULL, event_id TEXT NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(scenario_id,event_id))")
        for event in events:
            projection = project_evidence(event)
            conn.execute("INSERT OR REPLACE INTO evidence_details VALUES (?,?,?)",
                         (scenario_id, projection["event_id"], json.dumps(projection)))

def read_evidence(scenario_id: str, event_id: str) -> dict | None:
    path = _db_path()
    if not path.is_file():
        return None
    with sqlite3.connect(path, timeout=10) as conn:
        try:
            row = conn.execute("SELECT payload FROM evidence_details WHERE scenario_id=? AND event_id=?", (scenario_id,event_id)).fetchone()
        except sqlite3.OperationalError:
            return None
    return json.loads(row[0]) if row else None
