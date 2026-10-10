"""Pairwise correlation candidates across every Evidence domain combination.

Domain pairs with a dedicated matcher (Maintenance+Environment, PPE+Face,
Face+SSH) keep their stricter contracts. Every other combination uses the
Reasoning-layer contract: both events abnormal, different domains, same
declared zone, original/declared times within 15 minutes. A pair is contextual
only: no identity, causation, presence, or severity is inferred.
"""
import hashlib
import json
from datetime import datetime,timezone
from itertools import combinations
from fastapi import APIRouter,Depends,HTTPException
from presentation.backend.app.authentication import current_principal,authorize
from presentation.backend.app.authorization import Principal,Permission,allowed
from reasoning.correlation.correlation_rules import (ABNORMAL_STATES,
    DEFAULT_CORRELATION_WINDOW_MINUTES)

router=APIRouter()
WINDOW_SECONDS=DEFAULT_CORRELATION_WINDOW_MINUTES*60
DETAIL={"ssh":Permission.SSH_DETAIL,"maintenance":Permission.MAINTENANCE_DETAIL,
        "environment":Permission.ENVIRONMENT_DETAIL,"ppe":Permission.CAMERA_DETAIL,
        "face":Permission.PERSON_DETAIL}
# Combinations owned by dedicated matchers; the generic rule never duplicates them.
SPECIALIZED={frozenset(("maintenance","environment")),frozenset(("ppe","face")),
             frozenset(("face","ssh"))}
GENERIC_TYPE="REASONING_CONTEXT"
EXPLANATIONS={
 "OPERATIONAL":"Independent abnormal maintenance and environmental assessments in the same declared zone within 15 minutes. This does not establish causation, damage, or root cause.",
 "PHYSICAL_IMAGE":"Matching source hash or operator-declared camera and capture time. Camera authenticity, co-presence, and person-to-PPE linkage are not verified.",
 "FACE_SSH_CONTEXT":"Declared zone/time context only. No identity, source-IP, login, or causal linkage is established.",
 GENERIC_TYPE:"Both events are abnormal in the same declared zone within 15 minutes under the Reasoning-layer contract. Contextual relevance only: no causation, identity, presence, or severity is established.",
}

def instant(value):
    """Timezone-aware UTC instant, or None. Naive times are never assumed UTC."""
    if not isinstance(value,str):return None
    try:
        parsed=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError:
        return None
    return parsed.astimezone(timezone.utc) if parsed.tzinfo else None

def node(kind,oid,zone,state,times,provenance,server=None):
    return {"kind":kind,"id":oid,"zone_id":zone,"server_id":server,"state":state,
            "times":[t for t in times if t is not None],"time_provenance":provenance}

def ssh_nodes(principal):
    from presentation.backend.app.ssh_publication import connect
    from presentation.backend.app.ssh_temporal_context import get_context
    with connect() as db:
        rows=db.execute("SELECT event_id,zone_id,server_id,payload FROM ssh_published_evidence").fetchall()
    result=[]
    for sid,zone,server,payload_json in rows:
        if zone not in principal.zones:continue
        payload=json.loads(payload_json)
        declared=get_context(sid)
        if declared and declared.get("provenance")=="OPERATOR_DECLARED_UNVERIFIED_TEST_TIME":
            when,provenance=instant(declared["observed_at"]),declared["provenance"]
        else:
            # Same rule as the Face+SSH matcher: reconstructed legacy OpenSSH
            # years are not trustworthy, and receipt time is never substituted.
            when=instant(payload.get("window_start") or payload.get("observation_timestamp"))
            if payload.get("timestamp_uncertain") or (when and when.year<2020):when=None
            provenance="SOURCE_LOG_UNVERIFIED"
        result.append(node("ssh",sid,zone,payload.get("evidence_state"),[when],provenance,server))
    return result

def maintenance_nodes(principal):
    from presentation.backend.app.maintenance_workflow import list_events
    return [node("maintenance",m["event_id"],m["zone_id"],m["assessment"].get("assessment"),
                 [instant(m["assessment"].get("observation_timestamp"))],
                 "MODEL_OBSERVATION_TIMESTAMP",m.get("server_id"))
            for m in list_events(principal)]

