"""Controlled camera/time metadata for retained PPE and Face observations."""
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel
from presentation.backend.app.authentication import current_principal,authorize
from presentation.backend.app.authorization import Principal,Permission
from presentation.backend.app import ppe_observations,face_observations
from presentation.backend.app.image_evidence_mapping import validate_metadata,project_observation
from presentation.backend.app.image_metadata_store import save

router=APIRouter()

class CaptureDeclaration(BaseModel):
    camera_id:str
    captured_at:str
    acknowledgment:bool

@router.post("/api/v1/images/{kind}/{observation_id}/capture-declaration")
def declare_capture(kind:str,observation_id:str,payload:CaptureDeclaration,
                    principal:Principal=Depends(current_principal)):
    if kind not in ("ppe","face"):
        raise HTTPException(422,"Unsupported image kind")
    permission=Permission.CAMERA_DETAIL if kind=="ppe" else Permission.PERSON_DETAIL
    authorize(principal,permission)
    authorize(principal,Permission.SCENARIO_EXECUTE)
    record=(ppe_observations.get_observation(observation_id) if kind=="ppe"
            else face_observations.get(observation_id))
    if record is None:raise HTTPException(404,"Retained observation not found")
    zone=record["zone_id"]
    authorize(principal,permission,zone)
    authorize(principal,Permission.SCENARIO_EXECUTE,zone)
    if not payload.acknowledgment:
        raise HTTPException(422,"Unverified camera/time acknowledgment required")
    try:
        metadata=validate_metadata({"camera_id":payload.camera_id,
                                    "captured_at":payload.captured_at},zone)
    except (ValueError,TypeError) as exc:
        raise HTTPException(422,str(exc)) from exc
    try:
        graph=project_observation(kind,observation_id,record["assessment"],metadata)
    except Exception as exc:
        raise HTTPException(503,"Neo4j projection unavailable") from exc
    save(kind,observation_id,zone,metadata,graph)
    return {"observation_id":observation_id,"capture_metadata":metadata,
            "graph_projection":graph,"camera_verified":False}
