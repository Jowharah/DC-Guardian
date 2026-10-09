"""Approved sensor CSV -> frozen environmental rules -> Neo4j -> scoped correlation.

Operator-controlled batch, not a live sensor connection. No unsupported severity.
"""
import io
import json
import sqlite3
from datetime import datetime,timezone
from uuid import uuid4
import pandas as pd
from fastapi import APIRouter,Depends,File,Form,HTTPException,UploadFile
from presentation.backend.app.authentication import current_principal,authorize
from presentation.backend.app.authorization import Principal,Permission
from presentation.backend.app.custom_scenarios import topology_options
from presentation.backend.app.incident_store import _db_path
from evidence.environmental_monitoring.src.sensor_monitor import assess_sensor_reading
from reasoning.adapters.environmental_event_adapter import adapt_environmental_assessment
from reasoning.graph.ingest_event import create_driver,ingest_environmental_event
from reasoning.correlation.correlation_engine import find_cross_domain_correlations
from reasoning.topology.topology_mapper import load_topology
router=APIRouter()
MAX_BYTES=1024*1024

def db():
    path=_db_path();path.parent.mkdir(parents=True,exist_ok=True)
    con=sqlite3.connect(path,timeout=15)
    con.execute("""CREATE TABLE IF NOT EXISTS environmental_evidence(
      event_id TEXT PRIMARY KEY,received_at TEXT NOT NULL,zone_id TEXT NOT NULL,
      sensor_id TEXT NOT NULL,assessment_json TEXT NOT NULL,
      history_json TEXT NOT NULL,workflow_json TEXT NOT NULL)""")
    return con

def map_sensor(event_id,assessment,zone):
    event=adapt_environmental_assessment(assessment,dataset_name="Approved operator sensor CSV",
        source_type="CONTROLLED_TEST",event_id=event_id+"-MAPPED")
    event["location"]["zone_id"]=zone
    event["provenance"].update({"original_event_id":event_id,"synthetic_mapping":True,
        "mapping_type":"SYNTHETIC_SCENARIO","scenario_id":"DCG-ENV-"+event_id.removeprefix("ENV-EVT-")})
    return event

def process_sensor_batch(rows,zone,sensor,publish):
    results=[]
    for row in rows:
        result=assess_sensor_reading(sensor_id=sensor,observation_timestamp=row["timestamp"],
            temperature_c=row["temperature_c"],humidity_pct=row["humidity_pct"])
        results.append(result)
    if not publish:
        return {"published":False,"assessments":results,"events":[]}
    events=[]
    # The batch shares one scenario scope, but different uploaded sessions do not.
    scenario="DCG-ENV-BATCH-"+uuid4().hex.upper()
    driver=create_driver()
    try:
        for assessment in results:
            eid="ENV-EVT-"+uuid4().hex.upper()
            mapped=map_sensor(eid,assessment,zone)
            mapped["provenance"]["scenario_id"]=scenario
            ingested=ingest_environmental_event(mapped,driver)
            events.append((eid,assessment,mapped,ingested))
        correlations=find_cross_domain_correlations(driver,scenario_id=scenario,window_minutes=15)
    finally:
        driver.close()
    matched={e["event_id"] for c in correlations for e in c.get("events",[])}
    published=[]
    for eid,assessment,mapped,ingested in events:
        correlated=mapped["event_id"] in matched
        stages=[{"stage":"EVIDENCE","status":"COMPLETE"},
                {"stage":"REASONING","status":"COMPLETE"},
                {"stage":"NEO4J","status":"COMPLETE"},
                {"stage":"CORRELATION","status":"COMPLETE",
                 "detail":"CORRELATED" if correlated else "NO_CORRELATION"},
                {"stage":"RESPONSE","status":"NOT_RUN",
                 "detail":"Multi-domain workflow required" if correlated else "Standalone environmental Response not yet validated"},
                {"stage":"DECISION","status":"NOT_RUN",
                 "detail":"No validated standalone environmental severity rule"}]
        workflow={"stages":stages,"correlation":{"status":"CORRELATED" if correlated else "NO_CORRELATION",
                 "scope":"BATCH_SCENARIO_ONLY"},"decision":None}
        with db() as conn:
            conn.execute("INSERT INTO environmental_evidence VALUES (?,?,?,?,?,?,?)",
                (eid,datetime.now(timezone.utc).isoformat(),zone,sensor,
                 json.dumps(assessment),json.dumps(rows),json.dumps(workflow)))
        published.append({"event_id":eid,"assessment":assessment,"workflow":workflow})
    return {"published":True,"assessments":results,"events":published}

