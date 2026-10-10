"""Human verdicts on individual Evidence, recorded beside frozen detector output.

The detector record is never modified. Each verdict is an append-only,
hash-chained audit entry; the latest verdict for an Evidence item is its
effective human status. An OVERRIDDEN verdict changes whether the event is
treated as abnormal for correlation and is reported to the Investigator.
Local prototype only: SQLite is not a tamper-proof external audit service.
"""
import hashlib
import json
import sqlite3
from datetime import datetime,timezone
from typing import Literal
from uuid import uuid4
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from presentation.backend.app.authentication import current_principal,authorize
from presentation.backend.app.authorization import Principal,Permission,allowed
from presentation.backend.app.incident_store import _db_path
from presentation.backend.app.review_integrity import EVIDENCE_FIELDS,verify_evidence_database

router=APIRouter()
# Human-correctable status per domain, mapped to whether it is abnormal.
VOCABULARY={
 "ppe":{"COMPLIANT":False,"NON_COMPLIANT":True},
 "face":{"AUTHORIZED":False,"NO_FACE":False,"UNAUTHORIZED":True,"UNKNOWN_PERSON":True},
 "ssh":{"BENIGN":False,"ANOMALOUS":True},
 "maintenance":{"HEALTHY":False,"AT_RISK":True},
 "environment":{"NORMAL":False,"ABNORMAL":True},
}
DETAIL={"ssh":Permission.SSH_DETAIL,"ppe":Permission.CAMERA_DETAIL,"face":Permission.PERSON_DETAIL,
        "maintenance":Permission.MAINTENANCE_DETAIL,"environment":Permission.ENVIRONMENT_DETAIL}

class EvidenceReviewInput(BaseModel):
    verdict:Literal["CONFIRMED","OVERRIDDEN","INCONCLUSIVE"]
    corrected_status:str|None=None
    rationale:str=Field(min_length=15,max_length=2000)
    acknowledgment:bool

def connect():
    path=_db_path()
    path.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(path,timeout=15)
    db.execute("""CREATE TABLE IF NOT EXISTS evidence_review_audit(
        audit_id TEXT PRIMARY KEY, kind TEXT NOT NULL, evidence_id TEXT NOT NULL,
        zone_id TEXT NOT NULL, reviewer TEXT NOT NULL, recorded_at TEXT NOT NULL,
        verdict TEXT NOT NULL, corrected_status TEXT, model_status TEXT,
        rationale TEXT NOT NULL, previous_hash TEXT NOT NULL, entry_hash TEXT NOT NULL)""")
    return db

def model_status(kind,assessment):
    """The detector status the reviewer saw, snapshotted into the audit entry."""
    nested=assessment.get("assessment") if isinstance(assessment.get("assessment"),dict) else {}
    if kind=="ssh":return assessment.get("evidence_state")
    if kind=="ppe":return nested.get("overall_status")
    if kind=="face":return nested.get("recognition_status")
    return nested.get("assessment")

def effective(kind,records):
    """Latest verdict wins; only OVERRIDDEN changes the effective status."""
    if not records:return None
    latest=records[-1]
    overridden=latest["verdict"]=="OVERRIDDEN"
    return {"verdict":latest["verdict"],"model_status":latest["model_status"],
            "effective_status":latest["corrected_status"] if overridden else latest["model_status"],
            "abnormal":VOCABULARY[kind][latest["corrected_status"]] if overridden else None,
            "recorded_at":latest["recorded_at"],"reviewer":latest["reviewer"],
            "source":"HUMAN_OVERRIDE" if overridden else "HUMAN_"+latest["verdict"]}

def rows(where="",params=()):
    with connect() as db:
        found=db.execute("SELECT "+",".join(EVIDENCE_FIELDS)+" FROM evidence_review_audit "+where+" ORDER BY rowid ASC",params).fetchall()
    return [dict(zip(EVIDENCE_FIELDS,row)) for row in found]

def overrides():
    """(kind, evidence_id) -> abnormal, for Evidence whose latest verdict overrides the model."""
    latest={}
    for record in rows():
        latest[(record["kind"],record["evidence_id"])]=record
    return {key:VOCABULARY[r["kind"]][r["corrected_status"]] for key,r in latest.items()
            if r["verdict"]=="OVERRIDDEN"}

