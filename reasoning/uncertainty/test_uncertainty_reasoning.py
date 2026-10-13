"""
DC-Guardian Reasoning
Contract tests for probabilistic (Bayesian) correlation.

No Neo4j, private data or network access is needed. Runs under pytest or as a
script (the form used by check_all.py):

    python reasoning/uncertainty/test_uncertainty_reasoning.py
"""

from __future__ import annotations

import copy
import json
import math
import sys
from itertools import combinations
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from reasoning.correlation.correlation_rules import (  # noqa: E402
    DEFAULT_CORRELATION_WINDOW_MINUTES,
    SUPPORTED_DOMAINS,
)
from reasoning.uncertainty.bayesian_correlation import (  # noqa: E402
    FACTORS,
    build_network,
    crisp_correlated,
    domain_mechanism_state,
    extract_factors,
    is_abnormal,
    load_knowledge_base,
    score_pair,
    topology_state,
)
from reasoning.uncertainty.bayesian_network import BayesianNetwork, Node  # noqa: E402
from reasoning.uncertainty import evaluate  # noqa: E402


KB = load_knowledge_base()


def event(event_id, domain, state, minute, **fields):
    return {"event_id": event_id, "domain": domain, "state": state,
            "timestamp": f"2026-10-01T10:{minute:02d}:00+00:00", **fields}


SENSOR_A = event("E1", "ENVIRONMENTAL", "HIGH_TEMPERATURE", 0,
                 zone_id="ZONE-A", source_class="ENVIRONMENTAL_SENSOR")
DRIVE_A = event("E2", "MAINTENANCE", "AT_RISK", 9, zone_id="ZONE-A",
                rack_id="RACK-A1", server_id="SRV-A1-01", failure_probability=0.82)
SSH_WEAK_A = event("E3", "CYBERSECURITY", "ANOMALY_CANDIDATE", 5, zone_id="ZONE-A",
                   rack_id="RACK-A1", server_id="SRV-A1-02")
PPE_A = event("E4", "SAFETY", "PPE_NON_COMPLIANT", 11, zone_id="ZONE-A", confidence=0.58)


# ============================================================
# Bayesian network engine
# ============================================================

def test_knowledge_base_cpts_are_valid_distributions():
    network = build_network(KB)
    assert set(network.nodes) == {"Related", *FACTORS}
    for factor in FACTORS:
        cpt = KB["network"]["cpts"][factor]
        for row in ("Yes", "No"):
            assert abs(sum(cpt[row]) - 1) < 1e-9
            assert len(cpt[row]) == len(cpt["states"])


def test_exact_inference_matches_hand_calculation():
    factors = {"TimeGap": "LE_15_MIN", "Topology": "SAME_ZONE",
               "DomainMechanism": "KNOWN", "EvidenceStrength": "BOTH_STRONG"}
    cpts, prior = KB["network"]["cpts"], KB["network"]["prior"]["Related"]
    yes, no = prior["Yes"], prior["No"]
    for factor, state in factors.items():
        index = cpts[factor]["states"].index(state)
        yes *= cpts[factor]["Yes"][index]
        no *= cpts[factor]["No"][index]
    posterior = build_network(KB).query("Related", factors)["Yes"]
    assert math.isclose(posterior, yes / (yes + no), rel_tol=1e-12)


def test_missing_evidence_is_marginalized_not_guessed():
    network = build_network(KB)
    assert math.isclose(network.query("Related")["Yes"], KB["network"]["prior"]["Related"]["Yes"])
    partial = network.query("Related", {"TimeGap": "LE_5_MIN"})["Yes"]
    assert 0 < partial < 1


def test_network_rejects_invalid_structure_and_cpts():
    root = Node("A", ("x", "y"), (), {(): (0.5, 0.5)})
    for bad in (
        [root, Node("B", ("x",), ("A",), {("x",): (1.0,)})],                      # missing parent row
        [root, Node("B", ("x", "y"), ("A",), {("x",): (0.7, 0.7), ("y",): (0.5, 0.5)})],  # row sum
        [Node("A", ("x",), ("B",), {("x",): (1.0,)}), Node("B", ("x",), ("A",), {("x",): (1.0,)})],  # cycle
    ):
        try:
            BayesianNetwork(bad)
        except ValueError:
            continue
        raise AssertionError("Invalid network was accepted.")


# ============================================================
# Knowledge and feature extraction
# ============================================================

def test_every_domain_pair_has_a_mechanism_level():
    for left, right in combinations(sorted(SUPPORTED_DOMAINS), 2):
        state = domain_mechanism_state({"domain": left}, {"domain": right}, KB)
        assert state in ("KNOWN", "POSSIBLE", "UNLIKELY")


def test_camera_evidence_resolves_to_zone_scope_only():
    face = event("F", "PHYSICAL_SECURITY", "RECOGNIZED", 0, zone_id="ZONE-A",
                 camera_id="CAM-A-01", authorization="UNAUTHORIZED")
    assert topology_state(face, SSH_WEAK_A, KB) == "SAME_ZONE"


def test_cooling_dependency_applies_only_to_infrastructure_domains():
    chiller = event("C", "ENVIRONMENTAL", "AIRFLOW_ANOMALY", 0, zone_id="ZONE-C",
                    source_class="ENVIRONMENTAL_SENSOR")
    face_c = event("F", "PHYSICAL_SECURITY", "UNKNOWN_PERSON", 0, zone_id="ZONE-C")
    assert topology_state(chiller, DRIVE_A, KB) == "DEPENDENCY"
    assert topology_state(face_c, SSH_WEAK_A, KB) == "UNRELATED"
    drive_b = {**DRIVE_A, "zone_id": "ZONE-B", "rack_id": "RACK-B1", "server_id": "SRV-B1-01"}
    assert topology_state(DRIVE_A, drive_b, KB) == "UNRELATED"


