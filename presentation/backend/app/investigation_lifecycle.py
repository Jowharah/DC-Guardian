"""Investigation lifecycle for unified groups and single Evidence (policy DCG-LIFECYCLE-v1).

States: OPEN (no transition yet) -> IN_REVIEW -> RESOLVED -> (REOPEN) -> IN_REVIEW ...
- START_REVIEW: an operator allowed to review the subject claims it (OPEN or REOPENED).
- RESOLVE: the assigned reviewer or an administrator, with a resolution, a rationale
  (>= 15 characters) and an explicit acknowledgment.
- REOPEN: any operator allowed to review the subject, with a rationale.
A resolved subject whose Evidence or human verdicts changed after resolution is
reported as REOPENED_EVIDENCE_CHANGED (computed on read; no record is altered).

Who may review: unified groups need every member domain plus scenario:execute
(administrators), as group reviews do; a single Evidence record needs its
domain's detail permission in its zone, as verdicts do.

Lifecycle transitions never change detector output, verdicts, Decisions or
severity. Transitions form an append-only hash chain (same scheme and verifier
as the review audits), included in audit integrity and external checkpoints.
Operator-adjustable policy (default chosen 2026-10-12).
"""
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from presentation.backend.app.authentication import authorize, current_principal
from presentation.backend.app.authorization import Permission, Principal
from presentation.backend.app.incident_store import _db_path

router = APIRouter()
POLICY = "DCG-LIFECYCLE-v1"
EVIDENCE_KINDS = ("ssh", "ppe", "face", "maintenance", "environment")
RESOLUTIONS = ("NO_FINDING", "FALSE_POSITIVE", "HANDLED_OUTSIDE_SYSTEM", "DUPLICATE")
FIELDS = ("transition_id", "subject_type", "subject_id", "zone_id", "actor", "recorded_at", "action",
          "from_state", "to_state", "assignee", "resolution", "rationale", "evidence_signature",
          "policy_version", "previous_hash", "entry_hash")


class TransitionInput(BaseModel):
    action: Literal["START_REVIEW", "RESOLVE", "REOPEN"]
    resolution: Literal["NO_FINDING", "FALSE_POSITIVE", "HANDLED_OUTSIDE_SYSTEM", "DUPLICATE"] | None = None
    rationale: str = Field(default="", max_length=2000)
    acknowledgment: bool = False


def connect():
    db = sqlite3.connect(_db_path(), timeout=15)
    db.execute("""CREATE TABLE IF NOT EXISTS investigation_lifecycle(
        transition_id TEXT PRIMARY KEY, subject_type TEXT NOT NULL, subject_id TEXT NOT NULL,
        zone_id TEXT NOT NULL, actor TEXT NOT NULL, recorded_at TEXT NOT NULL, action TEXT NOT NULL,
        from_state TEXT NOT NULL, to_state TEXT NOT NULL, assignee TEXT, resolution TEXT,
        rationale TEXT NOT NULL, evidence_signature TEXT NOT NULL, policy_version TEXT NOT NULL,
        previous_hash TEXT NOT NULL, entry_hash TEXT NOT NULL)""")
    return db


def subject(subject_type, subject_id, principal):
    """(zone, evidence signature) after the same authorization reviews of this subject use."""
    if subject_type == "group":
        from presentation.backend.app.unified_specialists import find_group, fingerprint
        group = find_group(subject_id, principal)
        authorize(principal, Permission.SCENARIO_EXECUTE, group["zone_id"])
        verdicts = [(m["kind"], m["observation_id"], (m.get("human_review") or {}).get("effective_status"))
                    for m in group.get("members", [])]
        return group["zone_id"], hashlib.sha256((fingerprint(group) + json.dumps(verdicts)).encode()).hexdigest()
    if subject_type in EVIDENCE_KINDS:
        from presentation.backend.app.single_specialists import authorized_evidence, signature
        zone, evidence = authorized_evidence(subject_type, subject_id, principal)
        return zone, hashlib.sha256(signature(evidence).encode()).hexdigest()
    raise HTTPException(404, "Unsupported lifecycle subject")


def history(subject_type, subject_id):
    with connect() as db:
        rows = db.execute("SELECT " + ",".join(FIELDS) + " FROM investigation_lifecycle "  # nosec B608: constant columns
                          "WHERE subject_type=? AND subject_id=? ORDER BY rowid ASC", (subject_type, subject_id)).fetchall()
    return [dict(zip(FIELDS, r)) for r in rows]


