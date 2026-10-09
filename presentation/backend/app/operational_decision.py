"""Explicit correlated Operations Response and deterministic Decision v1.

Only persisted, independently inferred Evidence may be evaluated. Fail closed
when approved knowledge, provider or response contract is unavailable.
"""
import json
import sqlite3
from datetime import datetime,timezone
from fastapi import APIRouter,Depends,HTTPException
from presentation.backend.app.authentication import current_principal,authorize
from presentation.backend.app.authorization import Principal,Permission
from presentation.backend.app.incident_store import _db_path
from presentation.backend.app.operational_correlations import correlate,maintenance_events,environmental_events
from decision.rules import decide

router=APIRouter()

def storage():
    path=_db_path()
    path.parent.mkdir(parents=True,exist_ok=True)
    conn=sqlite3.connect(path,timeout=15)
    conn.execute("""CREATE TABLE IF NOT EXISTS operational_decisions(
        candidate_id TEXT PRIMARY KEY, evaluated_at TEXT NOT NULL,
        response_json TEXT NOT NULL,decision_json TEXT NOT NULL,
        evidence_ids_json TEXT NOT NULL)""")
    return conn

def eligible(candidate):
    if candidate["status"]!="CORRELATION_CANDIDATE":
        raise ValueError("Validated correlation candidate required")
    m=candidate["maintenance"]
    e=candidate["environment"]
    if m["zone_id"]!=e["zone_id"] or m["assessment"]["assessment"]!="AT_RISK":
        raise ValueError("Invalid operational correlation evidence")
    if candidate["time_difference_seconds"]>900:
        raise ValueError("Observation times exceed approved window")
    if not m["workflow"].get("graph_event_id") or not e.get("evidence_event_ids"):
        raise ValueError("Mapped Neo4j Evidence references required")
    return [m["workflow"]["graph_event_id"]]+[
        eid+"-MAPPED" for eid in e["evidence_event_ids"] if eid.startswith("ENV-EVT-")]

def make_decision(candidate,response):
    ids=eligible(candidate)
    if not ids or response.get("grounding_status") not in (
        "SUPPORTED","PARTIALLY_SUPPORTED","INSUFFICIENT"):
        raise ValueError("Valid grounded Operations assessment required")
    pipeline={"reasoning":{"domains":["MAINTENANCE","ENVIRONMENTAL"],
              "correlation":{"type":"CORRELATED_INFRASTRUCTURE_RISK",
                  "scope":"ZONE","shared_entity_id":candidate["zone_id"]},
              "authorization_status":None},
              "response":{"assessment":{"grounding_status":response["grounding_status"]},
                  "boundary_claims":{"confirmed_compromise":False,
                      "identity_link_established":False,
                      "causal_relationship_established":False,
                      "root_cause_established":False}}}
    result=decide(pipeline)
    if result["autonomous_action_allowed"] is not False or "CORRELATED_OPERATIONAL_RISK" not in result["decision_rules_triggered"]:
        raise ValueError("Unsafe or unexpected Decision contract")
    return result

def get_candidate(candidate_id,principal):
    authorize(principal,Permission.INCIDENT_READ)
    authorize(principal,Permission.MAINTENANCE_DETAIL)
    authorize(principal,Permission.ENVIRONMENT_DETAIL)
    candidate=next((x for x in correlate(maintenance_events(principal),environmental_events(principal))
                    if x["id"]==candidate_id),None)
    if candidate is None:
        raise HTTPException(404,"Operational correlation candidate unavailable")
    authorize(principal,Permission.MAINTENANCE_DETAIL,candidate["zone_id"])
    authorize(principal,Permission.ENVIRONMENT_DETAIL,candidate["zone_id"])
    return candidate

@router.get("/api/v1/operations/correlations/{candidate_id}/decision")
def read_decision(candidate_id:str,principal:Principal=Depends(current_principal)):
    get_candidate(candidate_id,principal)
    with storage() as conn:
        row=conn.execute("SELECT evaluated_at,response_json,decision_json,evidence_ids_json FROM operational_decisions WHERE candidate_id=?",
                         (candidate_id,)).fetchone()
    if row is None:
        raise HTTPException(404,"No completed correlated Decision")
    return {"candidate_id":candidate_id,"evaluated_at":row[0],
            "specialist":json.loads(row[1]),"decision":json.loads(row[2]),
            "evidence_event_ids":json.loads(row[3])}

