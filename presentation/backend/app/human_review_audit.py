"""Append-only local human review audit for controlled Evidence investigations.

Reviewer actions never modify detector Evidence, Decision severity, or graph edges.
Local prototype only: SQLite is not a tamper-proof external audit service.
"""
import hashlib
import json
import sqlite3
from datetime import datetime,timezone
from uuid import uuid4
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from typing import Literal
from presentation.backend.app.authentication import current_principal,authorize
from presentation.backend.app.authorization import Principal,Permission
from presentation.backend.app.incident_store import _db_path
from presentation.backend.app.unified_specialists import find_group,fingerprint
from presentation.backend.app.unified_decision import read_review_decision

from presentation.backend.app.review_integrity import verify_database

router=APIRouter()
Outcome=Literal["REVIEWED_NO_FINDING","NEEDS_FOLLOW_UP","INCONCLUSIVE"]

class ReviewInput(BaseModel):
    outcome:Outcome
    rationale:str=Field(min_length=15,max_length=2000)
    acknowledgment:bool

def connect():
    path=_db_path()
    path.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(path,timeout=15)
    db.execute("""CREATE TABLE IF NOT EXISTS human_review_audit(
        audit_id TEXT PRIMARY KEY, group_id TEXT NOT NULL,
        zone_id TEXT NOT NULL, reviewer TEXT NOT NULL,
        recorded_at TEXT NOT NULL, outcome TEXT NOT NULL,
        rationale TEXT NOT NULL, evidence_signature TEXT NOT NULL,
        policy_version TEXT NOT NULL, review_status TEXT NOT NULL,
        previous_hash TEXT NOT NULL, entry_hash TEXT NOT NULL)""")
    return db

def review_record(group_id,payload,principal):
    group=find_group(group_id,principal)
    authorize(principal,Permission.SCENARIO_EXECUTE,group["zone_id"])
    if not payload.acknowledgment:
        raise HTTPException(422,"Explicit human review acknowledgment required")
    # Require the existing grounded deterministic disposition before recording.
    decision=read_review_decision(group_id,principal)["decision"]
    if decision["status"]!="EVIDENCE_REVIEW_REQUIRED":
        raise HTTPException(409,"No deterministic review requirement for this group")
    entry={"audit_id":"DCG-HR-"+uuid4().hex.upper(),
           "group_id":group_id,"zone_id":group["zone_id"],
           "reviewer":principal.subject,"recorded_at":datetime.now(timezone.utc).isoformat(),
           "outcome":payload.outcome,"rationale":payload.rationale.strip(),
           "evidence_signature":hashlib.sha256(fingerprint(group).encode()).hexdigest(),
           "policy_version":decision["policy_version"],
           "review_status":decision["status"]}
    if len(entry["rationale"])<15:
        raise HTTPException(422,"Review rationale must contain at least 15 characters")
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        if verify_database(db)["status"] != "PASS":
            raise HTTPException(409,"Audit chain integrity failed; new review blocked")
        previous=db.execute("SELECT entry_hash FROM human_review_audit ORDER BY rowid DESC LIMIT 1").fetchone()
        entry["previous_hash"]=previous[0] if previous else "GENESIS"
        entry["entry_hash"]=hashlib.sha256(json.dumps(entry,sort_keys=True,separators=(",",":")).encode()).hexdigest()
        db.execute("INSERT INTO human_review_audit VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                   tuple(entry[k] for k in ("audit_id","group_id","zone_id","reviewer",
                   "recorded_at","outcome","rationale","evidence_signature",
                   "policy_version","review_status","previous_hash","entry_hash")))
    return {**entry,"severity":None,"autonomous_action_allowed":False,
            "note":"Human reviewer outcome only; original Evidence and deterministic Decision unchanged."}

@router.post("/api/v1/reviews/unified/{group_id}/records",status_code=201)
def record_review(group_id:str,payload:ReviewInput,principal:Principal=Depends(current_principal)):
    return review_record(group_id,payload,principal)

@router.get("/api/v1/reviews/unified/{group_id}/records")
def list_reviews(group_id:str,principal:Principal=Depends(current_principal)):
    group=find_group(group_id,principal)
    with connect() as db:
        rows=db.execute("""SELECT audit_id,group_id,zone_id,reviewer,recorded_at,
           outcome,rationale,evidence_signature,policy_version,review_status,
           previous_hash,entry_hash FROM human_review_audit WHERE group_id=?
           ORDER BY rowid ASC""",(group_id,)).fetchall()
    keys=("audit_id","group_id","zone_id","reviewer","recorded_at","outcome",
          "rationale","evidence_signature","policy_version","review_status",
          "previous_hash","entry_hash")
    return {"group_id":group_id,"zone_id":group["zone_id"],
            "records":[dict(zip(keys,row)) for row in rows],
            "note":"Historical append-only local audit; recorded reviews do not imply current Evidence validity."}

@router.get("/api/v1/reviews/audit-integrity")
def audit_integrity(principal:Principal=Depends(current_principal)):
    authorize(principal,Permission.SCENARIO_EXECUTE)
    if "administrator" not in principal.roles:
        raise HTTPException(403,"Administrator required")
    with connect() as db:
        return verify_database(db)
