"""Explicit controlled standalone Evidence events, separate from correlated incidents.

Local research prototype: events are operator-created synthetic assessments.
No Decision severity is assigned and no model inference is claimed.
"""
from datetime import datetime, timezone
from enum import StrEnum
from uuid import uuid4
import sqlite3
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Literal
from presentation.backend.app.incident_store import _db_path
from presentation.backend.app.authentication import current_principal, authorize
from presentation.backend.app.authorization import Principal, Permission

router = APIRouter()
class Domain(StrEnum):
    CYBERSECURITY = "CYBERSECURITY"
    ENVIRONMENTAL = "ENVIRONMENTAL"
    MAINTENANCE = "MAINTENANCE"
    SAFETY = "SAFETY"
    PHYSICAL_SECURITY = "PHYSICAL_SECURITY"

class SyntheticEventInput(BaseModel):
    domain: Domain
    zone_id: Literal["ZONE-A", "ZONE-B", "ZONE-C"]
    state: str = Field(min_length=1, max_length=60, pattern=r"^[A-Z][A-Z0-9_]*$")
    title: str = Field(min_length=3, max_length=120)
    asset_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    description: str = Field(default="", max_length=500)

def _connect():
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.execute("""CREATE TABLE IF NOT EXISTS standalone_events (
        event_id TEXT PRIMARY KEY, zone_id TEXT NOT NULL,
        received_at TEXT NOT NULL, domain TEXT NOT NULL,
        state TEXT NOT NULL, title TEXT NOT NULL,
        asset_id TEXT NOT NULL, description TEXT NOT NULL,
        created_by TEXT NOT NULL
    )""")
    return conn

@router.get("/api/v1/events/standalone")
def list_events(principal: Principal = Depends(current_principal)):
    authorize(principal, Permission.INCIDENT_READ)
    with _connect() as conn:
        rows = conn.execute("""SELECT event_id,zone_id,received_at,domain,state,title,
                              asset_id,description FROM standalone_events
                              ORDER BY received_at DESC LIMIT 200""").fetchall()
    keys = ("event_id","zone_id","received_at","domain","state","title","asset_id","description")
    return [{**dict(zip(keys,row)), "record_type":"STANDALONE_EVIDENCE",
             "source_type":"OPERATOR_SYNTHETIC", "decision_severity":None}
            for row in rows if row[1] in principal.zones]

@router.post("/api/v1/events/standalone", status_code=201)
def create_event(payload: SyntheticEventInput, principal: Principal = Depends(current_principal)):
    authorize(principal, Permission.SCENARIO_EXECUTE, payload.zone_id)
    event_id = "DCG-EVT-" + uuid4().hex[:20].upper()
    received_at = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute("INSERT INTO standalone_events VALUES (?,?,?,?,?,?,?,?,?)",
                     (event_id,payload.zone_id,received_at,payload.domain.value,
                      payload.state,payload.title,payload.asset_id,payload.description,principal.subject))
    return {"event_id":event_id, "zone_id":payload.zone_id, "received_at":received_at,
            "domain":payload.domain.value, "state":payload.state, "title":payload.title,
            "asset_id":payload.asset_id, "description":payload.description,
            "record_type":"STANDALONE_EVIDENCE", "source_type":"OPERATOR_SYNTHETIC",
            "decision_severity":None}
