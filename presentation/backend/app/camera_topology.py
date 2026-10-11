"""Read-only authorized camera choices from the declared topology."""
from fastapi import APIRouter,Depends
from presentation.backend.app.authentication import current_principal,authorize
from presentation.backend.app.authorization import Principal,Permission
from reasoning.topology.topology_mapper import load_topology,build_camera_index

router=APIRouter()

@router.get("/api/v1/topology/cameras")
def cameras(principal:Principal=Depends(current_principal)):
    authorize(principal,Permission.CAMERA_DETAIL)
    index=build_camera_index(load_topology())
    zones={}
    for camera_id,info in sorted(index.items()):
        zone=info["zone_id"]
        if zone not in principal.zones:continue
        authorize(principal,Permission.CAMERA_DETAIL,zone)
        zones.setdefault(zone,[]).append(camera_id)
    return [{"zone_id":zone,"cameras":items} for zone,items in sorted(zones.items())]
