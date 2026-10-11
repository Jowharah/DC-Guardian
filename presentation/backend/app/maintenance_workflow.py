"""End-to-end operator-approved SMART history workflow using frozen RF v2.

No hardcoded model outputs, no fabricated correlated incidents, and no invented
Decision severity for standalone maintenance (Decision v1 has no such rule).
"""
import io
import json
import sqlite3
from datetime import datetime, timezone
from uuid import uuid4
import pandas as pd
from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException
from presentation.backend.app.authentication import current_principal, authorize
from presentation.backend.app.authorization import Principal, Permission
from presentation.backend.app.incident_store import _db_path
from presentation.backend.app.custom_scenarios import topology_options
from evidence.predictive_maintenance.src.config import BASE_SMART_FEATURES
from evidence.predictive_maintenance.src.maintenance_detector import assess_drive_health
from reasoning.adapters.maintenance_event_adapter import adapt_maintenance_assessment
from reasoning.topology.topology_mapper import load_topology, build_server_index
from reasoning.graph.ingest_event import create_driver, ingest_maintenance_event
from reasoning.correlation.correlation_engine import find_cross_domain_correlations

router=APIRouter()
MAX_BYTES=4*1024*1024

def db():
    path=_db_path()
    path.parent.mkdir(parents=True,exist_ok=True)
    con=sqlite3.connect(path,timeout=15)
    con.execute("""CREATE TABLE IF NOT EXISTS maintenance_evidence(
        event_id TEXT PRIMARY KEY, received_at TEXT NOT NULL,
        zone_id TEXT NOT NULL, server_id TEXT NOT NULL,
        assessment_json TEXT NOT NULL, history_json TEXT NOT NULL,
        workflow_json TEXT NOT NULL, created_by TEXT NOT NULL)""")
    return con

def mapped_event(event_id, assessment, server, zone):
    target=build_server_index(load_topology()).get(server)
    if target is None or target["zone_id"]!=zone:
        raise ValueError("Invalid server/zone topology mapping")
    event=adapt_maintenance_assessment(assessment,dataset_name="Operator SMART history",
        source_type="CONTROLLED_TEST",event_id=event_id+"-MAPPED")
    observed=event["timestamp"]
    dt=datetime.fromisoformat(observed.replace("Z","+00:00"))
    if dt.tzinfo is None:
        dt=dt.replace(tzinfo=timezone.utc) # explicit controlled UTC convention
    timestamp=dt.isoformat()
    event["timestamp"]=timestamp
    event["window"]={"start":timestamp,"end":timestamp}
    event["entities"]["server_id"]=server
    event["location"].update({"data_center_id":target["data_center_id"],
                              "rack_id":target["rack_id"],"zone_id":zone})
    event["provenance"].update({"original_event_id":event_id,
        "original_timestamp":timestamp,"synthetic_mapping":True,
        "mapping_type":"SYNTHETIC_SCENARIO",
        "scenario_id":"DCG-MAINT-"+event_id.removeprefix("MAINT-EVT-")})
    return event

def run_workflow(event_id, assessment, server, zone):
    event=mapped_event(event_id,assessment,server,zone)
    stages=[{"stage":"EVIDENCE","status":"COMPLETE","detail":"Frozen Temporal RF v2 inference"},
            {"stage":"REASONING","status":"COMPLETE","detail":"Common Event adapter and controlled topology"}]
    driver=create_driver()
    try:
        graph=ingest_maintenance_event(event,driver)
        stages.append({"stage":"NEO4J","status":"COMPLETE","detail":"Drive asset, server and Event ingested"})
        correlations=find_cross_domain_correlations(driver,
            scenario_id=event["provenance"]["scenario_id"],window_minutes=15)
    finally:
        driver.close()
    matches=[c for c in correlations if any(e.get("event_id")==event["event_id"]
              for e in c.get("events",[]))]
    correlation={"status":"CORRELATED" if matches else "NO_CORRELATION",
                 "count":len(matches),"scope":"SCENARIO_ONLY"}
    stages.append({"stage":"CORRELATION","status":"COMPLETE",
                   "detail":correlation["status"]})
    # No fabricated Response when retrieval/provider is unavailable.
    response=None
    if assessment["assessment"]=="AT_RISK" and not matches:
        try:
            from response.agents.providers.openai_provider import OpenAIResponsesProvider
            from response.agents.specialists.operations import OperationsSpecialist
            from response.agents.specialists.base import SpecialistRequest
            from response.rag.knowledge_eligibility import evaluate_knowledge_eligibility
            from response.rag.retrieve import retrieve_knowledge
            if not evaluate_knowledge_eligibility(domains=["MAINTENANCE"])["eligible"]:
                raise RuntimeError("No eligible maintenance knowledge")
            knowledge=retrieve_knowledge("Approved drive SMART failure risk assessment and maintenance guidance",
                domains=["MAINTENANCE"],top_k=3,ranking="controlled",abstain=False)
            if not knowledge:
                raise RuntimeError("No approved maintenance knowledge retrieved")
            response=OperationsSpecialist(OpenAIResponsesProvider()).assess(
                SpecialistRequest(incident_evidence={"event_id":event_id,
                    "domains":["MAINTENANCE"],"maintenance_assessment":assessment,
                    "server_id":server,"zone_id":zone,
                    "correlation_status":"NO_CORRELATION",
                    "causal_relationship_established":False,"root_cause_established":False},
                    retrieved_evidence=knowledge,
                    task="Analyze standalone frozen SMART risk without predicting exact failure, assigning severity, or inferring cause.",
                    domains=("MAINTENANCE",)))
            stages.append({"stage":"RESPONSE","status":"COMPLETE","detail":"Grounded Operations Specialist"})
        except Exception:
            stages.append({"stage":"RESPONSE","status":"UNAVAILABLE",
                           "detail":"Approved knowledge or Response provider unavailable"})
    else:
        stages.append({"stage":"RESPONSE","status":"NOT_RUN",
                       "detail":"Normal assessment or multi-domain Response contract required"})
    stages.append({"stage":"DECISION","status":"NOT_RUN",
                   "detail":"Decision v1 has no validated standalone maintenance severity rule"})
    return {"stages":stages,"correlation":correlation,"specialist":response,
            "decision":None,"graph_event_id":graph["event_id"]}

