"""
DC-Guardian Reasoning
Evaluate crisp vs Bayesian correlation on the labelled scenarios.

Compares three ways of presenting abnormal Evidence to an operator:

1. Single-domain alerts: every abnormal event is its own alert.
2. Crisp rule: the frozen Reasoning rule (same zone, at most 15 minutes).
3. Bayesian model: P(Related) >= decision threshold from the knowledge base.

Metrics
- Pair level: precision, recall and F1 over all cross-domain pairs of
  abnormal events within each scenario. A pair is truly related when both
  events carry the same non-null ground-truth incident.
- Ranking: average precision and ROC-AUC of the Bayesian probability.
- Operator view: alerts shown (connected groups plus uncorrelated events),
  incidents fully linked into one group, and incidents linked cleanly
  (one group containing no unrelated event).
- Robustness: factor ablation and random perturbation of every
  conditional probability (CPT sensitivity).

The knowledge base is read as frozen; nothing here fits or tunes it.

Run from the repository root:
    python reasoning/uncertainty/evaluate.py
"""

from __future__ import annotations

import copy
import json
import math
import random
import statistics
import sys
from itertools import combinations
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from reasoning.uncertainty.bayesian_correlation import (  # noqa: E402
    FACTORS,
    build_network,
    crisp_correlated,
    extract_factors,
    is_abnormal,
    load_knowledge_base,
    minutes_apart,
)

HERE = Path(__file__).resolve().parent
SCENARIOS_PATH = HERE / "scenarios" / "labelled_scenarios.json"
RESULTS_DIR = HERE / "results"
SENSITIVITY_DRAWS = 200
SENSITIVITY_SIGMA = 0.3
SEED = 20261011


# ============================================================
# Data
# ============================================================

def load_scenarios(path: Path = SCENARIOS_PATH) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))["scenarios"]


def candidate_pairs(scenario: dict) -> list[tuple[dict, dict]]:
    events = [e for e in scenario["events"] if is_abnormal(e)]
    return [(a, b) for a, b in combinations(events, 2) if a["domain"] != b["domain"]]


def truly_related(left: dict, right: dict) -> bool:
    incident = left.get("ground_truth_incident")
    return incident is not None and incident == right.get("ground_truth_incident")


# ============================================================
# Metrics
# ============================================================

def prf(rows: list[dict], key: str) -> dict:
    tp = sum(1 for r in rows if r[key] and r["truth"])
    fp = sum(1 for r in rows if r[key] and not r["truth"])
    fn = sum(1 for r in rows if not r[key] and r["truth"])
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": round(precision, 3),
            "recall": round(recall, 3), "f1": round(f1, 3)}


def average_precision(rows: list[dict]) -> float:
    ranked = sorted(rows, key=lambda r: -r["probability"])
    positives = sum(r["truth"] for r in rows)
    hits, total = 0, 0.0
    for rank, row in enumerate(ranked, start=1):
        if row["truth"]:
            hits += 1
            total += hits / rank
    return round(total / positives, 3) if positives else 0.0


def roc_auc(rows: list[dict]) -> float:
    pos = [r["probability"] for r in rows if r["truth"]]
    neg = [r["probability"] for r in rows if not r["truth"]]
    if not pos or not neg:
        return 0.0
    wins = sum(1.0 if p > n else 0.5 if p == n else 0.0 for p in pos for n in neg)
    return round(wins / (len(pos) * len(neg)), 3)


def components(event_ids: list[str], links: list[tuple[str, str]]) -> list[set[str]]:
    parent = {e: e for e in event_ids}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in links:
        parent[find(a)] = find(b)
    groups = {}
    for e in event_ids:
        groups.setdefault(find(e), set()).add(e)
    return list(groups.values())


def operator_view(scenarios: list[dict], rows: list[dict], key: str) -> dict:
    alerts = linked = clean = incidents = 0
    for scenario in scenarios:
        abnormal = [e for e in scenario["events"] if is_abnormal(e)]
        ids = [e["event_id"] for e in abnormal]
        links = [tuple(r["event_ids"]) for r in rows if r["scenario_id"] == scenario["scenario_id"] and r[key]]
        groups = components(ids, links)
        alerts += len(groups)
        truth = {}
        for e in abnormal:
            if e["ground_truth_incident"] is not None:
                truth.setdefault(e["ground_truth_incident"], set()).add(e["event_id"])
        for members in truth.values():
            incidents += 1
            group = next(g for g in groups if next(iter(members)) in g)
            if members <= group:
                linked += 1
                if group == members:
                    clean += 1
    return {"alerts_shown": alerts, "incidents": incidents,
            "incidents_fully_linked": linked, "incidents_linked_cleanly": clean}


