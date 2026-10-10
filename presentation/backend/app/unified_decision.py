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
    edges = {e["type"] for e in group["edges"]}
    members = group.get("members")
    reasons = []
    if members is None:
        # Membership without verdict annotation: every member counts as unreviewed.
        active_kinds = unreviewed = {r["kind"] for r in group["evidence"]}
    else:
        active = [m for m in members if not m["cleared_by_human"]]
        active_kinds = {m["kind"] for m in active}
        unreviewed = {m["kind"] for m in active
                      if not m["human_review"] or m["human_review"]["verdict"] == "INCONCLUSIVE"}
        if any(m["cleared_by_human"] for m in members):
            reasons.append("HUMAN_CLEARED_MEMBERS_PRESENT")
        if any(m["active_concern"] and m["human_review"]
               and m["human_review"]["verdict"] in ("CONFIRMED", "OVERRIDDEN") for m in active):
            reasons.append("HUMAN_VERIFIED_CONCERNS_PRESENT")
    if "ssh" in active_kinds:
        reasons.append("CYBERSECURITY_EVIDENCE_PRESENT")
    if "ppe" in unreviewed:
        reasons.append("PPE_EVIDENCE_REQUIRES_SOURCE_REVIEW")
    if "face" in unreviewed:
        reasons.append("FACE_IDENTITY_CONTEXT_UNVERIFIED")
    if "face" in active_kinds:
        # A group may hold several face observations; one is enough to flag.
        faces = authorization if isinstance(authorization, list) else [authorization]
        def human_override(face):
            review = face.get("human_review") if isinstance(face, dict) else None
            return review["effective_status"] if review and review.get("source") == "HUMAN_OVERRIDE" else None
        if any(human_override(face) == "UNAUTHORIZED" for face in faces):
            reasons.append("UNAUTHORIZED_BY_HUMAN_VERDICT")
        if any(isinstance(face, dict) and face.get("recognition_status") == "RECOGNIZED"
               and human_override(face) not in ("AUTHORIZED", "NO_FACE")
               and isinstance(face.get("zone_authorization"), dict)
               and face["zone_authorization"].get("status") == "UNAUTHORIZED"
               and face["zone_authorization"].get("source") == "NEO4J_READ_ONLY"
               and face["zone_authorization"].get("reason") == "GRAPH_RELATIONSHIP_CHECK"
               for face in faces):
            reasons.append("RECOGNIZED_IDENTITY_NOT_AUTHORIZED_FOR_DECLARED_ZONE")
    if "maintenance" in unreviewed:
        reasons.append("MAINTENANCE_RISK_REQUIRES_SOURCE_REVIEW")
    if "environment" in unreviewed:
        reasons.append("ENVIRONMENTAL_CONDITION_REQUIRES_SOURCE_REVIEW")
    if any(a["grounding_status"] == "INSUFFICIENT" for a in specialists.values()):
        reasons.append("SPECIALIST_GROUNDING_INSUFFICIENT")
    if "FACE_SSH_CONTEXT" in edges:
        reasons.append("FACE_SSH_CONTEXTUAL_ASSOCIATION_UNVERIFIED")
    # Severity comes only from the group's provisional deterministic policy
    # (unified_severity), never from specialists or standalone Decisions.
    severity = group.get("decision_severity")
    status = ("EVIDENCE_REVIEW_REQUIRED" if reasons
              else "REVIEW_REQUIRED" if severity in ("MEDIUM", "HIGH")
              else "OBSERVATION_RECORDED")
    return {"policy_version": POLICY,
            "status": status,
            "response_mode": "NO_ACTION_ASSIGNED" if status == "OBSERVATION_RECORDED" else "HUMAN_REVIEW",
            "review_reasons": reasons,
            "severity": severity, "severity_policy": group.get("severity_policy"),
            "severity_rule_triggered": bool(group.get("severity_rules_triggered")),
            "decision_v1_severity_evaluated": severity is not None,
            "autonomous_action_allowed": False,
            "identity_to_ssh_established": False,
            "person_to_ppe_verified": False,
            "causal_relationship_established": False,
            "standalone_severity_inherited": False,
            "note": "Provisional evidence disposition; any severity is the group's provisional deterministic policy, not a validated unified Decision."}

def member_verdicts_changed(group, principal):
    """True when a member verdict was recorded after the latest group review."""
    from presentation.backend.app.human_review_audit import list_reviews
    records = list_reviews(group["id"], principal)["records"]
    if not records:
        return False
    last = records[-1]["recorded_at"]
    return any(m["human_review"] and m["human_review"]["recorded_at"] > last
               for m in group.get("members", []))

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
    return {"group_id": group_id, "specialists_evaluated_at": row[0], "decision": decision,
            "member_verdicts_changed_since_review": member_verdicts_changed(group, principal)}
