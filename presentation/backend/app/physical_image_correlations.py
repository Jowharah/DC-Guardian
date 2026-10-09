"""Controlled same-source image pairing, no inferred camera authenticity or Decision."""
from datetime import datetime,timezone
from fastapi import APIRouter,Depends
from presentation.backend.app.authentication import current_principal,authorize
from presentation.backend.app.authorization import Principal,Permission
from presentation.backend.app.image_source_hashes import pairs,connect as hash_connect
from presentation.backend.app.image_metadata_store import get,connect as metadata_connect
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
    # Match on metadata, not just identical image bytes. The hash is an
    # optional stronger source signal; camera declarations are unverified.
    with metadata_connect() as db:
        rows=db.execute("SELECT observation_id,kind,zone_id FROM image_observation_metadata ORDER BY observation_id").fetchall()
    grouped={}
    for oid,kind,zone in rows:
        if zone in principal.zones and kind in ("ppe","face"):
            grouped.setdefault(zone,{}).setdefault(kind,[]).append(oid)
    with hash_connect() as db:
        hashes={row[0]:row[1] for row in db.execute("SELECT observation_id,source_sha256 FROM image_source_hashes")}
    result=[]
    used=set()
    for zone,groups in sorted(grouped.items()):
        authorize(principal,Permission.CAMERA_DETAIL,zone)
        authorize(principal,Permission.PERSON_DETAIL,zone)
        candidates=[]
        for pid in groups.get("ppe",[]):
            pm=get("ppe",pid,zone)
            for fid in groups.get("face",[]):
                fm=get("face",fid,zone)
                if not eligible_pair(None,None,pm,fm):continue
                delta=abs((parse_time(pm["capture_metadata"]["captured_at"])-parse_time(fm["capture_metadata"]["captured_at"])).total_seconds())
                same_hash=bool(hashes.get(pid) and hashes.get(pid)==hashes.get(fid))
                candidates.append((0 if same_hash else 1,delta,pid,fid,pm,fm,same_hash))
        for _,delta,pid,fid,pm,fm,same_hash in sorted(candidates):
            if pid in used or fid in used:continue
            p=ppe_observations.get_observation(pid)
            f=face_observations.get(fid)
            if p is None or f is None:continue
            used.update((pid,fid))
            result.append({"id":"DCG-PHYSICAL-"+pid+"-"+fid,"zone_id":zone,
              "ppe_observation_id":pid,"face_observation_id":fid,
              "camera_id":pm["capture_metadata"]["camera_id"],
              "captured_at":pm["capture_metadata"]["captured_at"],
              "time_difference_seconds":delta,
              "ppe_status":p["assessment"]["overall_status"],
              "face_status":f["assessment"]["recognition_status"],
              "source_match":"IDENTICAL_SOURCE_BYTES" if same_hash else "MATCHING_DECLARED_CAMERA_AND_TIME",
              "provenance":"OPERATOR_DECLARED_UNVERIFIED",
              "correlation_status":"CONTROLLED_CANDIDATE",
              "decision_severity":None,
              "explanation":"Controlled candidate based on source hash or matching operator-declared camera and capture time. Camera authenticity, co-presence, and person-to-PPE linkage are not verified."})
    return result
