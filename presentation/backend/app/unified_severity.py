"""Deterministic severity for unified correlation groups.

Current policy: DCG-DECISION-v2 (decision/rules_v2.py), via group_decision():
the group starts at its most severe active-concern member and is raised one
level when the members show a linkage mechanism (known domain mechanism, all
within 10 minutes). Validated on the author's labels only (no independent labelling round).

Historical policy, kept for the earlier validation report:

Policy DCG-UNIFIED-SEVERITY-PROVISIONAL-v1 applies the unchanged Decision
Rules v1 to the domains of the group's *active concern* members: detector-
abnormal or human-escalated, and not cleared by a human verdict. It never
inherits standalone or specialist severity, uses no model output, and is
recomputed from audited verdicts and frozen detector output, so it is
reproducible. Contextual grouping still establishes no causation or identity.
"""
from datetime import datetime, timezone

from decision.rules import decide

POLICY="DCG-UNIFIED-SEVERITY-PROVISIONAL-v1"

def members_with_review(group,states,human,summaries):
    """Per-member detector state, human verdict and concern flags."""
    from presentation.backend.app.unified_correlations import DOMAIN
    result=[]
    for ref in group["evidence"]:
        key=(ref["kind"],ref["observation_id"])
        state=states.get(key,{})
        verdict=summaries.get(key)
        override=human.get(key)
        cleared=override is False
        result.append({"kind":ref["kind"],"observation_id":ref["observation_id"],
            "domain":DOMAIN[ref["kind"]],"detector_state":state.get("state"),
            "detector_abnormal":bool(state.get("detector_abnormal")),
            "effective_state":verdict["effective_status"] if verdict and override is not None else state.get("state"),
            "human_review":verdict,"cleared_by_human":cleared,
            "active_concern":not cleared and (override is True or bool(state.get("detector_abnormal")))})
    return result

def group_severity_provisional_v1(members):
    active=[m for m in members if m["active_concern"]]
    domains=sorted({m["domain"] for m in active})
    if not domains:
        return {"severity":None,"rules_triggered":[],"active_concern_domains":[],
                "policy":POLICY,"provisional":True}
    unauthorized=any(m["kind"]=="face" and m["effective_state"]=="UNAUTHORIZED" for m in active)
    result=decide({"reasoning":{"domains":domains,"correlation":{},
                                "authorization_status":"UNAUTHORIZED" if unauthorized else None},
                   "response":{"assessment":{},"boundary_claims":{
                       "confirmed_compromise":False,"identity_link_established":False,
                       "causal_relationship_established":False,"root_cause_established":False}}})
    return {"severity":result["severity"],"rules_triggered":result["decision_rules_triggered"],
            "active_concern_domains":domains,"policy":POLICY,"provisional":True}


def _closest(times, anchor):
    return min(times, key=lambda t: abs((t - anchor).total_seconds()))

def member_events(members, nodes_by_key):
    """Scenario-format events for active-concern members (the shape rules_v2 uses).

    Each member contributes the observation time that keeps the group tightest,
    as the pair rule picks the closest pair of times.
    """
    from presentation.backend.app.correlation_uncertainty import model_event
    active = [(m, nodes_by_key.get((m["kind"], m["observation_id"]))) for m in members if m["active_concern"]]
    active = [(m, n) for m, n in active if n is not None]
    anchors = [t for _, n in active for t in n["times"]]
    best = None
    for anchor in anchors:
        chosen = [_closest(n["times"], anchor) if n["times"] else None for _, n in active]
        known = [t for t in chosen if t is not None]
        spread = (max(known) - min(known)).total_seconds() if known else 0
        if best is None or spread < best[0]:
            best = (spread, chosen)
    times = best[1] if best else [None] * len(active)
    events = []
    for (m, n), when in zip(active, times):
        event = model_event(n, when) if when else {**model_event(n, datetime.now(timezone.utc)), "timestamp": None}
        if when is None:
            event.pop("timestamp")
        state = m["effective_state"]
        if m["kind"] == "face" and state == "UNAUTHORIZED":
            event.update(state="RECOGNIZED", authorization="UNAUTHORIZED")
        else:
            event["state"] = state
            if m["kind"] == "face":
                event.pop("authorization", None)
        events.append(event)
    return events

def group_severity(members, nodes_by_key):
    """DCG-DECISION-v2 group Decision for one unified group."""
    from decision import rules_v2
    active = [m for m in members if m["active_concern"]]
    domains = sorted({m["domain"] for m in active})
    result = rules_v2.decide_group(member_events(members, nodes_by_key))
    record = rules_v2.decision_record(result["severity"], result["rules_triggered"], group=True)
    return {"severity": result["severity"], "rules_triggered": result["rules_triggered"],
            "active_concern_domains": domains, "policy": rules_v2.POLICY, "provisional": False,
            "base_severity": result["base_severity"], "escalated": result["escalated"],
            "linkage": result["linkage"], "linkage_rule": result["linkage_rule"],
            "validation_status": rules_v2.VALIDATION_STATUS, "decision": record}
