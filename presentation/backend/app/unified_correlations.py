"""Unified cross-domain correlation groups from existing validated candidate contracts.

V1 is a read-only orchestration layer: no inferred edges, severity, causal or
identity claims. Edges are sourced from the existing domain-specific matchers.
"""
from collections import defaultdict
from fastapi import APIRouter,Depends
from presentation.backend.app.authentication import current_principal,authorize
from presentation.backend.app.authorization import Principal,Permission

router=APIRouter()
DOMAIN={"maintenance":"MAINTENANCE","environment":"ENVIRONMENTAL",
        "ppe":"SAFETY","face":"PHYSICAL_SECURITY","ssh":"CYBERSECURITY"}

def edge(kind,left,right,source,zone,*,details=None):
    if left[0] not in DOMAIN or right[0] not in DOMAIN:
        raise ValueError("Unknown Evidence domain")
    if not all(isinstance(x,str) and x for x in (left[1],right[1],zone,source)):
        raise ValueError("Missing correlation Evidence reference")
    if left==right:raise ValueError("Self-link prohibited")
    return {"type":kind,"left":left,"right":right,"source_id":source,
            "zone_id":zone,"details":details or {}}

def group_edges(edges):
    """Connected Evidence components, scoped to one zone.

    Edges remain explicit. Transitive group membership does NOT imply a direct
    association between every pair or a causal relationship.
    """
    by_zone=defaultdict(list)
    for e in edges:
        if e["left"]==e["right"] or e["left"][0] not in DOMAIN or e["right"][0] not in DOMAIN:
            raise ValueError("Invalid correlation edge")
        by_zone[e["zone_id"]].append(e)
    groups=[]
    for zone,zone_edges in sorted(by_zone.items()):
        adjacency=defaultdict(set)
        for e in zone_edges:
            a=tuple(e["left"]);b=tuple(e["right"])
            adjacency[a].add(b);adjacency[b].add(a)
        visited=set()
        for first in sorted(adjacency):
            if first in visited:continue
            pending=[first];members=set()
            while pending:
                node=pending.pop()
                if node in members:continue
                members.add(node);pending.extend(adjacency[node]-members)
            visited.update(members)
            relevant=sorted(
                (e for e in zone_edges if tuple(e["left"]) in members and tuple(e["right"]) in members),
                key=lambda e:(e["type"],e["source_id"],tuple(e["left"]),tuple(e["right"]))
            )
            if len(members)<2:continue
            refs=[{"kind":kind,"domain":DOMAIN[kind],"observation_id":oid} for kind,oid in sorted(members)]
            source_ids=sorted({e["source_id"] for e in relevant})
            # Deterministic across restarts and input ordering; no new Evidence.
            import hashlib
            fingerprint="|".join([zone]+[kind+":"+oid for kind,oid in sorted(members)])
            group_id="DCG-UNIFIED-"+hashlib.sha256(fingerprint.encode()).hexdigest()[:20].upper()
            groups.append({"id":group_id,"zone_id":zone,"evidence":refs,
                "domains":sorted({r["domain"] for r in refs}),
                "edges":relevant,"source_candidate_ids":source_ids,
                "status":"CORRELATION_GROUP_CANDIDATE","decision":None,
                "decision_severity":None,"autonomous_action_allowed":False,
                "identity_link_established":False,"causal_relationship_established":False,
                "note":"Grouping reflects only listed source correlations. Shared group membership does not establish pairwise identity, causation, or compromise."})
    return sorted(groups,key=lambda g:(g["zone_id"],g["id"]))

def collect_existing(principal):
    """Reuse published candidate decisions; never invent eligibility rules."""
    from presentation.backend.app.operational_correlations import operational_correlations
    from presentation.backend.app.physical_image_correlations import image_correlations
    from presentation.backend.app.face_ssh_correlations import face_ssh_candidates
    edges=[]
    for c in operational_correlations(principal):
        edges.append(edge("OPERATIONAL",("maintenance",c["maintenance_event_id"]),
                          ("environment",c["environment_event_id"]),c["id"],c["zone_id"],
                          details={"time_difference_seconds":c["time_difference_seconds"]}))
    for c in image_correlations(principal):
        edges.append(edge("PHYSICAL_IMAGE",("ppe",c["ppe_observation_id"]),
                          ("face",c["face_observation_id"]),c["id"],c["zone_id"],
                          details={"source_match":c["source_match"],
                                   "time_difference_seconds":c["time_difference_seconds"]}))
    for c in face_ssh_candidates(principal):
        edges.append(edge("FACE_SSH_CONTEXT",("face",c["face_observation_id"]),
                          ("ssh",c["ssh_event_id"]),c["id"],c["zone_id"],
                          details={"time_difference_seconds":c["time_difference_seconds"]}))
    return edges

@router.get("/api/v1/correlations/unified")
def unified_correlations(principal:Principal=Depends(current_principal)):
    # V1 requires full cross-domain visibility, not a partially redacted group.
    for permission in (Permission.INCIDENT_READ,Permission.MAINTENANCE_DETAIL,
                       Permission.ENVIRONMENT_DETAIL,Permission.CAMERA_DETAIL,
                       Permission.PERSON_DETAIL,Permission.SSH_DETAIL):
        authorize(principal,permission)
    groups=group_edges(collect_existing(principal))
    result=[]
    for group in groups:
        zone=group["zone_id"]
        for permission in (Permission.INCIDENT_READ,Permission.MAINTENANCE_DETAIL,
                           Permission.ENVIRONMENT_DETAIL,Permission.CAMERA_DETAIL,
                           Permission.PERSON_DETAIL,Permission.SSH_DETAIL):
            authorize(principal,permission,zone)
        result.append(group)
    return result
