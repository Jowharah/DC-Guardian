"""Conservative synthesis of saved, grounded specialist assessments.

Does not call a model, assign severity, or infer new pairwise links.
"""
import json
from fastapi import APIRouter, Depends, HTTPException
from presentation.backend.app.authentication import current_principal
from presentation.backend.app.authorization import Principal
from presentation.backend.app.unified_specialists import find_group, fingerprint, storage

router = APIRouter()

def synthesize(group, specialists):
    if not specialists:
        raise ValueError("At least one specialist is required")
    supported = []
    limitations = []
    citations = []
    grounding = []
    for name, result in sorted(specialists.items()):
        status = result.get("grounding_status")
        if status not in ("SUPPORTED", "PARTIALLY_SUPPORTED", "INSUFFICIENT"):
            raise ValueError("Invalid grounding status")
        grounding.append(status)
        if status != "INSUFFICIENT":
            supported.extend({"specialist": name, "finding": finding}
                             for finding in result.get("supported_findings", [])
                             if isinstance(finding, str) and finding.strip())
        limitations.extend({"specialist": name, "limitation": value}
                           for value in result.get("limitations", [])
                           if isinstance(value, str) and value.strip())
        citations.extend(result.get("citations", []))
    status = ("INSUFFICIENT" if all(x == "INSUFFICIENT" for x in grounding)
              else "SUPPORTED" if all(x == "SUPPORTED" for x in grounding)
              else "PARTIALLY_SUPPORTED")
    return {
        "grounding_status": status,
        "contributing_specialists": sorted(specialists),
        "supported_source_findings": supported,
        "source_limitations": limitations,
        "approved_citations": citations,
        "validated_contextual_links": [
            {"type": e["type"], "source_id": e["source_id"]}
            for e in group["edges"]
        ],
        "identity_to_ssh_established": False,
        "identity_to_ppe_verified": False,
        "causal_relationship_established": False,
        "decision_severity": None,
        "decision_status": "NOT_RUN",
        "autonomous_action_allowed": False,
        "assessment": ("The contributing specialist assessments are presented as "
                       "independent source findings. The listed contextual links do not "
                       "establish SSH actor identity, a verified person-to-PPE association, "
                       "causation, or a unified Decision severity."),
    }

@router.get("/api/v1/correlations/unified/{group_id}/synthesis")
def read_synthesis(group_id: str, principal: Principal = Depends(current_principal)):
    group = find_group(group_id, principal)
    with storage() as db:
        row = db.execute(
            "SELECT evaluated_at,signature,response_json FROM unified_specialist_results WHERE group_id=?",
            (group_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Run unified specialists first")
    if row[1] != fingerprint(group):
        raise HTTPException(409, "Source correlation changed; re-evaluate specialists")
    results = json.loads(row[2])
    try:
        synthesis = synthesize(group, results)
    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(409, "Saved specialist contract invalid") from exc
    return {"group_id": group_id, "specialists_evaluated_at": row[0],
            "synthesis": synthesis}
