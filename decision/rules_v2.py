"""Deterministic DC-GUARDIAN decision rules v2 (DCG-DECISION-v2).

Adds what v1 lacks, without changing v1 (decision/rules.py stays the policy of
every Decision already saved):

1. Single-event severities for every domain. A conservative operator-approved
   policy (2026-10-11), not derived from data: every result still goes to
   human review.
2. A severity for correlated groups. The group starts at its most severe member
   and is raised one level only when the members show a linkage mechanism (see
   LINKAGE_RULES). Co-occurrence alone, however many domains, never escalates.
   The linkage rule was chosen on the dev split of the labelled scenarios and
   evaluated once on the held-out test split
   (presentation/backend/validation/decision_v2_validation.py). Those labels
   were written by the scenario author, so the result is "validated on author
   labels only" (the independent labelling round was dropped).

Events use the scenario/Bayesian event shape: domain, state, timestamp and,
where known, authorization, server_id and rack_id. Nothing here infers
compromise, identity, causation or root cause, and no autonomous action is
authorized.
"""

from __future__ import annotations

from datetime import datetime
from itertools import combinations

POLICY = "DCG-DECISION-v2"
SEVERITY_ORDER = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}
LEVELS = ("LOW", "MEDIUM", "HIGH")
# 2026-10-21: the independent labelling round was dropped (time); the result rests on the author's labels only.
VALIDATION_STATUS = "VALIDATED_ON_AUTHOR_LABELS_ONLY"

# --- 1. Single events (policy) ------------------------------------------------
SINGLE_EVENT_RULES = {
    ("CYBERSECURITY", "EXPLICIT_SECURITY_EVENT"): ("MEDIUM", "CYBERSECURITY_ANOMALY_EVIDENCE"),
    ("CYBERSECURITY", "HIGH_CONFIDENCE_ANOMALY"): ("MEDIUM", "CYBERSECURITY_ANOMALY_EVIDENCE"),
    ("CYBERSECURITY", "ANOMALY_CANDIDATE"): ("MEDIUM", "CYBERSECURITY_ANOMALY_EVIDENCE"),
    ("CYBERSECURITY", "ANOMALOUS"): ("MEDIUM", "CYBERSECURITY_ANOMALY_EVIDENCE"),  # human verdict vocabulary
    ("PHYSICAL_SECURITY", "UNKNOWN_PERSON"): ("MEDIUM", "UNKNOWN_PERSON_IN_ZONE"),
    ("SAFETY", "PPE_NON_COMPLIANT"): ("LOW", "PPE_NON_COMPLIANCE"),
    ("SAFETY", "NON_COMPLIANT"): ("LOW", "PPE_NON_COMPLIANCE"),
    ("MAINTENANCE", "AT_RISK"): ("LOW", "DRIVE_FAILURE_RISK"),
}
# Every abnormal environmental state is LOW in this conservative policy.
ENVIRONMENTAL_NORMAL = {"NORMAL", "NO_ANOMALY", None}
UNAUTHORIZED_RULE = ("MEDIUM", "UNAUTHORIZED_PHYSICAL_ACCESS_EVIDENCE")


def event_severity(event: dict) -> tuple[str | None, list[str]]:
    """(severity, rules) for one event; (None, []) when it is not abnormal."""
    levels, rules = [], []
    if event.get("authorization") == "UNAUTHORIZED" or (
            event["domain"] == "PHYSICAL_SECURITY" and event.get("state") == "UNAUTHORIZED"):
        levels.append(UNAUTHORIZED_RULE[0]); rules.append(UNAUTHORIZED_RULE[1])
    hit = SINGLE_EVENT_RULES.get((event["domain"], event.get("state")))
    if hit:
        levels.append(hit[0]); rules.append(hit[1])
    elif event["domain"] == "ENVIRONMENTAL" and event.get("state") not in ENVIRONMENTAL_NORMAL:
        levels.append("LOW"); rules.append("ENVIRONMENTAL_CONDITION")
    if not levels:
        return None, []
    return max(levels, key=SEVERITY_ORDER.get), rules


# --- 2. Groups ------------------------------------------------------------------
# Domain pairs with a known mechanism, frozen from the uncertainty knowledge base
# (DCG-UNCERTAINTY-KB-v1, domain_mechanisms.KNOWN); a test checks they still match.
KNOWN_MECHANISMS = frozenset({
    frozenset({"ENVIRONMENTAL", "MAINTENANCE"}),
    frozenset({"CYBERSECURITY", "PHYSICAL_SECURITY"}),
    frozenset({"PHYSICAL_SECURITY", "SAFETY"}),
})