def state_of(records, current_signature):
    if not records:
        return {"state": "OPEN", "assignee": None, "resolution": None}
    last = records[-1]
    state = last["to_state"]
    if state == "RESOLVED" and last["evidence_signature"] != current_signature:
        state = "REOPENED_EVIDENCE_CHANGED"
    return {"state": state, "assignee": last["assignee"], "resolution": last["resolution"] if state == "RESOLVED" else None,
            "since": last["recorded_at"]}


def view(subject_type, subject_id, principal):
    _, current = subject(subject_type, subject_id, principal)
    records = history(subject_type, subject_id)
    return {"subject_type": subject_type, "subject_id": subject_id, "policy_version": POLICY,
            **state_of(records, current),
            "transitions": [{k: r[k] for k in ("recorded_at", "actor", "action", "from_state", "to_state",
                                                "assignee", "resolution", "rationale")} for r in records],
            "note": "Lifecycle state only; Evidence, verdicts, Decisions and severity are unchanged."}


ALLOWED = {"START_REVIEW": ("OPEN", "REOPENED", "REOPENED_EVIDENCE_CHANGED"),
           "RESOLVE": ("IN_REVIEW",),
           "REOPEN": ("RESOLVED",)}
TARGET = {"START_REVIEW": "IN_REVIEW", "RESOLVE": "RESOLVED", "REOPEN": "REOPENED"}


def transition(subject_type, subject_id, payload, principal):
    from presentation.backend.app.review_integrity import verify_records
    zone, signature = subject(subject_type, subject_id, principal)
    rationale = payload.rationale.strip()
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        rows = db.execute("SELECT " + ",".join(FIELDS) + " FROM investigation_lifecycle ORDER BY rowid ASC").fetchall()  # nosec B608: constant columns
        if verify_records(rows, FIELDS)["status"] != "PASS":
            raise HTTPException(409, "Lifecycle chain integrity failed; transition blocked")
        records = [dict(zip(FIELDS, r)) for r in rows if r[1] == subject_type and r[2] == subject_id]
        current = state_of(records, signature)
        if current["state"] not in ALLOWED[payload.action]:
            raise HTTPException(409, f"{payload.action} is not allowed from {current['state']}")
        assignee = current["assignee"]
        if payload.action == "START_REVIEW":
            assignee = principal.subject
        if payload.action == "RESOLVE":
            if principal.subject != assignee and "administrator" not in principal.roles:
                raise HTTPException(403, "Only the assigned reviewer or an administrator may resolve")
            if payload.resolution is None or len(rationale) < 15 or not payload.acknowledgment:
                raise HTTPException(422, "Resolution, a rationale of at least 15 characters and acknowledgment are required")
        if payload.action == "REOPEN" and len(rationale) < 15:
            raise HTTPException(422, "A rationale of at least 15 characters is required to reopen")
        entry = {"transition_id": "DCG-LC-" + uuid4().hex.upper(), "subject_type": subject_type,
                 "subject_id": subject_id, "zone_id": zone, "actor": principal.subject,
                 "recorded_at": datetime.now(timezone.utc).isoformat(), "action": payload.action,
                 "from_state": current["state"], "to_state": TARGET[payload.action], "assignee": assignee,
                 "resolution": payload.resolution if payload.action == "RESOLVE" else None,
                 "rationale": rationale, "evidence_signature": signature, "policy_version": POLICY,
                 "previous_hash": rows[-1][FIELDS.index("entry_hash")] if rows else "GENESIS"}
        entry["entry_hash"] = hashlib.sha256(json.dumps(entry, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        db.execute("INSERT INTO investigation_lifecycle VALUES (" + ",".join("?" * len(FIELDS)) + ")",  # nosec B608: constant placeholders; values are bound parameters
                   tuple(entry[f] for f in FIELDS))
    return view(subject_type, subject_id, principal)


def verify():
    from presentation.backend.app.review_integrity import verify_records
    with connect() as db:
        rows = db.execute("SELECT " + ",".join(FIELDS) + " FROM investigation_lifecycle ORDER BY rowid ASC").fetchall()  # nosec B608: constant columns
    return verify_records(rows, FIELDS)


@router.get("/api/v1/lifecycle/{subject_type}/{subject_id}")
def read_lifecycle(subject_type: str, subject_id: str, principal: Principal = Depends(current_principal)):
    return view(subject_type, subject_id, principal)


@router.post("/api/v1/lifecycle/{subject_type}/{subject_id}/transitions")
def record_transition(subject_type: str, subject_id: str, payload: TransitionInput,
                      principal: Principal = Depends(current_principal)):
    return transition(subject_type, subject_id, payload, principal)