# ============================================================
# Scoring
# ============================================================

def score_rows(scenarios: list[dict], knowledge_base: dict, drop_factor: str | None = None) -> list[dict]:
    network = build_network(knowledge_base)
    threshold = knowledge_base["decision_threshold"]
    rows = []
    for scenario in scenarios:
        for left, right in candidate_pairs(scenario):
            factors = extract_factors(left, right, knowledge_base)
            evidence = {k: v for k, v in factors.items() if k != drop_factor}
            probability = network.query("Related", evidence)["Yes"]
            rows.append({
                "scenario_id": scenario["scenario_id"],
                "split": scenario["split"],
                "event_ids": [left["event_id"], right["event_id"]],
                "domains": [left["domain"], right["domain"]],
                "minutes_apart": round(minutes_apart(left, right), 1),
                "factors": factors,
                "truth": truly_related(left, right),
                "crisp": crisp_correlated(left, right),
                "probability": round(probability, 4),
                "bayesian": probability >= threshold,
            })
    return rows


def perturbed(knowledge_base: dict, rng: random.Random) -> dict:
    kb = copy.deepcopy(knowledge_base)

    def jitter(values):
        noisy = [v * math.exp(rng.gauss(0, SENSITIVITY_SIGMA)) for v in values]
        total = sum(noisy)
        return [v / total for v in noisy]

    prior = kb["network"]["prior"]["Related"]
    prior["Yes"], prior["No"] = jitter([prior["Yes"], prior["No"]])
    for cpt in kb["network"]["cpts"].values():
        cpt["Yes"] = jitter(cpt["Yes"])
        cpt["No"] = jitter(cpt["No"])
    return kb


def summarize(scenarios: list[dict], rows: list[dict]) -> dict:
    single_alerts = sum(1 for s in scenarios for e in s["events"] if is_abnormal(e))
    return {
        "scenarios": len(scenarios),
        "abnormal_events": single_alerts,
        "candidate_pairs": len(rows),
        "related_pairs": sum(r["truth"] for r in rows),
        "crisp": {**prf(rows, "crisp"), **operator_view(scenarios, rows, "crisp")},
        "bayesian": {**prf(rows, "bayesian"), **operator_view(scenarios, rows, "bayesian"),
                     "average_precision": average_precision(rows), "roc_auc": roc_auc(rows)},
        "single_domain": {"alerts_shown": single_alerts},
    }


def evaluate() -> dict:
    knowledge_base = load_knowledge_base()
    scenarios = load_scenarios()
    rows = score_rows(scenarios, knowledge_base)

    by_split = {}
    for split in ("dev", "test"):
        subset = [s for s in scenarios if s["split"] == split]
        by_split[split] = summarize(subset, [r for r in rows if r["split"] == split])
    by_split["all"] = summarize(scenarios, rows)

    test = [s for s in scenarios if s["split"] == "test"]
    ablation = {}
    for factor in FACTORS:
        ablated = [r for r in score_rows(test, knowledge_base, drop_factor=factor)]
        ablation[factor] = prf(ablated, "bayesian")["f1"]

    rng = random.Random(SEED)
    f1s, crisp_f1 = [], prf([r for r in rows if r["split"] == "test"], "crisp")["f1"]
    for _ in range(SENSITIVITY_DRAWS):
        f1s.append(prf(score_rows(test, perturbed(knowledge_base, rng)), "bayesian")["f1"])
    f1s.sort()
    sensitivity = {
        "draws": SENSITIVITY_DRAWS,
        "log_normal_sigma": SENSITIVITY_SIGMA,
        "test_f1_median": round(statistics.median(f1s), 3),
        "test_f1_p05": round(f1s[int(0.05 * len(f1s))], 3),
        "test_f1_p95": round(f1s[int(0.95 * len(f1s)) - 1], 3),
        "share_of_draws_beating_crisp": round(sum(f > crisp_f1 for f in f1s) / len(f1s), 3),
    }
    return {
        "knowledge_base_version": knowledge_base["knowledge_base_version"],
        "decision_threshold": knowledge_base["decision_threshold"],
        "results": by_split,
        "ablation_test_f1_without_factor": ablation,
        "sensitivity": sensitivity,
        "pairs": rows,
    }