def _when(event: dict) -> datetime:
    return datetime.fromisoformat(str(event["timestamp"]).replace("Z", "+00:00"))


def linkage_signals(events: list[dict]) -> dict:
    """Observable signs that a group's members belong together (no causal claim)."""
    servers = [e["server_id"] for e in events if e.get("server_id")]
    racks = [e["rack_id"] for e in events if e.get("rack_id")]
    domains = {e["domain"] for e in events}
    unauthorized = any(e.get("authorization") == "UNAUTHORIZED" or e.get("state") == "UNAUTHORIZED"
                       for e in events if e["domain"] == "PHYSICAL_SECURITY")
    times = [_when(e) for e in events if e.get("timestamp")]
    return {
        "same_server": len(servers) != len(set(servers)),
        "same_rack": len(racks) != len(set(racks)),
        "unauthorized_with_cyber": unauthorized and "CYBERSECURITY" in domains,
        "known_mechanism": any(frozenset(p) in KNOWN_MECHANISMS for p in combinations(sorted(domains), 2)),
        "time_spread_minutes": round((max(times) - min(times)).total_seconds() / 60, 1) if times else None,
    }


def _mechanism(s: dict) -> bool:
    return s["same_server"] or s["unauthorized_with_cyber"] or s["known_mechanism"]


def _within(s: dict, minutes: float) -> bool:
    return s["time_spread_minutes"] is not None and s["time_spread_minutes"] <= minutes


# Candidates declared before the dev-split comparison; each requires a mechanism.
# A time-only rule is deliberately excluded: it would encode how the scenarios
# were written rather than a data-center mechanism.
LINKAGE_RULES = {
    "L1_SERVER_OR_UNAUTHORIZED_CYBER": lambda s: s["same_server"] or s["unauthorized_with_cyber"],
    "L2_KNOWN_MECHANISM_WITHIN_10_MIN": lambda s: s["known_mechanism"] and _within(s, 10),
    "L3_ANY_MECHANISM_WITHIN_10_MIN": lambda s: _mechanism(s) and _within(s, 10),
    "L4_ANY_MECHANISM_WITHIN_5_MIN": lambda s: _mechanism(s) and _within(s, 5),
}
SELECTED_LINKAGE_RULE = "L2_KNOWN_MECHANISM_WITHIN_10_MIN"  # dev-split selection, 2026-10-11


def decide_group(events: list[dict], rule: str | None = None) -> dict:
    """Severity for 2+ correlated events: most severe member, +1 level on linkage."""
    rule = rule or SELECTED_LINKAGE_RULE
    scored = [(e, *event_severity(e)) for e in events]
    concern = [(e, level, rules) for e, level, rules in scored if level]
    if not concern:
        return {"severity": None, "base_severity": None, "escalated": False, "rules_triggered": [],
                "linkage": None, "linkage_rule": rule, "policy_version": POLICY}
    base = max((level for _, level, _ in concern), key=SEVERITY_ORDER.get)
    signals = linkage_signals([e for e, _, _ in concern])
    linked = len(concern) >= 2 and LINKAGE_RULES[rule](signals)
    severity = LEVELS[min(len(LEVELS) - 1, SEVERITY_ORDER[base])] if linked else base
    triggered = sorted({r for _, _, rules in concern for r in rules})
    if linked:
        triggered.append("LINKED_GROUP_ESCALATION")
    return {"severity": severity, "base_severity": base, "escalated": linked,
            "rules_triggered": triggered, "linkage": signals, "linkage_rule": rule,
            "policy_version": POLICY}


def decision_record(severity: str | None, rules: list[str], *, group: bool) -> dict:
    """The Decision contract shared with v1 (always human review, never autonomous)."""
    return {
        "incident_status": "REVIEW_REQUIRED" if severity else "NO_ACTIVE_CONCERN",
        "severity": severity,
        "response_mode": "HUMAN_REVIEW",
        "escalation_required": severity == "HIGH",
        "autonomous_action_allowed": False,
        "decision_rules_triggered": rules,
        "rationale": [
            "Decision is derived from deterministic evidence-state and linkage rules.",
            "Correlation is contextual: linkage raises review priority, it does not prove cause."
            if group else "Single-event severity is an operator-approved policy, not derived from data.",
            "No autonomous action is authorized by Decision Rules v2.",
        ],
        "protected_boundaries": {"identity_link_established": False, "confirmed_compromise": False,
                                 "causal_relationship_established": False, "root_cause_established": False},
        "policy_version": POLICY,
        "validation_status": VALIDATION_STATUS if group else "POLICY_NOT_DATA_VALIDATED",
    }
