"""Read-only Investigator tool gateway for saved, authorized unified investigations.

No model calls, synthetic fixtures, Evidence mutations, or autonomous actions.
All source observations retain their existing provenance and uncertainty.
"""
from fastapi import APIRouter,Depends,HTTPException
from presentation.backend.app.authentication import current_principal
from presentation.backend.app.authorization import Principal
from presentation.backend.app.unified_specialists import find_group,source_evidence,read_specialists
from presentation.backend.app.unified_graph import unified_graph
from presentation.backend.app.unified_decision import read_review_decision
from presentation.backend.app.human_review_audit import list_reviews

router=APIRouter()

@router.get("/api/v1/investigator/unified/{group_id}/context")
def unified_context(group_id:str,principal:Principal=Depends(current_principal)):
    # find_group performs global and zone-specific checks for every domain in
    # the selected unified group before any Evidence is retrieved.
    group=find_group(group_id,principal)
    evidence=source_evidence(group)
    specialists=None
    decision=None
    try:
        specialists=read_specialists(group_id,principal)
    except HTTPException as exc:
        if exc.status_code not in (404,409):raise
    try:
        decision=read_review_decision(group_id,principal)
    except HTTPException as exc:
        if exc.status_code!=409:raise
    reviews=list_reviews(group_id,principal)
    return {"group_id":group_id,"zone_id":group["zone_id"],
            "evidence_refs":group["evidence"],"contextual_links":group["edges"],
            "source_assessments":evidence,
            "saved_specialists":specialists,
            "deterministic_review":decision,
            "human_review_records":reviews["records"],
            "restrictions":{"read_only":True,"severity_assigned":False,
                "identity_to_ssh_established":False,
                "person_to_ppe_verified":False,
                "causation_established":False,
                "autonomous_action_allowed":False},
            "provenance_note":"Saved source assessments and operator-declared controlled context; no new model inference. Historical human reviews do not establish resolution."}

@router.get("/api/v1/investigator/unified/{group_id}/graph")
def unified_graph_context(group_id:str,principal:Principal=Depends(current_principal)):
    return unified_graph(group_id,principal)

@router.get("/api/v1/investigator/operations/{candidate_id}/context")
def operational_context(candidate_id:str,principal:Principal=Depends(current_principal)):
    """Reuse the saved Maintenance+Environmental correlation and Decision.

    No new inference, graph writes, or synthetic Evidence is produced.
    """
    from presentation.backend.app.operational_decision import get_candidate,read_decision
    candidate=get_candidate(candidate_id,principal)
    saved=None
    try:
        saved=read_decision(candidate_id,principal)
    except HTTPException as exc:
        if exc.status_code!=404:raise
    return {
        "candidate_id":candidate_id,
        "zone_id":candidate["zone_id"],
        "maintenance":candidate["maintenance"],
        "environment":candidate["environment"],
        "correlation":{
            "id":candidate["id"],
            "shared_scope":candidate.get("shared_scope"),
            "shared_entity":candidate.get("shared_entity"),
            "time_difference_seconds":candidate.get("time_difference_seconds"),
            "status":candidate.get("status"),
        },
        "saved_specialist":saved["specialist"] if saved else None,
        "saved_decision":saved["decision"] if saved else None,
        "evidence_event_ids":saved["evidence_event_ids"] if saved else [],
        "restrictions":{
            "read_only":True,"causation_established":False,
            "root_cause_established":False,"autonomous_action_allowed":False
        },
        "provenance_note":"Saved model/sensor Evidence and correlation context. Shared zone/time does not establish environmental causation of drive risk."
    }

@router.get("/api/v1/investigator/operations/{candidate_id}/graph")
def operational_graph_context(candidate_id:str,principal:Principal=Depends(current_principal)):
    from presentation.backend.app.operational_correlations import operational_graph
    return operational_graph(candidate_id,principal)