# ============================================================
# Report
# ============================================================

def _pct(x: float) -> str:
    return f"{100 * x:.0f}%"


def write_report(result: dict) -> str:
    r = result["results"]
    lines = [
        "# Uncertainty reasoning evaluation",
        "",
        f"Knowledge base `{result['knowledge_base_version']}` (frozen), decision threshold {result['decision_threshold']}.",
        "Generated by `python reasoning/uncertainty/evaluate.py`. Do not edit by hand.",
        "",
        "## Pair-level correlation",
        "",
        "| Split | Pairs (related) | Method | Precision | Recall | F1 | TP | FP | FN |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for split in ("dev", "test", "all"):
        s = r[split]
        for method in ("crisp", "bayesian"):
            m = s[method]
            lines.append(f"| {split} | {s['candidate_pairs']} ({s['related_pairs']}) | {method} | "
                         f"{m['precision']:.3f} | {m['recall']:.3f} | {m['f1']:.3f} | {m['tp']} | {m['fp']} | {m['fn']} |")
    lines += ["", "Bayesian ranking quality (threshold-free):", "",
              "| Split | Average precision | ROC-AUC |", "|---|---:|---:|"]
    for split in ("dev", "test", "all"):
        b = r[split]["bayesian"]
        lines.append(f"| {split} | {b['average_precision']:.3f} | {b['roc_auc']:.3f} |")
    lines += ["", "## Operator view", "",
              "| Split | Incidents | Method | Alerts shown | Fully linked | Linked cleanly |",
              "|---|---:|---|---:|---:|---:|"]
    for split in ("dev", "test", "all"):
        s = r[split]
        lines.append(f"| {split} | {s['crisp']['incidents']} | single-domain | {s['single_domain']['alerts_shown']} | – | – |")
        for method in ("crisp", "bayesian"):
            m = s[method]
            lines.append(f"| {split} | {m['incidents']} | {method} | {m['alerts_shown']} | "
                         f"{m['incidents_fully_linked']} | {m['incidents_linked_cleanly']} |")
    lines += ["", "## Robustness (test split)", "",
              "Factor ablation: Bayesian F1 when one factor is left out (marginalized).", "",
              "| Factor removed | Test F1 |", "|---|---:|"]
    for factor, f1 in result["ablation_test_f1_without_factor"].items():
        lines.append(f"| {factor} | {f1:.3f} |")
    sens = result["sensitivity"]
    lines += ["", f"CPT sensitivity: {sens['draws']} draws, every probability multiplied by log-normal noise "
              f"(sigma {sens['log_normal_sigma']}) and renormalized. Test F1 median {sens['test_f1_median']:.3f}, "
              f"5th–95th percentile {sens['test_f1_p05']:.3f}–{sens['test_f1_p95']:.3f}; "
              f"{_pct(sens['share_of_draws_beating_crisp'])} of draws beat the crisp rule's test F1.", "",
              "## All candidate pairs", "",
              "| Scenario | Pair | Domains | Minutes | Topology | Mechanism | Strength | Truth | Crisp | P(Related) |",
              "|---|---|---|---:|---|---|---|---|---|---:|"]
    for p in result["pairs"]:
        f = p["factors"]
        short = "/".join(d[:4] for d in p["domains"])
        lines.append(f"| {p['scenario_id']} | {' + '.join(e.split('-')[-1] for e in p['event_ids'])} | {short} | "
                     f"{p['minutes_apart']:g} | {f['Topology']} | {f['DomainMechanism']} | {f['EvidenceStrength']} | "
                     f"{'related' if p['truth'] else '–'} | {'yes' if p['crisp'] else 'no'} | {p['probability']:.2f} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    result = evaluate()
    RESULTS_DIR.mkdir(exist_ok=True)
    (RESULTS_DIR / "evaluation_results.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (RESULTS_DIR / "evaluation_report.md").write_text(write_report(result), encoding="utf-8")
    t = result["results"]["test"]
    print(f"Test split: crisp F1 {t['crisp']['f1']:.3f} · Bayesian F1 {t['bayesian']['f1']:.3f} "
          f"· alerts single/crisp/Bayesian {t['single_domain']['alerts_shown']}/"
          f"{t['crisp']['alerts_shown']}/{t['bayesian']['alerts_shown']}")
    print(f"Report: {(RESULTS_DIR / 'evaluation_report.md').relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
