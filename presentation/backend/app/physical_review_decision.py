"""Deterministic physical evidence-review disposition, without severity.

This is not a new severity rule in DCG-DECISION-v1. A source PPE state
must never be attributed to a recognized employee from a geometric candidate.
"""
from datetime import datetime,timezone
from fastapi import APIRouter,Depends,HTTPException
from presentation.backend.app.authentication import current_principal,authorize
from presentation.backend.app.authorization import Principal,Permission
from presentation.backend.app.physical_specialist import candidate_for,storage
from presentation.backend.app import ppe_observations,face_observations
import json

router=APIRouter()

def assess_review(ppe,face,grounding,ppe_verdict=None):
    if grounding not in ("SUPPORTED","PARTIALLY_SUPPORTED","INSUFFICIENT"):
        raise ValueError("Saved grounded specialist assessment required")
    if ppe.get("overall_status") not in ("COMPLIANT","NON_COMPLIANT","NO_PERSON"):
        raise ValueError("Unknown frozen PPE status")
    if face.get("recognition_status") not in ("RECOGNIZED","UNKNOWN","NO_FACE","MULTIPLE_FACES"):
        raise ValueError("Unknown frozen Face status")
    reasons=[]
    # A human override replaces the detector PPE status for this disposition;
    # the frozen detector output itself is unchanged.
    overridden=bool(ppe_verdict and ppe_verdict.get("source")=="HUMAN_OVERRIDE")
    ppe_status=ppe_verdict["effective_status"] if overridden else ppe["overall_status"]
    if ppe_status=="NON_COMPLIANT":
        reasons.append("PPE_NON_COMPLIANT_HUMAN_VERDICT" if overridden else "PPE_NON_COMPLIANT_DETECTOR_ASSESSMENT")
    if face["recognition_status"]!="RECOGNIZED":
        reasons.append("FACE_RECOGNITION_NOT_ESTABLISHED")
    if grounding=="INSUFFICIENT":
        reasons.append("SPECIALIST_GROUNDING_INSUFFICIENT")
    return {"policy_version":"DCG-PHYSICAL-REVIEW-PROVISIONAL-v1",
            "status":"EVIDENCE_REVIEW_REQUIRED" if reasons else "OBSERVATION_RECORDED",
            "severity":None,"response_mode":"HUMAN_REVIEW" if reasons else "NO_ACTION_ASSIGNED",
            "autonomous_action_allowed":False,"reasons":reasons,
            "identity_link_established":False,"confirmed_ppe_violation":False,
            "ppe_status_used":ppe_status,"ppe_status_source":"HUMAN_OVERRIDE" if overridden else "DETECTOR",
            "decision_v1_severity_evaluated":False}

@router.get("/api/v1/physical/image-correlations/{candidate_id}/review-decision")
def review_decision(candidate_id:str,principal:Principal=Depends(current_principal)):
    item=candidate_for(candidate_id,principal)
    authorize(principal,Permission.INCIDENT_READ,item["zone_id"])
    with storage() as db:
        row=db.execute("SELECT evaluated_at,response_json FROM physical_specialist_results WHERE candidate_id=?",(candidate_id,)).fetchone()
    if row is None:
        raise HTTPException(409,"Run grounded Physical Security Specialist first")
    p=ppe_observations.get_observation(item["ppe_observation_id"])
    f=face_observations.get(item["face_observation_id"])
    if not p or not f:
        raise HTTPException(409,"Source observations unavailable")
    try:
        from presentation.backend.app.evidence_review import summary
        result=assess_review(p["assessment"],f["assessment"],json.loads(row[1])["grounding_status"],
                             summary("ppe",item["ppe_observation_id"]))
    except (ValueError,KeyError,TypeError) as exc:
        raise HTTPException(409,"Source or specialist contract invalid") from exc
    return {"candidate_id":candidate_id,"specialist_evaluated_at":row[0],"decision":result}