def environment_nodes(principal):
    from presentation.backend.app.environment_workflow import list_events
    result=[]
    for e in list_events(principal):
        history=e.get("history",[])
        states=e.get("workflow",{}).get("reading_states") or []
        times=[];abnormal=[]
        for i,reading in enumerate(history):
            if i<len(states):
                if states[i] not in ABNORMAL_STATES:continue
                abnormal.append(states[i])
            # Legacy batches without per-reading states are only eligible at the
            # explicitly recorded abnormal observation timestamp.
            elif not (e["assessment"].get("anomaly_detected") is True and
                      reading.get("timestamp")==e["assessment"].get("observation_timestamp")):
                continue
            times.append(instant(reading.get("timestamp")))
        state=abnormal[-1] if abnormal else e["assessment"].get("assessment")
        result.append(node("environment",e["event_id"],e["zone_id"],state,times,
                           "SENSOR_READING_TIMESTAMP"))
    return result

def image_nodes(kind,principal):
    from presentation.backend.app.image_metadata_store import connect
    from presentation.backend.app import face_observations,ppe_observations
    with connect() as db:
        rows=db.execute("SELECT observation_id,zone_id,metadata_json,graph_json FROM image_observation_metadata WHERE kind=?",(kind,)).fetchall()
    result=[]
    for oid,zone,metadata_json,graph_json in rows:
        if zone not in principal.zones:continue
        metadata=json.loads(metadata_json)
        if (metadata.get("provenance")!="OPERATOR_DECLARED_UNVERIFIED" or
                json.loads(graph_json).get("graph_status")!="PROJECTED"):continue
        if kind=="ppe":
            record=ppe_observations.get_observation(oid)
            if record is None:continue
            status=record["assessment"].get("overall_status")
            state="PPE_NON_COMPLIANT" if status=="NON_COMPLIANT" else status
        else:
            record=face_observations.get(oid)
            if record is None:continue
            state=face_state(record["assessment"],zone)
        result.append(node(kind,oid,zone,state,[instant(metadata.get("captured_at"))],
                           "OPERATOR_DECLARED_UNVERIFIED"))
    return result

def face_state(assessment,zone):
    """Reasoning physical-security states; graph failure is never UNAUTHORIZED."""
    status=assessment.get("recognition_status")
    if status=="UNKNOWN":return "UNKNOWN_PERSON"
    if status=="RECOGNIZED":
        from presentation.backend.app.face_zone_authorization import assess
        if assess(assessment.get("person_id") or "",zone).get("status")=="UNAUTHORIZED":
            return "UNAUTHORIZED"
    return status

def abnormal(n):
    return n["state"] in ABNORMAL_STATES or n["state"] in ("UNKNOWN_PERSON","UNAUTHORIZED")

def generic_pairs(nodes):
    """Reasoning-contract pairs for combinations without a dedicated matcher."""
    from presentation.backend.app.unified_correlations import edge
    eligible=[n for n in nodes if abnormal(n) and n["times"]]
    result=[]
    for a,b in combinations(sorted(eligible,key=lambda n:(n["kind"],n["id"])),2):
        if a["kind"]==b["kind"] or frozenset((a["kind"],b["kind"])) in SPECIALIZED:continue
        if a["zone_id"]!=b["zone_id"]:continue
        delta=min(abs((x-y).total_seconds()) for x in a["times"] for y in b["times"])
        if delta>WINDOW_SECONDS:continue
        scope="SERVER" if a["server_id"] and a["server_id"]==b["server_id"] else "ZONE"
        digest=hashlib.sha256("|".join((a["zone_id"],a["kind"]+":"+a["id"],b["kind"]+":"+b["id"])).encode()).hexdigest()
        result.append(edge(GENERIC_TYPE,(a["kind"],a["id"]),(b["kind"],b["id"]),
            "DCG-PAIR-"+digest[:20].upper(),a["zone_id"],
            details={"scope":scope,"time_difference_seconds":delta,
                     "left_state":a["state"],"right_state":b["state"],
                     "left_time_provenance":a["time_provenance"],
                     "right_time_provenance":b["time_provenance"]}))
    return result

