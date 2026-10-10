"""Unified cross-domain correlation groups from existing validated candidate contracts.

A unified group is any connected set of three or more correlated events; two
events form a pair (see correlation_pairs). Read-only orchestration: no
inferred edges, severity, causal or identity claims. Edges come from the
dedicated matchers and the Reasoning-contract pair rule.
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

MIN_GROUP_MEMBERS=3

def group_edges(edges,min_members=MIN_GROUP_MEMBERS):
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
            if len(members)<min_members:continue
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

def collect_existing(principal,nodes=None):
    """Reuse published candidate contracts; never invent eligibility rules."""
    from presentation.backend.app.correlation_pairs import all_edges
    # Human-cleared members stay in their group, marked; see annotate().
    return all_edges(principal,include_cleared=True,nodes=nodes)

def annotate(groups,principal,nodes=None):
    """Member verdicts, concern flags and provisional severity per group.

    Group ID and fingerprint depend only on membership and links, so verdicts
    never invalidate saved specialists or review history. A group with fewer
    than two members left un-cleared is no longer a correlation candidate.
    """
    from presentation.backend.app.correlation_pairs import member_states
    from presentation.backend.app.evidence_review import overrides,summary
    from presentation.backend.app.unified_severity import members_with_review,group_severity
    states=member_states(principal,nodes)
    human=overrides()
    result=[]
    for group in groups:
        summaries={(r["kind"],r["observation_id"]):summary(r["kind"],r["observation_id"]) for r in group["evidence"]}
        members=members_with_review(group,states,human,summaries)
        if sum(not m["cleared_by_human"] for m in members)<2:continue
        severity=group_severity(members)
        result.append({**group,"members":members,
            "decision_severity":severity["severity"],"severity_policy":severity["policy"],
            "severity_rules_triggered":severity["rules_triggered"],
            "active_concern_domains":severity["active_concern_domains"],
            "severity_provisional":True})
    return result

@router.get("/api/v1/correlations/unified")
def unified_correlations(principal:Principal=Depends(current_principal)):
    # V1 requires full cross-domain visibility, not a partially redacted group.
    for permission in (Permission.INCIDENT_READ,Permission.MAINTENANCE_DETAIL,
                       Permission.ENVIRONMENT_DETAIL,Permission.CAMERA_DETAIL,
                       Permission.PERSON_DETAIL,Permission.SSH_DETAIL):
        authorize(principal,permission)
    from presentation.backend.app.correlation_pairs import load_nodes
    from presentation.backend.app.evidence_review import overrides
    nodes=load_nodes(principal,overrides())
    groups=group_edges(collect_existing(principal,nodes))
    result=[]
    for group in groups:
        zone=group["zone_id"]
        for permission in (Permission.INCIDENT_READ,Permission.MAINTENANCE_DETAIL,
                           Permission.ENVIRONMENT_DETAIL,Permission.CAMERA_DETAIL,
                           Permission.PERSON_DETAIL,Permission.SSH_DETAIL):
            authorize(principal,permission,zone)
        result.append(group)
    return annotate(result,principal,nodes)
