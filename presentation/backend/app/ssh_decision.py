"""Validated standalone SSH Decision adapter using unchanged Decision Rules v1."""
from decision.rules import decide

ELIGIBLE = frozenset({"HIGH_CONFIDENCE_ANOMALY","EXPLICIT_SECURITY_EVENT","ANOMALY_CANDIDATE"})

def decide_standalone_ssh(assessment: dict, correlation: dict, specialist: dict) -> dict:
    if assessment.get("evidence_state") not in ELIGIBLE:
        raise ValueError("SSH evidence state is not eligible for standalone Decision")
    if not assessment.get("source_ip") or not assessment.get("window_start"):
        raise ValueError("Missing original SSH source or time")
    if correlation.get("status") != "NO_CORRELATION":
        raise ValueError("Standalone Decision requires completed no-correlation result")
    if specialist.get("specialist_id") != "cybersecurity":
        raise ValueError("Validated Cybersecurity Specialist response required")
    if specialist.get("grounding_status") not in {"SUPPORTED","PARTIALLY_SUPPORTED","INSUFFICIENT"}:
        raise ValueError("Invalid grounding status")
    if specialist.get("confirmed_compromise") is not False:
        raise ValueError("Compromise cannot be inferred from SSH anomaly")
    pipeline = {
        "reasoning": {"domains": ["CYBERSECURITY"], "correlation": correlation,
                      "authorization_status": None},
        "response": {"assessment": {"grounding_status": specialist["grounding_status"]},
                     "boundary_claims": {"confirmed_compromise": False,
                                         "identity_link_established": False,
                                         "causal_relationship_established": False,
                                         "root_cause_established": False}},
    }
    result = decide(pipeline)
    if result["autonomous_action_allowed"] is not False:
        raise ValueError("Unsafe Decision contract")
    return result
