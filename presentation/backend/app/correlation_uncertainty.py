"""Research estimate P(Related) for live correlation pairs.

Scores each pair with the offline Bayesian correlation model
(reasoning/uncertainty, knowledge base DCG-UNCERTAINTY-KB-v1). Display only:
the deterministic pair rule stays the authoritative candidate filter, and the
probability never feeds correlation records, Decisions or severity.

Honest handling of missing inputs: a factor that cannot be observed for a live
event (for example PPE confidence) is marginalized by the network, never
guessed, and the response says which factor was left out. Pairs with an event
that is not abnormal are outside the model and are reported as not scored.
"""
import json
from functools import lru_cache
from pathlib import Path

from reasoning.uncertainty.bayesian_correlation import (
    build_network, extract_factors, is_abnormal, load_knowledge_base,
)

TOPOLOGY = Path(__file__).resolve().parents[3] / "shared" / "topology" / "data_center_topology.json"
MODEL_DOMAIN = {"ssh": "CYBERSECURITY", "maintenance": "MAINTENANCE", "environment": "ENVIRONMENTAL",
                "ppe": "SAFETY", "face": "PHYSICAL_SECURITY"}
STATUS = "RESEARCH_ESTIMATE_NOT_AUTHORITATIVE"
NOTE = ("Bayesian research estimate of whether both events belong to one incident (validated only on "
        "synthetic labelled scenarios). The deterministic rule decides correlation; this never changes "
        "correlation, Decisions or severity, and does not establish causation or identity.")


@lru_cache(maxsize=1)
def _model():
    knowledge_base = load_knowledge_base()
    return knowledge_base, build_network(knowledge_base)


@lru_cache(maxsize=1)
def server_racks():
    topology = json.loads(TOPOLOGY.read_text(encoding="utf-8"))
    return {server["server_id"]: rack["rack_id"]
            for zone in topology["data_center"]["zones"] for rack in zone.get("racks", [])
            for server in rack.get("servers", [])}


def model_event(node, when):
    """Translate a live correlation node into the model's event format."""
    attributes = node.get("attributes", {})
    event = {"event_id": f"{node['kind']}:{node['id']}", "domain": MODEL_DOMAIN[node["kind"]],
             "state": node["state"], "timestamp": when.isoformat(), "zone_id": node["zone_id"],
             "server_id": node.get("server_id"), "rack_id": server_racks().get(node.get("server_id") or ""),
             **attributes}
    if node["kind"] == "face" and node["state"] == "UNAUTHORIZED":
        # Live state folds the graph authorization check in; the model separates them.
        event.update(state="RECOGNIZED", authorization="UNAUTHORIZED")
    return event


def strength_observable(event):
    if event["domain"] == "SAFETY":
        return event.get("confidence") is not None
    if event["domain"] == "MAINTENANCE":
        return event.get("failure_probability") is not None
    if event["domain"] == "ENVIRONMENTAL":
        return event.get("source_class") is not None or event["state"] in ("SMOKE_DETECTED", "WATER_LEAK_DETECTED")
    return True


def score(left, right):
    if not left["times"] or not right["times"]:
        return {"status": "NOT_SCORED", "reason": "An event has no trustworthy time.", "note": NOTE}
    # Closest pair of observation times, as in the deterministic rule.
    tl, tr = min(((a, b) for a in left["times"] for b in right["times"]), key=lambda t: abs((t[0] - t[1]).total_seconds()))
    a, b = model_event(left, tl), model_event(right, tr)
    if not (is_abnormal(a) and is_abnormal(b)):
        return {"status": "NOT_SCORED", "reason": "One event is not abnormal; the model covers abnormal pairs only.",
                "note": NOTE}
    knowledge_base, network = _model()
    factors = extract_factors(a, b, knowledge_base)
    marginalized = []
    if not (strength_observable(a) and strength_observable(b)):
        factors.pop("EvidenceStrength")
        marginalized.append("EvidenceStrength")
    probability = network.query("Related", factors)["Yes"]
    cpts = knowledge_base["network"]["cpts"]
    contributions = []
    for factor, state in factors.items():
        index = cpts[factor]["states"].index(state)
        contributions.append({"factor": factor, "observed": state,
                              "likelihood_ratio": round(cpts[factor]["Yes"][index] / cpts[factor]["No"][index], 2)})
    return {"status": STATUS, "probability_related": round(probability, 3),
            "model_says_related": probability >= knowledge_base["decision_threshold"],
            "decision_threshold": knowledge_base["decision_threshold"],
            "prior": knowledge_base["network"]["prior"]["Related"]["Yes"],
            "factors": contributions, "marginalized_factors": marginalized,
            "knowledge_base_version": knowledge_base["knowledge_base_version"], "note": NOTE}


def score_pairs(pairs, nodes):
    by_key = {(n["kind"], n["id"]): n for n in nodes}
    for pair in pairs:
        left, right = (by_key.get((m["kind"], m["observation_id"])) for m in pair["members"])
        pair["uncertainty"] = (score(left, right) if left and right else
                               {"status": "NOT_SCORED", "reason": "Event details unavailable.", "note": NOTE})
    return pairs
