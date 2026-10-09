"""Explicit read-only physical-security Response, never an implicit Decision."""
import json
import sqlite3
from datetime import datetime,timezone
from fastapi import APIRouter,Depends,HTTPException
from presentation.backend.app.authentication import current_principal,authorize
from presentation.backend.app.authorization import Principal,Permission
from presentation.backend.app.incident_store import _db_path
from presentation.backend.app.physical_image_correlations import image_correlations
from presentation.backend.app import face_observations,ppe_observations

router=APIRouter()

def storage():
    path=_db_path()
    path.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(path,timeout=15)
    db.execute("""CREATE TABLE IF NOT EXISTS physical_specialist_results(
        candidate_id TEXT PRIMARY KEY, evaluated_at TEXT NOT NULL,
        response_json TEXT NOT NULL, evidence_ids_json TEXT NOT NULL)""")
    return db

def candidate_for(candidate_id,principal):
    for permission in (Permission.CAMERA_DETAIL,Permission.PERSON_DETAIL):
        authorize(principal,permission)
    item=next((c for c in image_correlations(principal) if c["id"]==candidate_id),None)
    if item is None:raise HTTPException(404,"Physical candidate not found")
    for permission in (Permission.CAMERA_DETAIL,Permission.PERSON_DETAIL):
        authorize(principal,permission,item["zone_id"])
    return item

@router.get("/api/v1/physical/image-correlations/{candidate_id}/specialist")
def read_specialist(candidate_id:str,principal:Principal=Depends(current_principal)):
    candidate_for(candidate_id,principal)
    with storage() as db:
        row=db.execute("SELECT evaluated_at,response_json,evidence_ids_json FROM physical_specialist_results WHERE candidate_id=?",(candidate_id,)).fetchone()
    if row is None:raise HTTPException(404,"No saved Physical Security Specialist assessment")
    return {"evaluated_at":row[0],"specialist":json.loads(row[1]),
            "evidence_event_ids":json.loads(row[2]),"decision":None}

@router.post("/api/v1/physical/image-correlations/{candidate_id}/specialist")
def evaluate_specialist(candidate_id:str,principal:Principal=Depends(current_principal)):
    item=candidate_for(candidate_id,principal)
    authorize(principal,Permission.SCENARIO_EXECUTE,item["zone_id"])
    ids=["IMG-EVT-"+item["ppe_observation_id"],"IMG-EVT-"+item["face_observation_id"]]
    from reasoning.graph.ingest_event import create_driver,NEO4J_DATABASE
    try:
        driver=create_driver()
        try:
            with driver.session(database=NEO4J_DATABASE,default_access_mode="READ") as session:
                found={r["id"] for r in session.run("MATCH (e:Event) WHERE e.event_id IN $ids RETURN e.event_id AS id",ids=ids)}
        finally:driver.close()
    except Exception as exc:
        raise HTTPException(503,"Neo4j Evidence verification unavailable") from exc
    if not set(ids).issubset(found):
        raise HTTPException(409,"Both source Evidence events must exist")
    p=ppe_observations.get_observation(item["ppe_observation_id"])
    f=face_observations.get(item["face_observation_id"])
    if p is None or f is None:raise HTTPException(409,"Original image observations unavailable")
    try:
        from response.rag.knowledge_eligibility import evaluate_knowledge_eligibility
        from response.rag.retrieve import retrieve_knowledge
        from response.agents.providers.openai_provider import OpenAIResponsesProvider
        from response.agents.specialists.base import SpecialistRequest
        from response.agents.specialists.physical_security import PhysicalSecuritySpecialist
        domains=["PHYSICAL_SECURITY","SAFETY"]
        if not evaluate_knowledge_eligibility(domains=domains)["eligible"]:
            raise ValueError("No approved physical security knowledge")
        knowledge=retrieve_knowledge("Data center personnel safety PPE helmet vest access control and identity assessment",domains=domains,top_k=4,ranking="controlled",abstain=False)
        if not knowledge:raise ValueError("No approved retrieved knowledge")
        assessment=PhysicalSecuritySpecialist(OpenAIResponsesProvider()).assess(SpecialistRequest(
            incident_evidence={"domains":domains,"zone_id":item["zone_id"],
                "declared_camera_id":item["camera_id"],
                "capture_time":item["captured_at"],
                "source_match":item["source_match"],
                "camera_provenance":"OPERATOR_DECLARED_UNVERIFIED",
                "ppe_assessment":{"overall_status":p["assessment"]["overall_status"],
                                  "people":p["assessment"].get("people",[]),
                                  "required_ppe":p["assessment"].get("required_ppe",[])},
                "face_assessment":{"recognition_status":f["assessment"]["recognition_status"],
                                   "person_id":f["assessment"].get("person_id"),
                                   "similarity":f["assessment"].get("similarity")},
                "zone_authorization_status":"NOT_ESTABLISHED_BY_THIS_CORRELATION",
                "person_to_ppe_identity_link_established":False,
                "evidence_event_ids":ids},
            retrieved_evidence=knowledge,
            task="Provide supported findings, review considerations, limitations and approved citations without deciding severity.",
            domains=tuple(domains)))
        if assessment.get("grounding_status") not in ("SUPPORTED","PARTIALLY_SUPPORTED","INSUFFICIENT"):
            raise ValueError("Invalid grounded Response")
    except Exception as exc:
        raise HTTPException(503,"Grounded Physical Security Specialist unavailable") from exc
    evaluated=datetime.now(timezone.utc).isoformat()
    with storage() as db:
        db.execute("""INSERT INTO physical_specialist_results VALUES (?,?,?,?)
          ON CONFLICT(candidate_id) DO UPDATE SET evaluated_at=excluded.evaluated_at,
          response_json=excluded.response_json,evidence_ids_json=excluded.evidence_ids_json""",
          (candidate_id,evaluated,json.dumps(assessment),json.dumps(ids)))
    return {"evaluated_at":evaluated,"specialist":assessment,
            "evidence_event_ids":ids,"decision":None}
