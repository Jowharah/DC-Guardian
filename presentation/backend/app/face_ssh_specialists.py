"""Grounded Face + SSH specialist assessment for contextual candidates."""
import json
from datetime import datetime,timezone
from fastapi import APIRouter,Depends,HTTPException
from presentation.backend.app.authentication import current_principal,authorize
from presentation.backend.app.authorization import Principal,Permission
from presentation.backend.app.face_ssh_correlations import face_ssh_candidates
from presentation.backend.app.unified_specialists import run_agents,storage
from presentation.backend.app import face_observations
from presentation.backend.app.face_zone_authorization import assess as assess_zone
from presentation.backend.app.ssh_publication import connect as ssh_connect

router=APIRouter()

def candidate(cid,principal):
    for perm in (Permission.INCIDENT_READ,Permission.PERSON_DETAIL,Permission.SSH_DETAIL):
        authorize(principal,perm)
    item=next((x for x in face_ssh_candidates(principal) if x["id"]==cid),None)
    if item is None:raise HTTPException(404,"Face SSH candidate not found")
    for perm in (Permission.PERSON_DETAIL,Permission.SSH_DETAIL):
        authorize(principal,perm,item["zone_id"])
    return item

@router.post("/api/v1/cyber/face-ssh/candidates/{candidate_id}/specialists")
def evaluate(candidate_id:str,principal:Principal=Depends(current_principal)):
    item=candidate(candidate_id,principal)
    authorize(principal,Permission.SCENARIO_EXECUTE,item["zone_id"])
    face=face_observations.get(item["face_observation_id"])
    if face is None:raise HTTPException(409,"Face evidence unavailable")
    with ssh_connect() as db:
        row=db.execute("SELECT payload FROM ssh_published_evidence WHERE event_id=?",
                       (item["ssh_event_id"],)).fetchone()
    if row is None:raise HTTPException(409,"SSH evidence unavailable")
    assessment=face["assessment"]
    ssh=json.loads(row[0])
    evidence={
        "face":{"recognition_status":assessment.get("recognition_status"),
                "person_id":assessment.get("person_id"),
                "similarity":assessment.get("similarity"),
                "zone_authorization":assess_zone(
                    assessment.get("person_id") if assessment.get("recognition_status")=="RECOGNIZED" else "",
                    item["zone_id"])},
        "ssh":{k:ssh.get(k) for k in ("evidence_state","source_ip","window_start",
                                     "detector_votes","usernames","evidence")}}
    group={"zone_id":item["zone_id"],"edges":[{"type":"FACE_SSH_CONTEXT","source_id":item["id"]}]}
    try:
        specialists=run_agents(group,evidence)
    except HTTPException:raise
    except Exception as exc:
        raise HTTPException(503,"Grounded specialist assessment unavailable") from exc
    authorization=evidence["face"]["zone_authorization"]
    reasons=["SSH_ANOMALY_REVIEW"]
    if authorization["status"]=="UNAUTHORIZED":
        reasons.append("RECOGNIZED_IDENTITY_NOT_AUTHORIZED_FOR_DECLARED_ZONE")
    if any(v["grounding_status"]=="INSUFFICIENT" for v in specialists.values()):
        reasons.append("SPECIALIST_GROUNDING_INSUFFICIENT")
    return {"candidate_id":candidate_id,"evaluated_at":datetime.now(timezone.utc).isoformat(),
            "specialists":specialists,"authorization":authorization,
            "review":{"status":"EVIDENCE_REVIEW_REQUIRED","response_mode":"HUMAN_REVIEW",
                      "reasons":reasons,"severity":None,"identity_to_ssh_established":False,
                      "physical_presence_verified":False,"autonomous_action_allowed":False}}