@router.post("/api/v1/environment/validate")
async def validate(file:UploadFile=File(...),zone_id:str=Form(...),sensor_id:str=Form(...),
                   publish:bool=Form(True),principal:Principal=Depends(current_principal)):
    authorize(principal,Permission.INCIDENT_READ,zone_id)
    authorize(principal,Permission.SCENARIO_EXECUTE,zone_id)
    options=next((x for x in topology_options() if x["zone_id"]==zone_id),None)
    if options is None or sensor_id not in options["sensors"]:
        raise HTTPException(422,"Sensor is not in selected zone")
    try: raw=await file.read(MAX_BYTES+1)
    finally: await file.close()
    if not raw or len(raw)>MAX_BYTES or bytes([0]) in raw:
        raise HTTPException(422,"Sensor CSV must be 1 byte to 1 MiB")
    try:
        frame=pd.read_csv(io.BytesIO(raw),nrows=501)
        if not {"timestamp","temperature_c","humidity_pct"}.issubset(frame.columns):
            raise ValueError("Required columns: timestamp,temperature_c,humidity_pct")
        if not 1<=len(frame)<=500: raise ValueError("Expected 1-500 sensor observations")
        frame["timestamp"]=pd.to_datetime(frame["timestamp"],utc=True,errors="raise")
        if frame["timestamp"].isna().any() or frame["timestamp"].duplicated().any():
            raise ValueError("Invalid or duplicate timestamp")
        for col in ("temperature_c","humidity_pct"):
            frame[col]=pd.to_numeric(frame[col],errors="coerce")
        if frame[["temperature_c","humidity_pct"]].isna().all(axis=1).any():
            raise ValueError("Each row requires a measurement")
        rows=[]
        for _,r in frame.sort_values("timestamp").iterrows():
            rows.append({"timestamp":r["timestamp"].isoformat(),
                         "temperature_c":None if pd.isna(r["temperature_c"]) else float(r["temperature_c"]),
                         "humidity_pct":None if pd.isna(r["humidity_pct"]) else float(r["humidity_pct"])})
        # Validate entire batch before any Neo4j writes.
        for row in rows:
            assess_sensor_reading(sensor_id=sensor_id,observation_timestamp=row["timestamp"],
                temperature_c=row["temperature_c"],humidity_pct=row["humidity_pct"])
    except (ValueError,TypeError,OverflowError) as exc:
        raise HTTPException(422,"Invalid environmental CSV: "+str(exc)) from exc
    try:
        result=process_sensor_batch(rows,zone_id,sensor_id,publish)
    except Exception as exc:
        raise HTTPException(503,"Environmental graph or correlation unavailable") from exc
    return {**result,"zone_id":zone_id,"sensor_id":sensor_id}

@router.get("/api/v1/environment/events")
def list_events(principal:Principal=Depends(current_principal)):
    authorize(principal,Permission.INCIDENT_READ)
    with db() as conn:
        records=conn.execute("""SELECT event_id,received_at,zone_id,sensor_id,
          assessment_json,history_json,workflow_json FROM environmental_evidence
          ORDER BY received_at DESC LIMIT 200""").fetchall()
    return [{"event_id":eid,"received_at":received,"zone_id":zone,"sensor_id":sensor,
             "assessment":json.loads(a),"history":json.loads(h),"workflow":json.loads(w),
             "record_type":"ENVIRONMENTAL_EVIDENCE","decision_severity":None}
            for eid,received,zone,sensor,a,h,w in records if zone in principal.zones]
