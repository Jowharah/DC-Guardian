"""Read-only Face + SSH candidate discovery.

Shared declared zone and close original observation times establish contextual
relevance only. They never link a recognized face to an SSH source IP or user.
"""
import json
from datetime import datetime,timezone
from fastapi import APIRouter,Depends
from presentation.backend.app.authentication import current_principal,authorize
from presentation.backend.app.authorization import Principal,Permission
from presentation.backend.app.image_metadata_store import connect as metadata_connect
from presentation.backend.app.ssh_publication import connect as ssh_connect
from presentation.backend.app import face_observations

router=APIRouter()
WINDOW_SECONDS=900

def parse_timestamp(value):
    if not isinstance(value,str):return None
    try:
        dt=datetime.fromisoformat(value.replace("Z","+00:00"))
        return dt.astimezone(timezone.utc) if dt.tzinfo else None
    except ValueError:
        return None

def eligible(face,ssh):
    if face["zone_id"]!=ssh["zone_id"]:return None
    if face.get("provenance")!="OPERATOR_DECLARED_UNVERIFIED":return None
    ft=parse_timestamp(face.get("captured_at"))
    st=parse_timestamp(ssh.get("original_timestamp"))
    if ft is None or st is None:return None
    # Legacy OpenSSH year reconstruction is not trustworthy for real-time
    # matching; do not substitute ingestion/received time.
    if ssh.get("timestamp_uncertain") or st.year<2020:return None
    delta=abs((ft-st).total_seconds())
    return delta if delta<=WINDOW_SECONDS else None

@router.get("/api/v1/cyber/face-ssh/candidates")
def face_ssh_candidates(principal:Principal=Depends(current_principal)):
    for permission in (Permission.INCIDENT_READ,Permission.PERSON_DETAIL,Permission.SSH_DETAIL):
        authorize(principal,permission)
    with metadata_connect() as db:
        face_rows=db.execute("SELECT observation_id,zone_id,metadata_json,graph_json FROM image_observation_metadata WHERE kind='face'").fetchall()
    with ssh_connect() as db:
        ssh_rows=db.execute("SELECT event_id,zone_id,server_id,received_at,payload FROM ssh_published_evidence").fetchall()
    result=[]
    for fid,zone,metadata_json,graph_json in face_rows:
        if zone not in principal.zones:continue
        for permission in (Permission.PERSON_DETAIL,Permission.SSH_DETAIL):
            authorize(principal,permission,zone)
        metadata=json.loads(metadata_json)
        graph=json.loads(graph_json)
        if graph.get("graph_status")!="PROJECTED":continue
        face=face_observations.get(fid)
        if face is None:continue
        face_context={"zone_id":zone,"captured_at":metadata.get("captured_at"),
                      "provenance":metadata.get("provenance")}
        for sid,ssh_zone,server,received,payload_json in ssh_rows:
            if ssh_zone!=zone:continue
            payload=json.loads(payload_json)
            if payload.get("evidence_state")=="NO_ANOMALY_EVIDENCE":continue
            # SSH detector timestamps are historical in many sample logs.
            timestamp=payload.get("window_start") or payload.get("observation_timestamp")
            ssh_context={"zone_id":ssh_zone,"original_timestamp":timestamp,
                         "timestamp_uncertain":payload.get("timestamp_uncertain",False)}
            delta=eligible(face_context,ssh_context)
            if delta is None:continue
            result.append({"id":"DCG-FACE-SSH-"+fid+"-"+sid,"zone_id":zone,
                "face_observation_id":fid,"ssh_event_id":sid,
                "camera_id":metadata["camera_id"],"server_id":server,
                "face_capture_time":metadata["captured_at"],
                "ssh_original_time":timestamp,"time_difference_seconds":delta,
                "face_recognition_status":face["assessment"]["recognition_status"],
                "ssh_evidence_state":payload.get("evidence_state"),
                "status":"CONTROLLED_CANDIDATE","decision_severity":None,
                "explanation":"Same declared zone and nearby original timestamps. No identity, source-IP, login, or causal linkage is established."})
    return sorted(result,key=lambda x:(x["time_difference_seconds"],x["id"]))[:100]