@router.post("/api/v1/maintenance/validate",status_code=200)
async def validate(
    file:UploadFile=File(...),zone_id:str=Form(...),server_id:str=Form(...),
    publish:bool=Form(False),principal:Principal=Depends(current_principal)):
    authorize(principal,Permission.INCIDENT_READ,zone_id)
    authorize(principal,Permission.SCENARIO_EXECUTE,zone_id)
    options=next((z for z in topology_options() if z["zone_id"]==zone_id),None)
    if options is None or server_id not in options["servers"]:
        raise HTTPException(422,"Invalid zone/server")
    try:
        raw=await file.read(MAX_BYTES+1)
    finally:
        await file.close()
    if not raw or len(raw)>MAX_BYTES or bytes([0]) in raw:
        raise HTTPException(422,"CSV must be 1 byte to 4 MiB, text only")
    try:
        history=pd.read_csv(io.BytesIO(raw),nrows=10001)
        required={"date","serial_number",*BASE_SMART_FEATURES}
        if not required.issubset(history.columns) or len(history)<8 or len(history)>10000:
            raise ValueError("Requires 8-10000 rows and date, serial_number and eight SMART columns")
        if history["serial_number"].nunique(dropna=True)!=1:
            raise ValueError("CSV must contain one drive serial_number")
        if history["date"].isna().any() or history.duplicated(["date"]).any():
            raise ValueError("Dates must be present and unique")
        history["date"]=pd.to_datetime(history["date"],errors="raise",utc=True)
        if history["date"].isna().any():
            raise ValueError("Invalid date")
        for key in BASE_SMART_FEATURES:
            history[key]=pd.to_numeric(history[key],errors="raise")
            if not history[key].map(lambda v: pd.notna(v) and float("-inf")<v<float("inf") and v>=0).all():
                raise ValueError("SMART measurements must be finite and nonnegative")
        assessment=assess_drive_health(history)
    except (ValueError,TypeError,KeyError,OverflowError) as exc:
        raise HTTPException(422,"Invalid SMART history or feature contract") from exc
    event_id="MAINT-EVT-"+uuid4().hex.upper()
    history_view=history.sort_values("date")[["date",*BASE_SMART_FEATURES]].copy()
    history_view["date"]=history_view["date"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    measurements=history_view.to_dict(orient="records")
    workflow=None
    if publish:
        try:
            workflow=run_workflow(event_id,assessment,server_id,zone_id)
        except Exception as exc:
            raise HTTPException(503,"Maintenance graph/pipeline unavailable; nothing published") from exc
        with db() as conn:
            conn.execute("INSERT INTO maintenance_evidence VALUES (?,?,?,?,?,?,?,?)",
                (event_id,datetime.now(timezone.utc).isoformat(),zone_id,server_id,
                 json.dumps(assessment,allow_nan=False),json.dumps(measurements,allow_nan=False),
                 json.dumps(workflow,allow_nan=False),principal.subject))
    return {"event_id":event_id,"assessment":assessment,"history":measurements,
            "workflow":workflow,"published":publish,"zone_id":zone_id,"server_id":server_id,
            "decision_severity":None}

@router.get("/api/v1/maintenance/events")
def list_events(principal:Principal=Depends(current_principal)):
    authorize(principal,Permission.INCIDENT_READ)
    with db() as conn:
        rows=conn.execute("""SELECT event_id,received_at,zone_id,server_id,assessment_json,
            history_json,workflow_json FROM maintenance_evidence ORDER BY received_at DESC LIMIT 200""").fetchall()
    return [{"event_id":eid,"received_at":received,"zone_id":zone,"server_id":server,
             "assessment":json.loads(a),"history":json.loads(h),"workflow":json.loads(w),
             "record_type":"MAINTENANCE_EVIDENCE","decision_severity":None}
            for eid,received,zone,server,a,h,w in rows if zone in principal.zones]
