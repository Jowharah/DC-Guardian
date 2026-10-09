"""Conservative spatial candidate from frozen Face and PPE outputs.

Same original source bytes are mandatory for pixel geometry. This does not
establish identity, authorization, or a physical-safety violation.
"""
import math
from fastapi import APIRouter,Depends,HTTPException
from presentation.backend.app.authentication import current_principal,authorize
from presentation.backend.app.authorization import Principal,Permission
from presentation.backend.app.physical_image_correlations import image_correlations
from presentation.backend.app.image_source_hashes import connect as hash_connect
from presentation.backend.app import face_observations,ppe_observations

router=APIRouter()

def face_box(area):
    if not isinstance(area,dict):return None
    try:
        if all(k in area for k in ("x","y","w","h")):
            x,y,w,h=(float(area[k]) for k in ("x","y","w","h"))
            result=[x,y,x+w,y+h]
        elif all(k in area for k in ("x1","y1","x2","y2")):
            result=[float(area[k]) for k in ("x1","y1","x2","y2")]
        else:return None
        if not all(math.isfinite(v) for v in result):return None
        if result[2]<=result[0] or result[3]<=result[1]:return None
        return result
    except (TypeError,ValueError):return None

def overlap(face,person):
    x1=max(face[0],person[0]);y1=max(face[1],person[1])
    x2=min(face[2],person[2]);y2=min(face[3],person[3])
    return max(0,x2-x1)*max(0,y2-y1)/((face[2]-face[0])*(face[3]-face[1]))

def associate(ppe,face,same_bytes):
    base={"status":"NO_MATCH","person_index":None,"ppe_status":None,
          "identity_link_established":False,"decision_severity":None}
    if not same_bytes:
        return {**base,"status":"NOT_EVALUATED","reason":"DIFFERENT_SOURCE_IMAGES"}
    if face.get("recognition_status")!="RECOGNIZED" or not face.get("person_id"):
        return {**base,"status":"NOT_EVALUATED","reason":"FACE_NOT_RECOGNIZED"}
    box=face_box(face.get("facial_area"))
    if box is None:return {**base,"status":"NOT_EVALUATED","reason":"FACE_GEOMETRY_UNAVAILABLE"}
    people=[d for d in ppe.get("detections",[]) if d.get("class_name")=="person"]
    # PPE policy indices sort person detections by x1, y1.
    people.sort(key=lambda d:(d["bbox_xyxy"][0],d["bbox_xyxy"][1]))
    if len(people)!=len(ppe.get("people",[])):
        return {**base,"status":"NOT_EVALUATED","reason":"PERSON_INDEX_CONTRACT_MISMATCH"}
    scores=[overlap(box,d["bbox_xyxy"]) for d in people]
    eligible=[i for i,score in enumerate(scores) if score>=0.8]
    if len(eligible)!=1:
        return {**base,"status":"AMBIGUOUS" if len(eligible)>1 else "NO_MATCH",
                "reason":"FACE_PERSON_OVERLAP_NOT_UNIQUE"}
    idx=eligible[0]
    status=ppe["people"][idx]["status"]
    return {**base,"status":"MATCH_CANDIDATE","person_index":idx,
            "ppe_status":status,"face_containment_ratio":round(scores[idx],4),
            "reason":"UNIQUE_FACE_CONTAINMENT_IN_DETECTED_PERSON"}

@router.get("/api/v1/physical/image-correlations/{candidate_id}/person-association")
def person_association(candidate_id:str,principal:Principal=Depends(current_principal)):
    for perm in (Permission.CAMERA_DETAIL,Permission.PERSON_DETAIL):
        authorize(principal,perm)
    candidate=next((x for x in image_correlations(principal) if x["id"]==candidate_id),None)
    if candidate is None:raise HTTPException(404,"Physical candidate not found")
    zone=candidate["zone_id"]
    for perm in (Permission.CAMERA_DETAIL,Permission.PERSON_DETAIL):
        authorize(principal,perm,zone)
    p=ppe_observations.get_observation(candidate["ppe_observation_id"])
    f=face_observations.get(candidate["face_observation_id"])
    if p is None or f is None:raise HTTPException(404,"Source observation missing")
    with hash_connect() as db:
        rows=db.execute("SELECT observation_id,source_sha256 FROM image_source_hashes WHERE observation_id IN (?,?)",
            (candidate["ppe_observation_id"],candidate["face_observation_id"])).fetchall()
    hashes=dict(rows)
    same=bool(hashes.get(candidate["ppe_observation_id"]) and
              hashes.get(candidate["ppe_observation_id"])==hashes.get(candidate["face_observation_id"]))
    result=associate(p["assessment"],f["assessment"],same)
    return {"candidate_id":candidate_id,"recognized_person_id":f["assessment"].get("person_id")
            if f["assessment"].get("recognition_status")=="RECOGNIZED" else None,
            **result}