def summary(kind,evidence_id):
    """Verdict summary for model input: no free-text rationale or reviewer identity."""
    result=effective(kind,rows("WHERE kind=? AND evidence_id=?",(kind,evidence_id)))
    if result is None:return None
    return {k:result[k] for k in ("verdict","model_status","effective_status","recorded_at","source")}

def authorized_context(kind,evidence_id,principal):
    from presentation.backend.app.investigator_tools import single_evidence_context
    # Existing domain permission, existence and zone checks.
    return single_evidence_context(kind,evidence_id,principal)

@router.post("/api/v1/evidence-reviews/{kind}/{evidence_id}",status_code=201)
def record_evidence_review(kind:str,evidence_id:str,payload:EvidenceReviewInput,
                           principal:Principal=Depends(current_principal)):
    context=authorized_context(kind,evidence_id,principal)
    zone=context["zone_id"]
    authorize(principal,DETAIL[kind],zone)
    if not payload.acknowledgment:
        raise HTTPException(422,"Explicit human review acknowledgment required")
    seen=model_status(kind,context["source_assessment"])
    if payload.verdict=="OVERRIDDEN":
        if payload.corrected_status not in VOCABULARY[kind]:
            raise HTTPException(422,"corrected_status must be one of "+", ".join(VOCABULARY[kind]))
        if payload.corrected_status==seen:
            raise HTTPException(422,"Override must differ from the detector status; use CONFIRMED")
    elif payload.corrected_status is not None:
        raise HTTPException(422,"corrected_status is only allowed with OVERRIDDEN")
    rationale=payload.rationale.strip()
    if len(rationale)<15:
        raise HTTPException(422,"Review rationale must contain at least 15 characters")
    entry={"audit_id":"DCG-ER-"+uuid4().hex.upper(),"kind":kind,"evidence_id":evidence_id,
           "zone_id":zone,"reviewer":principal.subject,
           "recorded_at":datetime.now(timezone.utc).isoformat(),"verdict":payload.verdict,
           "corrected_status":payload.corrected_status,"model_status":seen,"rationale":rationale}
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        if verify_evidence_database(db)["status"]!="PASS":
            raise HTTPException(409,"Evidence review audit chain integrity failed; new review blocked")
        previous=db.execute("SELECT entry_hash FROM evidence_review_audit ORDER BY rowid DESC LIMIT 1").fetchone()
        entry["previous_hash"]=previous[0] if previous else "GENESIS"
        entry["entry_hash"]=hashlib.sha256(json.dumps(entry,sort_keys=True,separators=(",",":")).encode()).hexdigest()
        db.execute("INSERT INTO evidence_review_audit VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                   tuple(entry[k] for k in EVIDENCE_FIELDS))
    return {**entry,"detector_output_modified":False,
            "note":"Human verdict recorded beside the frozen detector output, which is unchanged."}

@router.get("/api/v1/evidence-reviews/{kind}/{evidence_id}")
def list_evidence_reviews(kind:str,evidence_id:str,principal:Principal=Depends(current_principal)):
    authorized_context(kind,evidence_id,principal)
    records=rows("WHERE kind=? AND evidence_id=?",(kind,evidence_id))
    return {"kind":kind,"evidence_id":evidence_id,"records":records,
            "effective":effective(kind,records),"vocabulary":list(VOCABULARY[kind])}

@router.get("/api/v1/evidence-reviews")
def latest_evidence_reviews(principal:Principal=Depends(current_principal)):
    """Latest verdict per Evidence item the operator may see (review queue)."""
    authorize(principal,Permission.INCIDENT_READ)
    latest={}
    for record in rows():
        if record["zone_id"] in principal.zones and allowed(principal,DETAIL[record["kind"]],record["zone_id"]):
            latest[(record["kind"],record["evidence_id"])]=record
    return [{**{k:r[k] for k in ("kind","evidence_id","zone_id","verdict","corrected_status",
                                 "model_status","recorded_at","reviewer")},
             "effective_status":r["corrected_status"] if r["verdict"]=="OVERRIDDEN" else r["model_status"]}
            for r in latest.values()]
