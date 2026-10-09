"""RBAC-protected image capture metadata projection, never a camera verification claim."""
from fastapi import APIRouter,Depends,HTTPException
from presentation.backend.app.authentication import current_principal,authorize
from presentation.backend.app.authorization import Principal,Permission
from presentation.backend.app.image_metadata_store import get
from presentation.backend.app import face_observations,ppe_observations

router=APIRouter()

@router.get("/api/v1/image-observations/{kind}/{observation_id}/metadata")
def image_metadata(kind:str,observation_id:str,principal:Principal=Depends(current_principal)):
    if kind=="face":
        permission=Permission.PERSON_DETAIL
        item=face_observations.get(observation_id)
    elif kind=="ppe":
        permission=Permission.CAMERA_DETAIL
        item=ppe_observations.get_observation(observation_id)
    else:
        raise HTTPException(404,"Unknown image Evidence domain")
    authorize(principal,permission)
    if item is None:
        raise HTTPException(404,"Image observation not found")
    authorize(principal,permission,item["zone_id"])
    metadata=get(kind,observation_id,item["zone_id"])
    if metadata is None:
        return {"capture_metadata":None,"graph_projection":None}
    return metadata
