"""Deterministic DC-GUARDIAN decision rules v1.

These rules classify validated pipeline evidence. They do not infer compromise,
identity, causation, or root cause and do not authorize autonomous action.
"""

from __future__ import annotations


SEVERITY_ORDER = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}


def _max_severity(*levels: str) -> str:
    return max(levels, key=lambda x: SEVERITY_ORDER[x])


def decide(pipeline: dict) -> dict:
    reasoning = pipeline["reasoning"]
    response = pipeline["response"]
    domains = set(reasoning.get("domains", []))
    boundaries = response.get("boundary_claims", {})
    triggered = []
    severity = "LOW"

    # Evidence-derived rules only.
    if reasoning.get("authorization_status") == "UNAUTHORIZED":
        severity = _max_severity(severity, "MEDIUM")
        triggered.append("UNAUTHORIZED_PHYSICAL_ACCESS_EVIDENCE")

    if "CYBERSECURITY" in domains:
        severity = _max_severity(severity, "MEDIUM")
        triggered.append("CYBERSECURITY_ANOMALY_EVIDENCE")

    if {"MAINTENANCE", "ENVIRONMENTAL"}.issubset(domains):
        severity = _max_severity(severity, "MEDIUM")
        triggered.append("CORRELATED_OPERATIONAL_RISK")

    if boundaries.get("confirmed_compromise") is True:
        severity = _max_severity(severity, "HIGH")
        triggered.append("CONFIRMED_COMPROMISE")

    # Multi-domain context increases review priority, but does not prove cause.
    if len(domains) >= 3:
        severity = _max_severity(severity, "HIGH")
        triggered.append("MULTI_DOMAIN_CORRELATED_RISK")

    grounding = (
        response.get("assessment", {}).get("grounding_status")
        or response.get("synthesis", {}).get("grounding_status")
    )
    if grounding == "INSUFFICIENT":
        incident_status = "EVIDENCE_REVIEW_REQUIRED"
    else:
        incident_status = "REVIEW_REQUIRED"

    return {
        "incident_status": incident_status,
        "severity": severity,
        "response_mode": "HUMAN_REVIEW",
        "escalation_required": severity == "HIGH",
        "autonomous_action_allowed": False,
        "decision_rules_triggered": triggered,
        "rationale": [
            "Decision is derived from deterministic evidence-state and domain rules.",
            "LLM grounding status informs evidence sufficiency but does not assign severity.",
            "No autonomous action is authorized by Decision Rules v1.",
        ],
        "protected_boundaries": {
            "identity_link_established": bool(
                boundaries.get("identity_link_established", False)
            ),
            "confirmed_compromise": bool(
                boundaries.get("confirmed_compromise", False)
            ),
            "causal_relationship_established": bool(
                boundaries.get("causal_relationship_established", False)
            ),
            "root_cause_established": bool(
                boundaries.get("root_cause_established", False)
            ),
        },
        "policy_version": "DCG-DECISION-v1",
    }
