"""Grounded unified specialist evaluations; no unified Decision authority."""
import json
import sqlite3
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from presentation.backend.app.authentication import current_principal, authorize
from presentation.backend.app.authorization import Principal, Permission
from presentation.backend.app.incident_store import _db_path
from presentation.backend.app.unified_correlations import unified_correlations
from presentation.backend.app.unified_graph import unified_graph, REQUIRED
from presentation.backend.app import face_observations, ppe_observations
from presentation.backend.app.ssh_publication import connect as ssh_connect

router = APIRouter()

def storage():
    db = sqlite3.connect(_db_path(), timeout=15)
    db.execute("""CREATE TABLE IF NOT EXISTS unified_specialist_results (
        group_id TEXT PRIMARY KEY, evaluated_at TEXT NOT NULL,
        signature TEXT NOT NULL, response_json TEXT NOT NULL)""")
    return db

def find_group(group_id, principal):
    for permission in REQUIRED:
        authorize(principal, permission)
    group = next((g for g in unified_correlations(principal) if g["id"] == group_id), None)
    if group is None:
        raise HTTPException(404, "Unified correlation group not found")
    for permission in REQUIRED:
        authorize(principal, permission, group["zone_id"])
    return group

def fingerprint(group):
    return json.dumps({"evidence": group["evidence"], "edges": group["edges"]}, sort_keys=True)

def source_evidence(group):
    result = {}
    for ref in group["evidence"]:
        kind, oid = ref["kind"], ref["observation_id"]
        if kind == "face":
            record = face_observations.get(oid)
            if record is None:
                raise HTTPException(409, "Face evidence unavailable")
            a = record["assessment"]
            result["face"] = {k: a.get(k) for k in ("recognition_status", "person_id", "similarity")}
            from presentation.backend.app.face_zone_authorization import assess as assess_zone
            result["face"]["zone_authorization"] = assess_zone(
                a.get("person_id") if a.get("recognition_status") == "RECOGNIZED" else "",
                group["zone_id"])
        elif kind == "ppe":
            record = ppe_observations.get_observation(oid)
            if record is None:
                raise HTTPException(409, "PPE evidence unavailable")
            a = record["assessment"]
            result["ppe"] = {k: a.get(k) for k in ("overall_status", "people", "required_ppe")}
        elif kind == "ssh":
            with ssh_connect() as db:
                row = db.execute("SELECT payload FROM ssh_published_evidence WHERE event_id=?", (oid,)).fetchone()
            if row is None:
                raise HTTPException(409, "SSH evidence unavailable")
            a = json.loads(row[0])
            result["ssh"] = {k: a.get(k) for k in ("evidence_state", "source_ip", "window_start", "detector_votes", "usernames", "evidence")}
    return result

def run_agents(group, evidence):
    from response.rag.knowledge_eligibility import evaluate_knowledge_eligibility
    from response.rag.retrieve import retrieve_knowledge
    from response.agents.providers.openai_provider import OpenAIResponsesProvider
    from response.agents.specialists.base import SpecialistRequest
    from response.agents.specialists.cybersecurity import CybersecuritySpecialist
    from response.agents.specialists.physical_security import PhysicalSecuritySpecialist
    specs = []
    provider = OpenAIResponsesProvider()
    if "ssh" in evidence:
        specs.append(("cybersecurity", CybersecuritySpecialist(provider), ["CYBERSECURITY"], {"ssh": evidence["ssh"]}))
    if "face" in evidence or "ppe" in evidence:
        domains = [d for d, key in (("PHYSICAL_SECURITY", "face"), ("SAFETY", "ppe")) if key in evidence]
        specs.append(("physical_security", PhysicalSecuritySpecialist(provider), domains,
                      {k: evidence[k] for k in ("face", "ppe") if k in evidence}))
    if not specs:
        raise HTTPException(409, "No unified specialist available for these domains")
    results = {}
    for name, agent, domains, sources in specs:
        if not evaluate_knowledge_eligibility(domains=domains)["eligible"]:
            raise HTTPException(503, "Approved specialist knowledge unavailable")
        knowledge = retrieve_knowledge("Data center " + name + " evidence review",
                                       domains=domains, top_k=4, ranking="controlled", abstain=False)
        if not knowledge:
            raise HTTPException(503, "Approved specialist knowledge unavailable")
        assessment = agent.assess(SpecialistRequest(
            incident_evidence={"zone_id": group["zone_id"], "domains": domains,
                               "source_evidence": sources,
                               "contextual_links": [{"type": e["type"], "source_id": e["source_id"]} for e in group["edges"]],
                               "identity_link_established": False,
                               "causal_relationship_established": False,
                               "time_provenance": "CONTROLLED_CONTEXT_MAY_BE_OPERATOR_DECLARED_UNVERIFIED"},
            retrieved_evidence=knowledge,
            task="Describe supported source findings and limits only. Do not attribute SSH activity to a recognized person, assert PPE identity linkage, infer causation, or assign severity.",
            domains=tuple(domains)))
        if assessment.get("grounding_status") not in ("SUPPORTED", "PARTIALLY_SUPPORTED", "INSUFFICIENT"):
            raise HTTPException(503, "Invalid specialist response contract")
        for field in ("supported_findings", "recommended_considerations", "limitations"):
            values = assessment.get(field, [])
            if isinstance(values, list):
                assessment[field] = [v.strip() for v in values if isinstance(v, str) and v.strip()]
        results[name] = assessment
    return results

@router.get("/api/v1/correlations/unified/{group_id}/specialists")
def read_specialists(group_id: str, principal: Principal = Depends(current_principal)):
    group = find_group(group_id, principal)
    with storage() as db:
        row = db.execute("SELECT evaluated_at,signature,response_json FROM unified_specialist_results WHERE group_id=?", (group_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "No saved unified specialist assessment")
    if row[1] != fingerprint(group):
        raise HTTPException(409, "Correlation evidence changed; re-evaluation required")
    return {"group_id": group_id, "evaluated_at": row[0], "specialists": json.loads(row[2]),
            "decision": None, "decision_severity": None}

@router.post("/api/v1/correlations/unified/{group_id}/specialists")
def evaluate_specialists(group_id: str, principal: Principal = Depends(current_principal)):
    group = find_group(group_id, principal)
    authorize(principal, Permission.SCENARIO_EXECUTE, group["zone_id"])
    unified_graph(group_id, principal)
    evidence = source_evidence(group)
    try:
        results = run_agents(group, evidence)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(503, "Unified specialist evaluation unavailable") from exc
    evaluated = datetime.now(timezone.utc).isoformat()
    with storage() as db:
        db.execute("""INSERT INTO unified_specialist_results VALUES (?,?,?,?)
          ON CONFLICT(group_id) DO UPDATE SET evaluated_at=excluded.evaluated_at,
          signature=excluded.signature,response_json=excluded.response_json""",
          (group_id, evaluated, fingerprint(group), json.dumps(results)))
    return {"group_id": group_id, "evaluated_at": evaluated, "specialists": results,
            "decision": None, "decision_severity": None}
