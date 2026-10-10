"""Private, opt-in, bounded local Investigator conversation history.

Prototype storage is plaintext SQLite: only approved test Evidence, not sensitive
production conversations. No model input is taken from stored history.
"""
import sqlite3
from datetime import datetime,timezone,timedelta
from uuid import uuid4
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from typing import Literal
from presentation.backend.app.authentication import current_principal,local_setting
from presentation.backend.app.authorization import Principal
from presentation.backend.app.incident_store import _db_path
from presentation.backend.app.unified_specialists import find_group

router=APIRouter()
class HistoryEntry(BaseModel):
    question:str=Field(min_length=3,max_length=1000)
    answer:str=Field(min_length=1,max_length=10000)

def enabled():
    return local_setting("DCG_INVESTIGATOR_HISTORY_ENABLED")=="1"

def connect():
    path=_db_path()
    path.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(path,timeout=10)
    db.execute("""CREATE TABLE IF NOT EXISTS investigator_history (
        id TEXT PRIMARY KEY, group_id TEXT NOT NULL, reviewer TEXT NOT NULL,
        created_at TEXT NOT NULL, question TEXT NOT NULL, answer TEXT NOT NULL)""")
    db.execute("CREATE INDEX IF NOT EXISTS idx_investigator_history_scope ON investigator_history(reviewer,group_id,created_at)")
    return db

def scope(group_id,principal):
    if not enabled():raise HTTPException(503,"INVESTIGATOR_HISTORY_DISABLED")
    find_group(group_id,principal)

def prune(db):
    days=int(local_setting("DCG_INVESTIGATOR_HISTORY_DAYS") or "7")
    if not 1<=days<=30:raise HTTPException(503,"INVESTIGATOR_HISTORY_RETENTION_INVALID")
    cutoff=(datetime.now(timezone.utc)-timedelta(days=days)).isoformat()
    db.execute("DELETE FROM investigator_history WHERE created_at < ?",(cutoff,))

@router.get("/api/v1/investigator/unified/{group_id}/history")
def get_history(group_id:str,principal:Principal=Depends(current_principal)):
    scope(group_id,principal)
    with connect() as db:
        prune(db)
        rows=db.execute("""SELECT id,created_at,question,answer FROM investigator_history
            WHERE group_id=? AND reviewer=? ORDER BY created_at DESC,id DESC LIMIT 30""",
            (group_id,principal.subject)).fetchall()
    return {"group_id":group_id,"messages":[dict(zip(("id","created_at","question","answer"),r)) for r in reversed(rows)]}

@router.post("/api/v1/investigator/unified/{group_id}/history",status_code=201)
def save_history(group_id:str,entry:HistoryEntry,principal:Principal=Depends(current_principal)):
    scope(group_id,principal)
    row={"id":"DCG-CHAT-"+uuid4().hex.upper(),"created_at":datetime.now(timezone.utc).isoformat(),
         "question":entry.question,"answer":entry.answer}
    with connect() as db:
        prune(db)
        db.execute("INSERT INTO investigator_history VALUES (?,?,?,?,?,?)",
                   (row["id"],group_id,principal.subject,row["created_at"],row["question"],row["answer"]))
    return row

@router.delete("/api/v1/investigator/unified/{group_id}/history")
def clear_history(group_id:str,principal:Principal=Depends(current_principal)):
    scope(group_id,principal)
    with connect() as db:
        db.execute("DELETE FROM investigator_history WHERE group_id=? AND reviewer=?",(group_id,principal.subject))
    return {"cleared":True,"group_id":group_id}

def _other_scope(kind,identifier,principal):
    if not enabled():raise HTTPException(503,"INVESTIGATOR_HISTORY_DISABLED")
    if kind=="operations":
        from presentation.backend.app.operational_decision import get_candidate
        get_candidate(identifier,principal)
    else:
        from presentation.backend.app.investigator_tools import single_evidence_context
        single_evidence_context(kind,identifier,principal)
    return kind+":"+identifier

def _other_history(kind,identifier,principal):
    key=_other_scope(kind,identifier,principal)
    with connect() as db:
        prune(db)
        rows=db.execute("SELECT id,created_at,question,answer FROM investigator_history WHERE group_id=? AND reviewer=? ORDER BY created_at DESC,id DESC LIMIT 30",(key,principal.subject)).fetchall()
    return {"messages":[dict(zip(("id","created_at","question","answer"),r)) for r in reversed(rows)]}

def _other_save(kind,identifier,entry,principal):
    key=_other_scope(kind,identifier,principal)
    row={"id":"DCG-CHAT-"+uuid4().hex.upper(),"created_at":datetime.now(timezone.utc).isoformat(),"question":entry.question,"answer":entry.answer}
    with connect() as db:
        prune(db)
        db.execute("INSERT INTO investigator_history VALUES (?,?,?,?,?,?)",(row["id"],key,principal.subject,row["created_at"],row["question"],row["answer"]))
    return row

def _other_clear(kind,identifier,principal):
    key=_other_scope(kind,identifier,principal)
    with connect() as db:
        db.execute("DELETE FROM investigator_history WHERE group_id=? AND reviewer=?",(key,principal.subject))
    return {"cleared":True}

@router.get("/api/v1/investigator/operations/{candidate_id}/history")
def operations_history(candidate_id:str,principal:Principal=Depends(current_principal)):
    return _other_history("operations",candidate_id,principal)

@router.post("/api/v1/investigator/operations/{candidate_id}/history",status_code=201)
def operations_save(candidate_id:str,entry:HistoryEntry,principal:Principal=Depends(current_principal)):
    return _other_save("operations",candidate_id,entry,principal)

@router.delete("/api/v1/investigator/operations/{candidate_id}/history")
def operations_clear(candidate_id:str,principal:Principal=Depends(current_principal)):
    return _other_clear("operations",candidate_id,principal)

@router.get("/api/v1/investigator/evidence/{kind}/{evidence_id}/history")
def evidence_history(kind:str,evidence_id:str,principal:Principal=Depends(current_principal)):
    return _other_history(kind,evidence_id,principal)

@router.post("/api/v1/investigator/evidence/{kind}/{evidence_id}/history",status_code=201)
def evidence_save(kind:str,evidence_id:str,entry:HistoryEntry,principal:Principal=Depends(current_principal)):
    return _other_save(kind,evidence_id,entry,principal)

@router.delete("/api/v1/investigator/evidence/{kind}/{evidence_id}/history")
def evidence_clear(kind:str,evidence_id:str,principal:Principal=Depends(current_principal)):
    return _other_clear(kind,evidence_id,principal)
