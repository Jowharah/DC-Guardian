"""Read-only, source-scoped correlation results after Evidence publication.

Reuses existing correlation contracts. Does not create or alter model Evidence,
infer causation, or assign severity. Called after successful publication.
"""
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from presentation.backend.app.authentication import current_principal,authorize
from presentation.backend.app.authorization import Principal,Permission
from presentation.backend.app.unified_correlations import unified_correlations

router=APIRouter()
KINDS={"ssh","maintenance","environment","ppe","face"}

class CheckRequest(BaseModel):
    kind:str
    observation_ids:list[str]=Field(min_length=1,max_length=100)

def matches(group,kind,ids):
    return any(r["kind"]==kind and r["observation_id"] in ids for r in group["evidence"])

@router.post("/api/v1/correlations/check-published")
def check_published(payload:CheckRequest,principal:Principal=Depends(current_principal)):
    if payload.kind not in KINDS:raise HTTPException(422,"Unsupported Evidence kind")
    for permission in (Permission.INCIDENT_READ,Permission.SSH_DETAIL,
                       Permission.MAINTENANCE_DETAIL,Permission.ENVIRONMENT_DETAIL,
                       Permission.CAMERA_DETAIL,Permission.PERSON_DETAIL):
        authorize(principal,permission)
    # Existing service enforces per-zone permissions and uses retained source records.
    groups=unified_correlations(principal)
    ids=set(payload.observation_ids)
    matched=[g for g in groups if matches(g,payload.kind,ids)]
    return {"kind":payload.kind,"observation_ids":sorted(ids),
            "status":"CANDIDATES_FOUND" if matched else "NO_ELIGIBLE_CORRELATION",
            "groups":matched,"checked_against":"PERSISTED_EVIDENCE",
            "note":"A correlation candidate is contextual; no identity, causation, or severity is inferred."}
