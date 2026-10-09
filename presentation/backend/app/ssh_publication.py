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

@router.post("/api/v1/ssh/published/{event_id}/run-pipeline")
def run_pipeline(event_id: str, principal: Principal = Depends(current_principal)):
    """Advance genuine SSH evidence through adapter and topology verification.

    Do not run the synthetic three-domain scenario or manufacture other evidence.
    Response and Decision are explicitly blocked until a compatible pipeline exists.
    """
    authorize(principal, Permission.SSH_DETAIL)
    with connect() as conn:
        row = conn.execute("SELECT zone_id,server_id,payload FROM ssh_published_evidence WHERE event_id=?",
                           (event_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Published SSH evidence not found")
    zone, server, encoded = row
    authorize(principal, Permission.SSH_DETAIL, zone)
    authorize(principal, Permission.SCENARIO_EXECUTE, zone)
    from reasoning.adapters.ssh_event_adapter import adapt_ssh_assessment
    from reasoning.topology.topology_mapper import load_topology, build_server_index
    assessment = json.loads(encoded)
    try:
        normalized = adapt_ssh_assessment(assessment, dataset_name="Operator uploaded OpenSSH log",
                                          source_type="CONTROLLED_TEST", event_id=event_id)
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(422, "SSH evidence is incompatible with Reasoning adapter; validate and republish") from exc
    index = build_server_index(load_topology())
    target = index.get(server)
    if not target or target["zone_id"] != zone:
        raise HTTPException(422, "Selected server/zone is absent from controlled topology")
    # Topology metadata is a controlled operator assignment, not a claim about
    # the real SSH hostname or source IP's physical location.
    stages = [
        {"stage":"EVIDENCE","status":"COMPLETE","detail":"Frozen SSH detector assessment published"},
        {"stage":"REASONING_ADAPTER","status":"COMPLETE","detail":"Common Event schema adapter succeeded"},
        {"stage":"TOPOLOGY","status":"COMPLETE","detail":"Selected server and zone verified in controlled topology"},
    ]
    from reasoning.graph.ingest_event import create_driver, NEO4J_DATABASE
    try:
        driver=create_driver()
        try:
            with driver.session(database=NEO4J_DATABASE,default_access_mode="READ") as session:
                record=session.run("MATCH (s:Server {server_id:$server}) RETURN s.server_id AS id LIMIT 1",
                                   server=server).single()
        finally:
            driver.close()
        graph_ok=record is not None
        stages.append({"stage":"NEO4J","status":"COMPLETE" if graph_ok else "UNAVAILABLE",
                       "detail":"Server node verified read-only" if graph_ok else "Server node not found"})
    except Exception:
        graph_ok=False
        stages.append({"stage":"NEO4J","status":"UNAVAILABLE","detail":"Read-only graph verification unavailable"})
    stages.extend([
        {"stage":"CORRELATION","status":"NOT_RUN","detail":"No validated standalone SSH correlation runner"},
        {"stage":"RESPONSE","status":"NOT_RUN","detail":"No grounded standalone SSH Response contract"},
        {"stage":"DECISION","status":"NOT_RUN","detail":"No standalone SSH Decision result or severity"},
    ])
    return {"event_id":event_id,"source_ip":normalized["entities"]["source_ip"],
            "original_timestamp":normalized["timestamp"],"server_id":server,"zone_id":zone,
            "stages":stages,"completed_full_pipeline":False,"decision_severity":None,
            "note":"Actual model evidence; no synthetic environmental or maintenance events inserted."}

@router.post("/api/v1/ssh/published/{event_id}/ingest-graph")
def ingest_graph(event_id: str, principal: Principal = Depends(current_principal)):
    """Explicitly persist genuine SSH detector evidence in the controlled graph."""
    authorize(principal, Permission.SSH_DETAIL)
    with connect() as conn:
        row = conn.execute("SELECT zone_id,server_id,payload FROM ssh_published_evidence WHERE event_id=?",
                           (event_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Published SSH evidence not found")
    zone, server, encoded = row
    authorize(principal, Permission.SSH_DETAIL, zone)
    authorize(principal, Permission.SCENARIO_EXECUTE, zone)
    from presentation.backend.app.ssh_graph_ingestion import ingest_published_ssh
    try:
        ingested = ingest_published_ssh(event_id, json.loads(encoded), server, zone)
    except ValueError as exc:
        raise HTTPException(422, "SSH mapping or event contract validation failed") from exc
    except Exception as exc:
        raise HTTPException(503, "Neo4j SSH ingestion unavailable") from exc
    return {"status":"INGESTED","graph_event_id":ingested["event_id"],
            "scenario_id":ingested["scenario_id"],"source_ip":ingested["source_ip"],
            "server_id":server,"zone_id":zone,
            "original_timestamp":ingested["original_timestamp"],
            "correlation_performed":False,"response_performed":False,
            "decision_performed":False,"decision_severity":None}

@router.post("/api/v1/ssh/published/{event_id}/check-correlation")
def check_correlation(event_id: str, principal: Principal = Depends(current_principal)):
    authorize(principal, Permission.SSH_DETAIL)
    with connect() as conn:
        row = conn.execute("SELECT zone_id,server_id,payload FROM ssh_published_evidence WHERE event_id=?",
                           (event_id,)).fetchone()
    if row is None:
        raise HTTPException(404,"Published SSH evidence not found")
    zone,server,encoded=row
    authorize(principal, Permission.SSH_DETAIL, zone)
    authorize(principal, Permission.SCENARIO_EXECUTE, zone)
    from presentation.backend.app.ssh_graph_ingestion import prepare_mapped_ssh
    from presentation.backend.app.ssh_correlation import check_ssh_correlations
    mapped=prepare_mapped_ssh(event_id,json.loads(encoded),server,zone)
    from reasoning.graph.ingest_event import create_driver,NEO4J_DATABASE
    try:
        driver=create_driver()
        try:
            with driver.session(database=NEO4J_DATABASE,default_access_mode="READ") as session:
                record=session.run("MATCH (e:Event {event_id:$id}) RETURN e.event_id AS id LIMIT 1",
                                   id=mapped["event_id"]).single()
        finally:
            driver.close()
        if record is None:
            raise HTTPException(409,"Ingest this SSH evidence into Neo4j first")
        return check_ssh_correlations(mapped["provenance"]["scenario_id"],mapped["event_id"])
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(503,"Correlation service unavailable") from exc

@router.post("/api/v1/ssh/published/{event_id}/specialist-response")
def specialist_response(event_id: str, principal: Principal = Depends(current_principal)):
    authorize(principal, Permission.SSH_DETAIL)
    with connect() as conn:
        row=conn.execute("SELECT zone_id,server_id,payload FROM ssh_published_evidence WHERE event_id=?",
                         (event_id,)).fetchone()
    if row is None:
        raise HTTPException(404,"Published SSH evidence not found")
    zone,server,encoded=row
    authorize(principal, Permission.SSH_DETAIL, zone)
    authorize(principal, Permission.SCENARIO_EXECUTE, zone)
    from presentation.backend.app.ssh_graph_ingestion import prepare_mapped_ssh
    from presentation.backend.app.ssh_response import assess_standalone_ssh
    assessment=json.loads(encoded)
    mapped=prepare_mapped_ssh(event_id,assessment,server,zone)
    from reasoning.graph.ingest_event import create_driver,NEO4J_DATABASE
    try:
        driver=create_driver()
        try:
            with driver.session(database=NEO4J_DATABASE,default_access_mode="READ") as session:
                found=session.run("MATCH (e:Event {event_id:$id}) RETURN e.event_id AS id",
                                  id=mapped["event_id"]).single()
        finally:
            driver.close()
        if found is None:
            raise HTTPException(409,"Ingest SSH Evidence into Neo4j first")
        from presentation.backend.app.ssh_correlation import check_ssh_correlations
        correlation=check_ssh_correlations(mapped["provenance"]["scenario_id"],mapped["event_id"])
        if correlation["status"]!="NO_CORRELATION":
            raise HTTPException(409,"Correlated events require validated multi-domain Response workflow")
        return assess_standalone_ssh(event_id,assessment,zone,server)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(503,"Cybersecurity specialist unavailable") from exc

@router.post("/api/v1/ssh/published/{event_id}/decision")
def standalone_decision(event_id: str, principal: Principal = Depends(current_principal)):
    """Execute validated SSH-only Reasoning/Response/Decision; no synthetic companions."""
    authorize(principal, Permission.SSH_DETAIL)
    with connect() as conn:
        row=conn.execute("SELECT zone_id,server_id,payload FROM ssh_published_evidence WHERE event_id=?",
                         (event_id,)).fetchone()
    if row is None:
        raise HTTPException(404,"Published SSH evidence not found")
    zone,server,encoded=row
    authorize(principal, Permission.SSH_DETAIL, zone)
    authorize(principal, Permission.SCENARIO_EXECUTE, zone)
    from presentation.backend.app.ssh_graph_ingestion import prepare_mapped_ssh
    from presentation.backend.app.ssh_correlation import check_ssh_correlations
    from presentation.backend.app.ssh_response import assess_standalone_ssh
    from presentation.backend.app.ssh_decision import decide_standalone_ssh
    assessment=json.loads(encoded)
    try:
        mapped=prepare_mapped_ssh(event_id,assessment,server,zone)
    except (ValueError,KeyError,TypeError) as exc:
        raise HTTPException(422,"Invalid SSH Reasoning contract") from exc
    from reasoning.graph.ingest_event import create_driver,NEO4J_DATABASE
    try:
        driver=create_driver()
        try:
            with driver.session(database=NEO4J_DATABASE,default_access_mode="READ") as session:
                found=session.run("MATCH (e:Event {event_id:$id}) RETURN e.event_id AS id",
                                  id=mapped["event_id"]).single()
        finally:
            driver.close()
        if found is None:
            raise HTTPException(409,"Ingest SSH Evidence into Neo4j first")
        correlation=check_ssh_correlations(mapped["provenance"]["scenario_id"],mapped["event_id"])
        if correlation["status"]!="NO_CORRELATION":
            raise HTTPException(409,"Correlated evidence requires multi-domain Decision workflow")
        specialist=assess_standalone_ssh(event_id,assessment,zone,server)
        decision=decide_standalone_ssh(assessment,correlation,specialist)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(422,"Standalone Decision contract invalid") from exc
    except Exception as exc:
        raise HTTPException(503,"Standalone Decision dependencies unavailable") from exc
    return {"event_id":event_id,"zone_id":zone,"server_id":server,
            "source_ip":assessment["source_ip"],"evidence_state":assessment["evidence_state"],
            "correlation":correlation,"specialist":specialist,"decision":decision,
            "record_type":"STANDALONE_SSH_DECISION",
            "incident_linked":False,"decision_source":"DCG-DECISION-v1",
            "note":"SSH-only human-review Decision; no cross-domain incident inferred."}
