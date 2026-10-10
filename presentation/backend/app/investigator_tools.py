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

SINGLE_KINDS={"ssh","ppe","face","maintenance","environment"}

@router.get("/api/v1/investigator/evidence/{kind}/{evidence_id}/context")
def single_evidence_context(kind:str,evidence_id:str,principal:Principal=Depends(current_principal)):
    """Reuse existing authorized Evidence feeds; never infer correlation."""
    from presentation.backend.app.authentication import authorize
    from presentation.backend.app.authorization import Permission
    from presentation.backend.app import ssh_publication,ppe_image_validation,face_image_validation
    from presentation.backend.app import maintenance_workflow,environment_workflow
    if kind not in SINGLE_KINDS:raise HTTPException(404,"Unsupported Evidence domain")
    permissions={"ssh":Permission.SSH_DETAIL,"ppe":Permission.CAMERA_DETAIL,
                 "face":Permission.PERSON_DETAIL,"maintenance":Permission.MAINTENANCE_DETAIL,
                 "environment":Permission.ENVIRONMENT_DETAIL}
    authorize(principal,permissions[kind])
    if kind=="ssh":
        record=next((r for r in ssh_publication.published(principal) if r["event_id"]==evidence_id),None)
    elif kind=="ppe":
        record=ppe_image_validation.ppe_observation_detail(evidence_id,principal)
    elif kind=="face":
        record=face_image_validation.face_detail(evidence_id,principal)
    elif kind=="maintenance":
        record=next((r for r in maintenance_workflow.list_events(principal) if r["event_id"]==evidence_id),None)
    else:
        record=next((r for r in environment_workflow.list_events(principal) if r["event_id"]==evidence_id),None)
    if record is None:raise HTTPException(404,"Authorized Evidence not found")
    zone=record.get("zone_id")
    if not zone:raise HTTPException(409,"Evidence zone unavailable")
    authorize(principal,permissions[kind],zone)
    # Domain-specific allowlists: never return raw images, enrollment, full
    # history, or arbitrary original source payloads to the LLM.
    allowed={
      "ssh":("event_id","zone_id","server_id","source_ip","evidence_state","detector_votes","usernames","window_start","evidence"),
      "ppe":("observation_id","zone_id","assessment","capture_metadata"),
      "face":("observation_id","zone_id","assessment","capture_metadata"),
      "maintenance":("event_id","zone_id","server_id","assessment"),
      "environment":("event_id","zone_id","sensor_id","assessment"),
    }[kind]
    selected={key:record[key] for key in allowed if key in record}
    return {"kind":kind,"evidence_id":evidence_id,"zone_id":zone,
            "source_assessment":selected,
            "correlation_status":"NOT_ASSESSED_BY_SINGLE_EVIDENCE_TOOL",
            "restrictions":{"read_only":True,"identity_link_established":False,
                            "causation_established":False,"autonomous_action_allowed":False},
            "provenance_note":"Individual saved detector Evidence. No correlation or Decision severity inferred."}
