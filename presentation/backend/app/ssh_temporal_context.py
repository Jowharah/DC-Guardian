"""Explicit, auditable controlled-test SSH time context.

Never modifies frozen detector timestamps or claims source timestamp verification.
This is an operator declaration for contextual *test* correlation only.
"""
import sqlite3
from datetime import datetime,timezone
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel
from presentation.backend.app.authentication import current_principal,authorize
from presentation.backend.app.authorization import Principal,Permission
from presentation.backend.app.ssh_publication import connect as ssh_connect
from presentation.backend.app.incident_store import _db_path

router=APIRouter()

class ControlledTimeInput(BaseModel):
    observed_at:str
    acknowledgment:bool

def parse_aware(value):
    try:
        parsed=datetime.fromisoformat(value.replace("Z","+00:00"))
        if parsed.tzinfo is None:raise ValueError("timezone required")
        return parsed.astimezone(timezone.utc)
    except (TypeError,AttributeError,ValueError) as exc:
        raise HTTPException(422,"observed_at must be an ISO-8601 timestamp with timezone") from exc

def context_db():
    db=sqlite3.connect(_db_path(),timeout=10)
    db.execute("""CREATE TABLE IF NOT EXISTS ssh_controlled_time_context(
      event_id TEXT PRIMARY KEY, observed_at TEXT NOT NULL,
      declared_by TEXT NOT NULL, declared_at TEXT NOT NULL,
      provenance TEXT NOT NULL)""")
    return db

@router.put("/api/v1/ssh/published/{event_id}/controlled-time")
def set_controlled_time(event_id:str,payload:ControlledTimeInput,
                        principal:Principal=Depends(current_principal)):
    authorize(principal,Permission.SSH_DETAIL)
    authorize(principal,Permission.SCENARIO_EXECUTE)
    if not payload.acknowledgment:
        raise HTTPException(422,"Explicit unverified test-time acknowledgment required")
    with ssh_connect() as db:
        row=db.execute("SELECT zone_id FROM ssh_published_evidence WHERE event_id=?",(event_id,)).fetchone()
    if row is None:raise HTTPException(404,"Published SSH Evidence not found")
    zone=row[0]
    authorize(principal,Permission.SSH_DETAIL,zone)
    authorize(principal,Permission.SCENARIO_EXECUTE,zone)
    observed=parse_aware(payload.observed_at).isoformat()
    now=datetime.now(timezone.utc).isoformat()
    with context_db() as db:
        db.execute("""INSERT INTO ssh_controlled_time_context VALUES (?,?,?,?,?)
          ON CONFLICT(event_id) DO UPDATE SET observed_at=excluded.observed_at,
          declared_by=excluded.declared_by,declared_at=excluded.declared_at,
          provenance=excluded.provenance""",
          (event_id,observed,principal.subject,now,"OPERATOR_DECLARED_UNVERIFIED_TEST_TIME"))
    return {"event_id":event_id,"observed_at":observed,
            "provenance":"OPERATOR_DECLARED_UNVERIFIED_TEST_TIME",
            "original_detector_timestamp_unchanged":True,
            "verified_observation_time":False}

def get_context(event_id):
    with context_db() as db:
        row=db.execute("SELECT observed_at,provenance FROM ssh_controlled_time_context WHERE event_id=?",(event_id,)).fetchone()
    return None if row is None else {"observed_at":row[0],"provenance":row[1]}
