"""
DC-Guardian Reasoning
Probabilistic cross-domain correlation (reasoning under uncertainty).

The frozen Reasoning rule is crisp: two abnormal events in different domains
correlate when they share a declared zone and are at most 15 minutes apart.
This module adds a Bayesian alternative that estimates

    P(Related | time gap, topology, domain mechanism, evidence strength)

for a pair of abnormal events, using the expert knowledge base in
`knowledge_base.json`. It explains every score as per-factor likelihood
ratios, so an operator can see why a pair scored high or low.

Boundaries (unchanged from the rest of DC-Guardian):
- The probability expresses how plausible a shared incident is under an
  expert model. It does not establish causation, identity, presence or
  compromise, and it never changes detector Evidence or Decision severity.
- The crisp rule remains the frozen baseline; this module runs beside it.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from reasoning.correlation.correlation_rules import (
    ABNORMAL_STATES,
    DEFAULT_CORRELATION_WINDOW_MINUTES,
    PHYSICAL_SECURITY_ABNORMAL_AUTHORIZATION,
    PHYSICAL_SECURITY_ABNORMAL_STATES,
)
from reasoning.uncertainty.bayesian_network import BayesianNetwork, Node


KNOWLEDGE_BASE_PATH = Path(__file__).resolve().parent / "knowledge_base.json"
FACTORS = ("TimeGap", "Topology", "DomainMechanism", "EvidenceStrength")
# Keys that hold labels for evaluation only. The model must never read them.
GROUND_TRUTH_KEYS = frozenset({"ground_truth_incident", "ground_truth"})


# ============================================================
# Knowledge base and network
# ============================================================

@lru_cache(maxsize=4)
def load_knowledge_base(path: str | None = None) -> dict:
    with open(path or KNOWLEDGE_BASE_PATH, encoding="utf-8") as handle:
        return json.load(handle)


def build_network(knowledge_base: dict) -> BayesianNetwork:
    spec = knowledge_base["network"]
    prior = spec["prior"]["Related"]
    nodes = [Node("Related", ("Yes", "No"), (), {(): (prior["Yes"], prior["No"])})]
    for factor in FACTORS:
        cpt = spec["cpts"][factor]
        nodes.append(Node(
            factor,
            tuple(cpt["states"]),
            ("Related",),
            {("Yes",): tuple(cpt["Yes"]), ("No",): tuple(cpt["No"])},
        ))
    return BayesianNetwork(nodes)


# ============================================================
# Event helpers
# ============================================================

def _features_only(event: dict) -> dict:
    return {k: v for k, v in event.items() if k not in GROUND_TRUTH_KEYS}


def parse_instant(value: str) -> datetime:
    """Timezone-aware UTC instant. Naive timestamps are rejected, never assumed UTC."""
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"Timestamp without a time zone: {value}")
    return parsed.astimezone(timezone.utc)


def is_abnormal(event: dict) -> bool:
    """Same eligibility as the frozen Reasoning correlation rule."""
    if event.get("state") in ABNORMAL_STATES:
        return True
    return event.get("domain") == "PHYSICAL_SECURITY" and (
        event.get("state") in PHYSICAL_SECURITY_ABNORMAL_STATES
        or event.get("authorization") in PHYSICAL_SECURITY_ABNORMAL_AUTHORIZATION
    )


def minutes_apart(left: dict, right: dict) -> float:
    delta = parse_instant(left["timestamp"]) - parse_instant(right["timestamp"])
    return abs(delta.total_seconds()) / 60.0


# ============================================================
# Feature extraction (one discrete state per factor)
# ============================================================

def time_gap_state(minutes: float) -> str:
    if minutes <= 5:
        return "LE_5_MIN"
    if minutes <= 15:
        return "LE_15_MIN"
    if minutes <= 60:
        return "LE_60_MIN"
    return "GT_60_MIN"


def _depends(provider: dict, dependent: dict, knowledge_base: dict) -> bool:
    for dep in knowledge_base["infrastructure_dependencies"]["dependencies"]:
        if (
            provider.get("zone_id") == dep["provider_zone"]
            and provider.get("domain") in dep["provider_domains"]
            and dependent.get("zone_id") in dep["dependent_zones"]
        ):
            return True
    return False


def topology_state(left: dict, right: dict, knowledge_base: dict) -> str:
    """Deepest truthful shared scope. Camera Evidence has zone scope only."""
    if left.get("server_id") and left.get("server_id") == right.get("server_id"):
        return "SAME_SERVER"
    if left.get("rack_id") and left.get("rack_id") == right.get("rack_id"):
        return "SAME_RACK"
    if left.get("zone_id") and left.get("zone_id") == right.get("zone_id"):
        return "SAME_ZONE"
    if _depends(left, right, knowledge_base) or _depends(right, left, knowledge_base):
        return "DEPENDENCY"
    return "UNRELATED"


def domain_mechanism_state(left: dict, right: dict, knowledge_base: dict) -> str:
    pair = {left["domain"], right["domain"]}
    for level in ("KNOWN", "POSSIBLE", "UNLIKELY"):
        for entry in knowledge_base["domain_mechanisms"][level]:
            if set(entry["pair"]) == pair:
                return level
    raise ValueError(f"Domain pair not covered by the knowledge base: {sorted(pair)}")


def event_strength(event: dict, knowledge_base: dict) -> str:
    rules = knowledge_base["evidence_strength_rules"]
    domain, state = event["domain"], event.get("state")
    if domain == "CYBERSECURITY":
        return "STRONG" if state in rules["CYBERSECURITY"]["STRONG_STATES"] else "WEAK"
    if domain == "MAINTENANCE":
        probability = event.get("failure_probability")
        threshold = rules["MAINTENANCE"]["STRONG_IF_PROBABILITY_AT_LEAST"]
        return "STRONG" if probability is not None and probability >= threshold else "WEAK"
    if domain == "ENVIRONMENTAL":
        env = rules["ENVIRONMENTAL"]
        if state in env["ALWAYS_STRONG_STATES"] or event.get("source_class") in env["STRONG_SOURCE_CLASSES"]:
            return "STRONG"
        return "WEAK"
    if domain == "PHYSICAL_SECURITY":
        return "STRONG" if event.get("authorization") in rules["PHYSICAL_SECURITY"]["STRONG_AUTHORIZATION"] else "WEAK"
    if domain == "SAFETY":
        confidence = event.get("confidence")
        threshold = rules["SAFETY"]["STRONG_IF_CONFIDENCE_AT_LEAST"]
        return "STRONG" if confidence is not None and confidence >= threshold else "WEAK"
    raise ValueError(f"Unsupported domain: {domain}")


def evidence_strength_state(left: dict, right: dict, knowledge_base: dict) -> str:
    strong = [event_strength(e, knowledge_base) == "STRONG" for e in (left, right)]
    if all(strong):
        return "BOTH_STRONG"
    if any(strong):
        return "MIXED"
    return "BOTH_WEAK"


def extract_factors(left: dict, right: dict, knowledge_base: dict | None = None) -> dict[str, str]:
    knowledge_base = knowledge_base or load_knowledge_base()
    left, right = _features_only(left), _features_only(right)
    return {
        "TimeGap": time_gap_state(minutes_apart(left, right)),
        "Topology": topology_state(left, right, knowledge_base),
        "DomainMechanism": domain_mechanism_state(left, right, knowledge_base),
        "EvidenceStrength": evidence_strength_state(left, right, knowledge_base),
    }


# ============================================================
# Scoring
# ============================================================

def _validate_pair(left: dict, right: dict) -> None:
    if left.get("event_id") == right.get("event_id"):
        raise ValueError("A pair needs two different events.")
    if left.get("domain") == right.get("domain"):
        raise ValueError("Cross-domain correlation needs two different domains.")
    if not (is_abnormal(left) and is_abnormal(right)):
        raise ValueError("Only abnormal events are correlation candidates.")


def score_pair(left: dict, right: dict, knowledge_base: dict | None = None, network: BayesianNetwork | None = None) -> dict:
    """Posterior probability that two abnormal events share an incident, with an explanation."""
    knowledge_base = knowledge_base or load_knowledge_base()
    network = network or build_network(knowledge_base)
    _validate_pair(left, right)
    factors = extract_factors(left, right, knowledge_base)
    posterior = network.query("Related", factors)["Yes"]

    cpts = knowledge_base["network"]["cpts"]
    contributions = []
    for factor, state in factors.items():
        index = cpts[factor]["states"].index(state)
        ratio = cpts[factor]["Yes"][index] / cpts[factor]["No"][index]
        contributions.append({
            "factor": factor,
            "observed": state,
            "likelihood_ratio": round(ratio, 3),
            "direction": "SUPPORTS" if ratio > 1 else ("OPPOSES" if ratio < 1 else "NEUTRAL"),
        })
    contributions.sort(key=lambda c: -abs(math.log(c["likelihood_ratio"])))

    threshold = knowledge_base["decision_threshold"]
    return {
        "event_ids": sorted([left["event_id"], right["event_id"]]),
        "probability_related": round(posterior, 4),
        "correlated": posterior >= threshold,
        "decision_threshold": threshold,
        "factors": factors,
        "contributions": contributions,
        "knowledge_base_version": knowledge_base["knowledge_base_version"],
        "boundary": "Plausibility of a shared incident under an expert model; not proof of causation, identity, presence or compromise.",
    }


# ============================================================
# Crisp baseline (frozen Reasoning rule, reproduced for comparison)
# ============================================================

def crisp_correlated(left: dict, right: dict) -> bool:
    """Both abnormal, different domains, same declared zone, at most 15 minutes apart."""
    left, right = _features_only(left), _features_only(right)
    return (
        left["domain"] != right["domain"]
        and is_abnormal(left)
        and is_abnormal(right)
        and bool(left.get("zone_id"))
        and left.get("zone_id") == right.get("zone_id")
        and minutes_apart(left, right) <= DEFAULT_CORRELATION_WINDOW_MINUTES
    )