@router.post("/api/v1/operations/correlations/{candidate_id}/decision")
def evaluate_decision(candidate_id:str,principal:Principal=Depends(current_principal)):
    candidate=get_candidate(candidate_id,principal)
    authorize(principal,Permission.SCENARIO_EXECUTE,candidate["zone_id"])
    try:
        evidence_ids=eligible(candidate)
    except ValueError as exc:
        raise HTTPException(409,"Mapped correlation evidence is incomplete") from exc
    from reasoning.graph.ingest_event import create_driver,NEO4J_DATABASE
    try:
        driver=create_driver()
        try:
            with driver.session(database=NEO4J_DATABASE,default_access_mode="READ") as session:
                rows=session.run("MATCH (e:Event) WHERE e.event_id IN $ids RETURN e.event_id AS id",
                                 ids=evidence_ids)
                observed={row["id"] for row in rows}
        finally:
            driver.close()
    except Exception as exc:
        raise HTTPException(503,"Neo4j evidence verification unavailable") from exc
    if not set(evidence_ids).issubset(observed):
        raise HTTPException(409,"Correlated Evidence nodes missing in Neo4j")
    try:
        from response.agents.providers.openai_provider import OpenAIResponsesProvider
        from response.agents.specialists.operations import OperationsSpecialist
        from response.agents.specialists.base import SpecialistRequest
        from response.rag.knowledge_eligibility import evaluate_knowledge_eligibility
        from response.rag.retrieve import retrieve_knowledge
        if not evaluate_knowledge_eligibility(domains=["MAINTENANCE","ENVIRONMENTAL"])["eligible"]:
            raise ValueError("Approved knowledge not eligible")
        knowledge=retrieve_knowledge(
            "Approved data center environmental temperature and SMART drive maintenance risk guidance",
            domains=["MAINTENANCE","ENVIRONMENTAL"],top_k=4,ranking="controlled",abstain=False)
        if not knowledge:
            raise ValueError("Approved knowledge unavailable")
        specialist=OperationsSpecialist(OpenAIResponsesProvider()).assess(
            SpecialistRequest(
                incident_evidence={
                    "domains":["MAINTENANCE","ENVIRONMENTAL"],
                    "correlation_type":"CORRELATED_INFRASTRUCTURE_RISK",
                    "shared_scope":"ZONE","shared_entity":candidate["zone_id"],
                    "time_difference_seconds":candidate["time_difference_seconds"],
                    "maintenance_assessment":candidate["maintenance"]["assessment"],
                    "environmental_assessment":candidate["environment"]["assessment"],
                    "matched_environment_timestamp":candidate["matched_environment_timestamp"],
                    "evidence_event_ids":evidence_ids,
                    "causal_relationship_established":False,
                    "root_cause_established":False},
                retrieved_evidence=knowledge,
                task="Assess the independently generated, zone-correlated Maintenance and Environmental evidence. Preserve all source values. Do not infer cause, damage, exact failure date, severity, or autonomous action.",
                domains=("MAINTENANCE","ENVIRONMENTAL")))
        decision=make_decision(candidate,specialist)
    except Exception as exc:
        raise HTTPException(503,"Grounded correlated Response or Decision unavailable") from exc
    evaluated=datetime.now(timezone.utc).isoformat()
    with storage() as conn:
        conn.execute("""INSERT INTO operational_decisions VALUES (?,?,?,?,?)
          ON CONFLICT(candidate_id) DO UPDATE SET
          evaluated_at=excluded.evaluated_at,response_json=excluded.response_json,
          decision_json=excluded.decision_json,evidence_ids_json=excluded.evidence_ids_json""",
          (candidate_id,evaluated,json.dumps(specialist),json.dumps(decision),
           json.dumps(evidence_ids)))
    return {"candidate_id":candidate_id,"evaluated_at":evaluated,
            "specialist":specialist,"decision":decision,
            "evidence_event_ids":evidence_ids}
