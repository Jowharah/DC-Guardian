"""Provisional deterministic unified Evidence disposition.

No cross-domain severity rule has been validated under DCG-DECISION-v1.
This policy never inherits standalone severity or treats contextual links as
proof of identity, causation, or compromise.
"""
import json
from fastapi import APIRouter, Depends, HTTPException
from presentation.backend.app.authentication import current_principal
from presentation.backend.app.authorization import Principal
from presentation.backend.app.unified_specialists import find_group, fingerprint, storage

router = APIRouter()
POLICY = "DCG-UNIFIED-EVIDENCE-REVIEW-v1"
GROUNDING = frozenset({"SUPPORTED", "PARTIALLY_SUPPORTED", "INSUFFICIENT"})

def evaluate(group, specialists, authorization=None):
    if not specialists:
        raise ValueError("Saved grounded specialists required")
    if any(a.get("grounding_status") not in GROUNDING for a in specialists.values()):
        raise ValueError("Invalid specialist grounding")
    kinds = {r["kind"] for r in group["evidence"]}
    edges = {e["type"] for e in group["edges"]}
    reasons = []
    if "ssh" in kinds:
        reasons.append("CYBERSECURITY_EVIDENCE_PRESENT")
    if "ppe" in kinds:
        reasons.append("PPE_EVIDENCE_REQUIRES_SOURCE_REVIEW")
    if "face" in kinds:
        reasons.append("FACE_IDENTITY_CONTEXT_UNVERIFIED")
        # A group may hold several face observations; one is enough to flag.
        faces = authorization if isinstance(authorization, list) else [authorization]
        if any(isinstance(face, dict) and face.get("recognition_status") == "RECOGNIZED"
               and isinstance(face.get("zone_authorization"), dict)
               and face["zone_authorization"].get("status") == "UNAUTHORIZED"
               and face["zone_authorization"].get("source") == "NEO4J_READ_ONLY"
               and face["zone_authorization"].get("reason") == "GRAPH_RELATIONSHIP_CHECK"
               for face in faces):
            reasons.append("RECOGNIZED_IDENTITY_NOT_AUTHORIZED_FOR_DECLARED_ZONE")
    if any(a["grounding_status"] == "INSUFFICIENT" for a in specialists.values()):
        reasons.append("SPECIALIST_GROUNDING_INSUFFICIENT")
    if "maintenance" in kinds:
        reasons.append("MAINTENANCE_RISK_REQUIRES_SOURCE_REVIEW")
    if "environment" in kinds:
        reasons.append("ENVIRONMENTAL_CONDITION_REQUIRES_SOURCE_REVIEW")
    if "FACE_SSH_CONTEXT" in edges:
        reasons.append("FACE_SSH_CONTEXTUAL_ASSOCIATION_UNVERIFIED")
    return {"policy_version": POLICY,
            "status": "EVIDENCE_REVIEW_REQUIRED" if reasons else "OBSERVATION_RECORDED",
            "response_mode": "HUMAN_REVIEW" if reasons else "NO_ACTION_ASSIGNED",
            "review_reasons": reasons,
            "severity": None, "severity_rule_triggered": False,
            "decision_v1_severity_evaluated": False,
            "autonomous_action_allowed": False,
            "identity_to_ssh_established": False,
            "person_to_ppe_verified": False,
            "causal_relationship_established": False,
            "standalone_severity_inherited": False,
            "note": "Provisional evidence disposition only; not a validated unified severity Decision."}

@router.get("/api/v1/correlations/unified/{group_id}/review-decision")
def read_review_decision(group_id: str, principal: Principal = Depends(current_principal)):
    group = find_group(group_id, principal)
    with storage() as db:
        row = db.execute("SELECT evaluated_at,signature,response_json FROM unified_specialist_results WHERE group_id=?", (group_id,)).fetchone()
    if row is None:
        raise HTTPException(409, "Evaluate unified specialists first")
    if row[1] != fingerprint(group):
        raise HTTPException(409, "Source correlations changed; re-evaluate specialists")
    try:
        authorization = None
        if any(ref["kind"] == "face" for ref in group["evidence"]):
            from presentation.backend.app.unified_specialists import source_evidence
            authorization = source_evidence(group).get("face")
        decision = evaluate(group, json.loads(row[2]), authorization)
    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(409, "Invalid saved specialist evidence") from exc
    return {"group_id": group_id, "specialists_evaluated_at": row[0], "decision": decision}
