"""Provisional deterministic severity for unified correlation groups.

Policy DCG-UNIFIED-SEVERITY-PROVISIONAL-v1 applies the unchanged Decision
Rules v1 to the domains of the group's *active concern* members: detector-
abnormal or human-escalated, and not cleared by a human verdict. It never
inherits standalone or specialist severity, uses no model output, and is
recomputed from audited verdicts and frozen detector output, so it is
reproducible. Contextual grouping still establishes no causation or identity.
"""
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

def group_severity(members):
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
