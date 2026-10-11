"""DCG-DECISION-v2 single-event Decisions for PPE, Face, Maintenance and Environment.

Computed on read from frozen detector output and the audited human verdicts,
so the result is reproducible and always reflects the latest verdict:
a cleared event has no severity, an overridden one uses the human status.
SSH keeps its saved Decision v1 record (same MEDIUM policy). Severity comes
only from decision/rules_v2.py; no model output is used.
"""
from fastapi import APIRouter, Depends

from decision import rules_v2
from presentation.backend.app.authentication import current_principal
from presentation.backend.app.authorization import Principal

router = APIRouter()
KINDS = ("ppe", "face", "maintenance", "environment")


def latest_verdicts():
    from presentation.backend.app.evidence_review import effective, rows
    grouped = {}
    for record in rows():
        grouped.setdefault((record["kind"], record["evidence_id"]), []).append(record)
    return {key: effective(key[0], records) for key, records in grouped.items()}


def node_decision(node, verdict=None):
    """v2 Decision for one live correlation node, after any human verdict."""
    from presentation.backend.app.correlation_uncertainty import MODEL_DOMAIN
    if verdict and verdict["verdict"] == "OVERRIDDEN" and verdict["abnormal"] is False:
        record = rules_v2.decision_record(None, ["INPUT_CLEARED_BY_HUMAN_VERDICT"], group=False)
        return {**record, "input_source": "HUMAN_OVERRIDE", "effective_state": verdict["effective_status"]}
    overridden = bool(verdict and verdict["verdict"] == "OVERRIDDEN")
    state = verdict["effective_status"] if overridden else node["state"]
    severity, rules = rules_v2.event_severity({"domain": MODEL_DOMAIN[node["kind"]], "state": state})
    record = rules_v2.decision_record(severity, rules, group=False)
    return {**record, "input_source": "HUMAN_OVERRIDE" if overridden else "DETECTOR", "effective_state": state}


@router.get("/api/v1/decisions/standalone")
def standalone_decisions(principal: Principal = Depends(current_principal)):
    from presentation.backend.app.correlation_pairs import load_nodes
    from presentation.backend.app.evidence_review import overrides
    verdicts = latest_verdicts()
    nodes = [n for n in load_nodes(principal, overrides()) if n["kind"] in KINDS]
    return [{"kind": n["kind"], "evidence_id": n["id"], "zone_id": n["zone_id"],
             "decision": node_decision(n, verdicts.get((n["kind"], n["id"])))} for n in nodes]
