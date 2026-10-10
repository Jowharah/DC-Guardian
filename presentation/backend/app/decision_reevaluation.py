"""Re-evaluate saved Decisions after human verdicts change their inputs.

The original Decision row is never modified. A re-evaluation re-runs the same
deterministic Decision Rules v1 on human-verified input states, reusing the
saved specialist grounding (no model call), and is appended to its own table.
The latest re-evaluation is the current Decision. When a human clears an input,
the rules no longer apply: severity is None, never a guessed lower level.
"""
import json
import sqlite3
from datetime import datetime,timezone
from uuid import uuid4
from fastapi import APIRouter,Depends,HTTPException
from presentation.backend.app.authentication import current_principal,authorize
from presentation.backend.app.authorization import Principal,Permission
from presentation.backend.app.incident_store import _db_path
from presentation.backend.app import evidence_review

router=APIRouter()

def storage():
    path=_db_path()
    path.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(path,timeout=15)
    db.execute("""CREATE TABLE IF NOT EXISTS decision_reevaluations(
        reevaluation_id TEXT PRIMARY KEY, decision_kind TEXT NOT NULL,
        subject_id TEXT NOT NULL, zone_id TEXT NOT NULL, evaluated_at TEXT NOT NULL,
        evaluated_by TEXT NOT NULL, inputs_json TEXT NOT NULL, decision_json TEXT NOT NULL)""")
    return db

def latest(kind,subject_id):
    with storage() as db:
        row=db.execute("""SELECT reevaluation_id,evaluated_at,evaluated_by,inputs_json,decision_json
            FROM decision_reevaluations WHERE decision_kind=? AND subject_id=?
            ORDER BY rowid DESC LIMIT 1""",(kind,subject_id)).fetchone()
    if row is None:return None
    return {"reevaluation_id":row[0],"evaluated_at":row[1],"evaluated_by":row[2],
            "inputs":json.loads(row[3]),"decision":json.loads(row[4])}

def effective_inputs(members):
    """Human-verified abnormality per Decision input (kind, evidence_id).

    A Decision only exists for abnormal detector input, so an input without an
    override is abnormal. The verdict audit ID records which verdict applied.
    """
    result={}
    for kind,evidence_id in members:
        records=evidence_review.rows("WHERE kind=? AND evidence_id=?",(kind,evidence_id))
        state=evidence_review.effective(kind,records)
        overridden=bool(state and state["source"]=="HUMAN_OVERRIDE")
        result[kind+":"+evidence_id]={
            "abnormal":state["abnormal"] if overridden else True,
            "status":state["effective_status"] if state else None,
            "source":state["source"] if state else "DETECTOR",
            "verdict_audit_id":records[-1]["audit_id"] if records else None}
    return result

def overlay(kind,subject_id,original,members):
    """Current Decision plus original, latest re-evaluation and input review flag."""
    if original is None:return None
    saved=latest(kind,subject_id)
    used=saved["inputs"] if saved else {key:{"abnormal":True} for key in
                                       (k+":"+e for k,e in members)}
    current=effective_inputs(members)
    changed=sorted(key for key,value in current.items()
                   if value["abnormal"]!=used.get(key,{}).get("abnormal"))
    return {"decision":saved["decision"] if saved else original,
            "original_decision":original,
            "reevaluation":{k:saved[k] for k in ("reevaluation_id","evaluated_at","evaluated_by","inputs")} if saved else None,
            "input_review":{"reevaluation_required":bool(changed),"changed_inputs":changed,
                            "current_inputs":current}}

def cleared_decision(original,current):
    cleared=sorted(key for key,value in current.items() if value["abnormal"] is False)
    return {**original,"incident_status":"INPUT_CLEARED_BY_HUMAN_VERDICT","severity":None,
            "response_mode":"NO_ACTION_ASSIGNED","escalation_required":False,
            "autonomous_action_allowed":False,"decision_rules_triggered":[],
            "cleared_inputs":cleared,
            "rationale":["A human verdict cleared Decision input; no Decision Rules v1 rule applies.",
                         "The original Decision is retained unchanged in history."]}

def append(kind,subject_id,zone,inputs,decision,principal):
    entry={"reevaluation_id":"DCG-RE-"+uuid4().hex.upper(),"evaluated_at":datetime.now(timezone.utc).isoformat()}
    with storage() as db:
        db.execute("INSERT INTO decision_reevaluations VALUES (?,?,?,?,?,?,?,?)",
                   (entry["reevaluation_id"],kind,subject_id,zone,entry["evaluated_at"],
                    principal.subject,json.dumps(inputs),json.dumps(decision)))
    return {**entry,"evaluated_by":principal.subject,"inputs":inputs,"decision":decision,
            "original_decision_modified":False}

@router.post("/api/v1/decisions/ssh/{event_id}/reevaluate",status_code=201)
def reevaluate_ssh(event_id:str,principal:Principal=Depends(current_principal)):
    from presentation.backend.app.ssh_publication import connect,load_decision
    from presentation.backend.app.ssh_decision import decide_standalone_ssh
    authorize(principal,Permission.SSH_DETAIL)
    with connect() as db:
        row=db.execute("SELECT zone_id,payload FROM ssh_published_evidence WHERE event_id=?",(event_id,)).fetchone()
    if row is None:raise HTTPException(404,"Published SSH evidence not found")
    zone,payload=row
    authorize(principal,Permission.SSH_DETAIL,zone)
    authorize(principal,Permission.SCENARIO_EXECUTE,zone)
    saved=load_decision(event_id)
    if saved is None:raise HTTPException(409,"No saved Decision to re-evaluate")
    inputs=effective_inputs([("ssh",event_id)])
    if inputs["ssh:"+event_id]["abnormal"]:
        try:
            decision=decide_standalone_ssh(json.loads(payload),saved["correlation"],saved["specialist"])
        except ValueError as exc:
            raise HTTPException(409,"Saved Decision inputs no longer satisfy the Decision contract") from exc
    else:
        decision=cleared_decision(saved["decision"],inputs)
    return append("ssh",event_id,zone,inputs,decision,principal)

@router.post("/api/v1/decisions/operations/{candidate_id}/reevaluate",status_code=201)
def reevaluate_operations(candidate_id:str,principal:Principal=Depends(current_principal)):
    from presentation.backend.app.operational_decision import get_candidate,make_decision,storage as decision_storage
    candidate=get_candidate(candidate_id,principal)
    authorize(principal,Permission.SCENARIO_EXECUTE,candidate["zone_id"])
    with decision_storage() as db:
        row=db.execute("SELECT response_json,decision_json FROM operational_decisions WHERE candidate_id=?",(candidate_id,)).fetchone()
    if row is None:raise HTTPException(409,"No saved Decision to re-evaluate")
    specialist,original=json.loads(row[0]),json.loads(row[1])
    inputs=effective_inputs(operational_members(candidate))
    if all(value["abnormal"] for value in inputs.values()):
        try:
            decision=make_decision(candidate,specialist)
        except ValueError as exc:
            raise HTTPException(409,"Saved Decision inputs no longer satisfy the Decision contract") from exc
    else:
        decision=cleared_decision(original,inputs)
    return append("operations",candidate_id,candidate["zone_id"],inputs,decision,principal)

def ssh_view(event_id,record):
    """Saved SSH Decision record with the current Decision and input review."""
    if record is None:return None
    return {**record,**overlay("ssh",event_id,record["decision"],[("ssh",event_id)])}

def operational_members(candidate):
    return [("maintenance",candidate["maintenance_event_id"]),("environment",candidate["environment_event_id"])]
