"""Consented grounded specialist evaluation for one Evidence record, any domain.

Same specialists, knowledge retrieval, grounding check and retry as unified
groups (unified_specialists.run_agents), with no contextual links. Sends the
allowlisted saved assessment (never images, enrollment or raw logs) plus the
human-verdict summary to OpenAI, so the operator must acknowledge that first.
Specialists never assign severity; Decisions come only from decision/rules*.py.
"""
import json
import logging
import sqlite3
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from presentation.backend.app.authentication import authorize, current_principal
from presentation.backend.app.authorization import Permission, Principal
from presentation.backend.app.incident_store import _db_path

router = APIRouter()
KINDS = ("ssh", "ppe", "face", "maintenance", "environment")


class SpecialistConsent(BaseModel):
    acknowledgment: bool = False


def storage():
    db = sqlite3.connect(_db_path(), timeout=15)
    db.execute("""CREATE TABLE IF NOT EXISTS single_specialist_results (
        kind TEXT NOT NULL, evidence_id TEXT NOT NULL, zone_id TEXT NOT NULL,
        evaluated_at TEXT NOT NULL, evaluated_by TEXT NOT NULL, signature TEXT NOT NULL,
        response_json TEXT NOT NULL, PRIMARY KEY (kind, evidence_id))""")
    return db


def authorized_evidence(kind, evidence_id, principal):
    """Domain permission, existence and zone checks, then the allowlisted assessment."""
    if kind not in KINDS:
        raise HTTPException(404, "Unsupported Evidence domain")
    from presentation.backend.app.investigator_tools import single_evidence_context
    from presentation.backend.app.unified_specialists import member_evidence
    zone = single_evidence_context(kind, evidence_id, principal)["zone_id"]
    return zone, member_evidence(kind, evidence_id, zone)


def signature(evidence):
    # Includes the human-verdict summary: a later verdict makes the result outdated.
    return json.dumps(evidence, sort_keys=True, default=str)


@router.get("/api/v1/evidence/{kind}/{evidence_id}/specialist")
def read_specialist(kind: str, evidence_id: str, principal: Principal = Depends(current_principal)):
    zone, evidence = authorized_evidence(kind, evidence_id, principal)
    with storage() as db:
        row = db.execute("SELECT evaluated_at,signature,response_json FROM single_specialist_results "
                         "WHERE kind=? AND evidence_id=?", (kind, evidence_id)).fetchone()
    if row is None:
        raise HTTPException(404, "No saved specialist assessment")
    return {"kind": kind, "evidence_id": evidence_id, "zone_id": zone, "evaluated_at": row[0],
            "evidence_changed_since": row[1] != signature(evidence),
            "specialists": json.loads(row[2]), "decision_severity": None}


@router.post("/api/v1/evidence/{kind}/{evidence_id}/specialist")
def evaluate_specialist(kind: str, evidence_id: str, consent: SpecialistConsent,
                        principal: Principal = Depends(current_principal)):
    zone, evidence = authorized_evidence(kind, evidence_id, principal)
    authorize(principal, Permission.SCENARIO_EXECUTE, zone)
    if not consent.acknowledgment:
        raise HTTPException(400, "Acknowledge that this Evidence record is sent to OpenAI")
    from presentation.backend.app.unified_specialists import run_agents
    try:
        results = run_agents({"zone_id": zone, "edges": []}, {kind: [evidence]})
    except HTTPException:
        raise
    except Exception as exc:
        logging.getLogger("dcg.response").warning("Single-event specialist failed for %s %s: %s: %s",
                                                  kind, evidence_id, type(exc).__name__, exc)
        raise HTTPException(503, "Specialist evaluation unavailable") from exc
    evaluated = datetime.now(timezone.utc).isoformat()
    with storage() as db:
        db.execute("""INSERT INTO single_specialist_results VALUES (?,?,?,?,?,?,?)
            ON CONFLICT(kind,evidence_id) DO UPDATE SET zone_id=excluded.zone_id,
            evaluated_at=excluded.evaluated_at, evaluated_by=excluded.evaluated_by,
            signature=excluded.signature, response_json=excluded.response_json""",
                   (kind, evidence_id, zone, evaluated, principal.subject, signature(evidence), json.dumps(results)))
    return {"kind": kind, "evidence_id": evidence_id, "zone_id": zone, "evaluated_at": evaluated,
            "evidence_changed_since": False, "specialists": results, "decision_severity": None}