def generic_edges(principal):
    loaders={"ssh":ssh_nodes,"maintenance":maintenance_nodes,"environment":environment_nodes,
             "ppe":lambda p:image_nodes("ppe",p),"face":lambda p:image_nodes("face",p)}
    # Only domains the operator may inspect contribute nodes.
    nodes=[n for kind,load in loaders.items() if allowed(principal,DETAIL[kind])
           for n in load(principal)]
    return generic_pairs(nodes)

def specialized_edges(principal):
    """Existing matcher output, collected only where the operator holds access."""
    from presentation.backend.app.unified_correlations import edge
    from presentation.backend.app.operational_correlations import operational_correlations
    from presentation.backend.app.physical_image_correlations import image_correlations
    from presentation.backend.app.face_ssh_correlations import face_ssh_candidates
    def can(*kinds):
        return allowed(principal,Permission.INCIDENT_READ) and all(allowed(principal,DETAIL[k]) for k in kinds)
    edges=[]
    if can("maintenance","environment"):
        for c in operational_correlations(principal):
            edges.append(edge("OPERATIONAL",("maintenance",c["maintenance_event_id"]),
                              ("environment",c["environment_event_id"]),c["id"],c["zone_id"],
                              details={"time_difference_seconds":c["time_difference_seconds"]}))
    if can("ppe","face"):
        for c in image_correlations(principal):
            edges.append(edge("PHYSICAL_IMAGE",("ppe",c["ppe_observation_id"]),
                              ("face",c["face_observation_id"]),c["id"],c["zone_id"],
                              details={"source_match":c["source_match"],
                                       "time_difference_seconds":c["time_difference_seconds"]}))
    if can("face","ssh"):
        for c in face_ssh_candidates(principal):
            edges.append(edge("FACE_SSH_CONTEXT",("face",c["face_observation_id"]),
                              ("ssh",c["ssh_event_id"]),c["id"],c["zone_id"],
                              details={"time_difference_seconds":c["time_difference_seconds"]}))
    return edges

def all_edges(principal):
    return specialized_edges(principal)+generic_edges(principal)

def as_pair(e,severities=None):
    from presentation.backend.app.unified_correlations import DOMAIN
    members=[{"kind":k,"domain":DOMAIN[k],"observation_id":oid} for k,oid in (e["left"],e["right"])]
    return {"id":e["source_id"],"type":e["type"],"zone_id":e["zone_id"],"members":members,
            "domains":sorted({m["domain"] for m in members}),"details":e["details"],
            "status":"CORRELATION_CANDIDATE",
            # Only the operational matcher has its own saved deterministic Decision;
            # it is reported here, never written into unified group edges.
            "decision_severity":(severities or {}).get(e["source_id"]) if e["type"]=="OPERATIONAL" else None,
            "autonomous_action_allowed":False,"identity_link_established":False,
            "causal_relationship_established":False,"explanation":EXPLANATIONS[e["type"]]}

@router.get("/api/v1/correlations/pairs")
def correlation_pairs(principal:Principal=Depends(current_principal)):
    authorize(principal,Permission.INCIDENT_READ)
    severities={}
    if allowed(principal,DETAIL["maintenance"]) and allowed(principal,DETAIL["environment"]):
        from presentation.backend.app.operational_correlations import operational_correlations
        severities={c["id"]:c.get("decision_severity") for c in operational_correlations(principal)}
    pairs=[]
    for e in all_edges(principal):
        if all(allowed(principal,DETAIL[k],e["zone_id"]) for k,_ in (e["left"],e["right"])):
            pairs.append(as_pair(e,severities))
    return sorted(pairs,key=lambda p:(p["zone_id"],p["details"].get("time_difference_seconds",0),p["id"]))

def find_pair(pair_id,principal):
    pair=next((p for p in correlation_pairs(principal) if p["id"]==pair_id),None)
    if pair is None:raise HTTPException(404,"Correlation pair not found")
    for m in pair["members"]:
        authorize(principal,DETAIL[m["kind"]],pair["zone_id"])
    return pair
