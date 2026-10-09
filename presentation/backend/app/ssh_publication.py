"""Publish server-validated SSH assessments, never client-supplied model claims."""
import json
import sqlite3
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from presentation.backend.app.incident_store import _db_path
from presentation.backend.app.authentication import current_principal, authorize
from presentation.backend.app.authorization import Principal, Permission

router = APIRouter()
TTL = timedelta(hours=1)

def connect():
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.execute("""CREATE TABLE IF NOT EXISTS ssh_validation_previews (
        preview_id TEXT PRIMARY KEY, created_at TEXT NOT NULL,
        owner TEXT NOT NULL, zone_id TEXT NOT NULL, server_id TEXT NOT NULL,
        assessments TEXT NOT NULL)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS ssh_published_evidence (
        event_id TEXT PRIMARY KEY, preview_id TEXT NOT NULL,
        assessment_index INTEGER NOT NULL, received_at TEXT NOT NULL,
        zone_id TEXT NOT NULL, server_id TEXT NOT NULL, payload TEXT NOT NULL,
        UNIQUE(preview_id,assessment_index))""")
    return conn

def save_preview(owner, zone, server, assessments):
    preview_id = "SSH-PREVIEW-" + uuid4().hex.upper()
    with connect() as conn:
        conn.execute("INSERT INTO ssh_validation_previews VALUES (?,?,?,?,?,?)",
                     (preview_id,datetime.now(timezone.utc).isoformat(),owner,zone,server,
                      json.dumps(assessments,allow_nan=False)))
    return preview_id

class PublishRequest(BaseModel):
    preview_id: str = Field(pattern=r"^SSH-PREVIEW-[A-F0-9]{32}$")
    indices: list[int] = Field(min_length=1,max_length=100)

@router.post("/api/v1/ssh/publish")
def publish(payload: PublishRequest, principal: Principal = Depends(current_principal)):
    authorize(principal, Permission.SSH_DETAIL)
    authorize(principal, Permission.SCENARIO_EXECUTE)
    if len(payload.indices)!=len(set(payload.indices)):
        raise HTTPException(422,"Duplicate assessment indices")
    with connect() as conn:
        row = conn.execute("SELECT created_at,owner,zone_id,server_id,assessments FROM ssh_validation_previews WHERE preview_id=?",
                           (payload.preview_id,)).fetchone()
        if row is None:
            raise HTTPException(404,"Validation preview not found")
        created,owner,zone,server,encoded = row
        authorize(principal, Permission.SSH_DETAIL, zone)
        authorize(principal, Permission.SCENARIO_EXECUTE, zone)
        if owner!=principal.subject:
            raise HTTPException(403,"Only the validating operator can publish")
        if datetime.now(timezone.utc)-datetime.fromisoformat(created)>TTL:
            raise HTTPException(410,"Validation preview expired; validate again")
        assessments=json.loads(encoded)
        if any(i<0 or i>=len(assessments) for i in payload.indices):
            raise HTTPException(422,"Assessment index out of range")
        ids=[]
        for i in payload.indices:
            assessment=assessments[i]
            if assessment.get("evidence_state")=="NO_ANOMALY_EVIDENCE":
                raise HTTPException(422,"Only security-relevant assessments can be published")
            event_id="SSH-EVT-"+uuid4().hex.upper()
            timestamp=datetime.now(timezone.utc).isoformat()
            cursor=conn.execute("""INSERT OR IGNORE INTO ssh_published_evidence
                VALUES (?,?,?,?,?,?,?)""",
                (event_id,payload.preview_id,i,timestamp,zone,server,
                 json.dumps(assessment,allow_nan=False)))
            if cursor.rowcount:
                ids.append(event_id)
            else:
                existing=conn.execute("SELECT event_id FROM ssh_published_evidence WHERE preview_id=? AND assessment_index=?",
                                      (payload.preview_id,i)).fetchone()
                ids.append(existing[0])
    return {"published_event_ids":ids}

@router.get("/api/v1/ssh/published")
def published(principal: Principal = Depends(current_principal)):
    authorize(principal, Permission.SSH_DETAIL)
    with connect() as conn:
        rows=conn.execute("""SELECT event_id,received_at,zone_id,server_id,payload
                             FROM ssh_published_evidence ORDER BY received_at DESC LIMIT 200""").fetchall()
    return [{**json.loads(payload),"event_id":eid,"received_at":received,
             "zone_id":zone,"server_id":server,"record_type":"SSH_DETECTOR_EVIDENCE",
             "source_type":"OPERATOR_UPLOADED_OPENSSH_LOG","decision_severity":None}
            for eid,received,zone,server,payload in rows if zone in principal.zones]

@router.get("/api/v1/ssh/published/{event_id}/reasoning-preview")
def reasoning_preview(event_id: str, principal: Principal = Depends(current_principal)):
    """Validate the actual published detector result against the Common Event adapter.

    Read-only: no Neo4j writes, correlation, Response or Decision claims.
    """
    authorize(principal, Permission.SSH_DETAIL)
    with connect() as conn:
        row = conn.execute("SELECT zone_id,server_id,payload FROM ssh_published_evidence WHERE event_id=?",
                           (event_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Published SSH evidence not found")
    zone,server,encoded = row
    authorize(principal, Permission.SSH_DETAIL, zone)
    from reasoning.adapters.ssh_event_adapter import adapt_ssh_assessment
    assessment = json.loads(encoded)
    try:
        normalized = adapt_ssh_assessment(
            assessment, dataset_name="Operator uploaded OpenSSH log",
            source_type="CONTROLLED_TEST", event_id=event_id)
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(422, "Published evidence lacks required Reasoning contract fields; validate and publish again") from exc
    return {"event_id":event_id, "status":"COMMON_EVENT_VALIDATED",
            "pipeline_stage":"REASONING_ADAPTER_ONLY",
            "zone_id":zone, "server_id":server,
            "original_timestamp":normalized["timestamp"],
            "source_ip":normalized["entities"]["source_ip"],
            "evidence_state":normalized["assessment"]["state"],
            "topology_mapping_performed":False,
            "correlation_performed":False, "response_performed":False,
            "decision_performed":False}
