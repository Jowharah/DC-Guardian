"""Controlled same-source image pairing, no inferred camera authenticity or Decision."""
from datetime import datetime,timezone
from fastapi import APIRouter,Depends
from presentation.backend.app.authentication import current_principal,authorize
from presentation.backend.app.authorization import Principal,Permission
from presentation.backend.app.image_source_hashes import pairs
from presentation.backend.app.image_metadata_store import get
from presentation.backend.app import face_observations,ppe_observations

router=APIRouter()

def parse_time(value):
    dt=datetime.fromisoformat(value.replace("Z","+00:00"))
    if dt.tzinfo is None:raise ValueError("Timezone required")
    return dt.astimezone(timezone.utc)

def eligible_pair(ppe,face,ppe_meta,face_meta):
    if not ppe_meta or not face_meta:return False
    p=ppe_meta["capture_metadata"];f=face_meta["capture_metadata"]
    if p["provenance"]!="OPERATOR_DECLARED_UNVERIFIED" or f["provenance"]!="OPERATOR_DECLARED_UNVERIFIED":
        return False
    if p["camera_id"]!=f["camera_id"] or p["zone_id"]!=f["zone_id"]:
        return False
    if abs((parse_time(p["captured_at"])-parse_time(f["captured_at"])).total_seconds())>900:
        return False
    if ppe_meta["graph_projection"]["graph_status"]!="PROJECTED" or face_meta["graph_projection"]["graph_status"]!="PROJECTED":
        return False
    return True

@router.get("/api/v1/physical/image-correlations")
def image_correlations(principal:Principal=Depends(current_principal)):
    authorize(principal,Permission.CAMERA_DETAIL)
    authorize(principal,Permission.PERSON_DETAIL)
    result=[]
    for zone,sha,pid,fid in pairs(principal.zones):
        authorize(principal,Permission.CAMERA_DETAIL,zone)
        authorize(principal,Permission.PERSON_DETAIL,zone)
        p=ppe_observations.get_observation(pid)
        f=face_observations.get(fid)
        if p is None or f is None:continue
        pm=get("ppe",pid,zone);fm=get("face",fid,zone)
        if not eligible_pair(p,f,pm,fm):continue
        result.append({"id":"DCG-PHYSICAL-"+pid+"-"+fid,"zone_id":zone,
          "ppe_observation_id":pid,"face_observation_id":fid,
          "camera_id":pm["capture_metadata"]["camera_id"],
          "captured_at":pm["capture_metadata"]["captured_at"],
          "ppe_status":p["assessment"]["overall_status"],
          "face_status":f["assessment"]["recognition_status"],
          "source_match":"IDENTICAL_SOURCE_BYTES",
          "provenance":"OPERATOR_DECLARED_UNVERIFIED",
          "correlation_status":"CONTROLLED_CANDIDATE",
          "decision_severity":None,
          "explanation":"Both frozen models processed identical source bytes with matching operator-declared camera context. No verified co-presence, person-to-PPE linkage, or camera authenticity is established."})
    return result