def test_ground_truth_labels_never_influence_the_score():
    labelled_left = {**SENSOR_A, "ground_truth_incident": "I1"}
    labelled_right = {**DRIVE_A, "ground_truth_incident": None}
    assert score_pair(SENSOR_A, DRIVE_A) == score_pair(labelled_left, labelled_right)


# ============================================================
# Scoring contract
# ============================================================

def test_explanation_multiplies_back_to_the_posterior():
    result = score_pair(SENSOR_A, DRIVE_A)
    prior = KB["network"]["prior"]["Related"]
    odds = prior["Yes"] / prior["No"]
    for contribution in result["contributions"]:
        odds *= contribution["likelihood_ratio"]
    assert math.isclose(odds / (1 + odds), result["probability_related"], abs_tol=2e-3)
    assert result["boundary"].startswith("Plausibility")


def test_strong_known_pair_scores_above_weak_unlikely_pair():
    strong = score_pair(SENSOR_A, DRIVE_A)
    weak = score_pair(SSH_WEAK_A, PPE_A)
    assert strong["correlated"] and not weak["correlated"]
    assert strong["probability_related"] > weak["probability_related"]


def test_invalid_pairs_are_rejected():
    normal = event("N", "ENVIRONMENTAL", "NORMAL", 1, zone_id="ZONE-A", source_class="ENVIRONMENTAL_SENSOR")
    naive_time = {**DRIVE_A, "timestamp": "2026-10-01T10:09:00"}
    invalid = (
        (SENSOR_A, SENSOR_A),                         # same event
        (SENSOR_A, {**SENSOR_A, "event_id": "X"}),    # same domain
        (normal, DRIVE_A),                            # not abnormal
        (SENSOR_A, naive_time),                       # timestamp without a time zone
    )
    for left, right in invalid:
        try:
            score_pair(left, right)
        except ValueError:
            continue
        raise AssertionError(f"Pair was accepted: {left['event_id']} + {right['event_id']}")


# ============================================================
# Crisp baseline fidelity
# ============================================================

def test_crisp_baseline_reproduces_the_frozen_rule():
    assert DEFAULT_CORRELATION_WINDOW_MINUTES == 15
    at_limit = {**DRIVE_A, "timestamp": "2026-10-01T10:15:00+00:00"}
    past_limit = {**DRIVE_A, "timestamp": "2026-10-01T10:16:00+00:00"}
    other_zone = {**DRIVE_A, "zone_id": "ZONE-B"}
    assert crisp_correlated(SENSOR_A, at_limit)
    assert not crisp_correlated(SENSOR_A, past_limit)
    assert not crisp_correlated(SENSOR_A, other_zone)
    assert not crisp_correlated(SENSOR_A, {**DRIVE_A, "domain": "ENVIRONMENTAL"})


# ============================================================
# Labelled scenarios and committed evaluation
# ============================================================

def test_labelled_scenarios_are_well_formed():
    scenarios = evaluate.load_scenarios()
    ids = [s["scenario_id"] for s in scenarios]
    assert len(ids) == len(set(ids))
    assert sum(s["split"] == "dev" for s in scenarios) == 16
    assert sum(s["split"] == "test" for s in scenarios) == 24
    window = KB["candidate_window_minutes"]
    for scenario in scenarios:
        event_ids = [e["event_id"] for e in scenario["events"]]
        assert len(event_ids) == len(set(event_ids))
        for e in scenario["events"]:
            assert is_abnormal(e), e["event_id"]
            assert "ground_truth_incident" in e
        first = scenario["events"][0]
        for e in scenario["events"]:
            assert evaluate.minutes_apart(first, e) <= window
        for left, right in evaluate.candidate_pairs(scenario):
            assert set(extract_factors(left, right)) == set(FACTORS)


def test_committed_evaluation_report_is_current():
    committed = json.loads((evaluate.RESULTS_DIR / "evaluation_results.json").read_text(encoding="utf-8"))
    fresh = json.loads(json.dumps(evaluate.evaluate()))
    assert committed["results"] == fresh["results"], "Re-run reasoning/uncertainty/evaluate.py and commit the results."
    assert committed["knowledge_base_version"] == KB["knowledge_base_version"]


def test_committed_v2_evaluation_reports_are_current():
    for name in ("v2", "v2-chatgpt"):
        path, suffix, _ = evaluate.SCENARIO_SETS[name]
        committed = json.loads((evaluate.RESULTS_DIR / f"evaluation_results{suffix}.json").read_text(encoding="utf-8"))
        fresh = json.loads(json.dumps(evaluate.evaluate(path)))
        assert committed["results"] == fresh["results"], f"Re-run evaluate.py --set {name} and commit the results."


def test_evaluation_does_not_modify_the_knowledge_base():
    before = copy.deepcopy(KB)
    evaluate.evaluate()
    assert load_knowledge_base() == before


# ============================================================
# Script runner
# ============================================================

def main() -> int:
    tests = [(name, fn) for name, fn in sorted(globals().items()) if name.startswith("test_") and callable(fn)]
    failures = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS  {name}")
        except Exception as exc:  # noqa: BLE001 - report every failing contract
            failures += 1
            print(f"FAIL  {name}: {exc!r}")
    print(f"\nUncertainty reasoning contracts: {len(tests) - failures} / {len(tests)} passing")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
