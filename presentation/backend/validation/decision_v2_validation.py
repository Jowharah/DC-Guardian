"""
Selection and validation of the DCG-DECISION-v2 group linkage rule on the
labelled uncertainty scenarios.

Protocol (fixed before any test-split result was seen):
1. Groups are formed per scenario exactly as the live system does (connected
   components of crisp-correlated abnormal events), 2+ events.
2. A group is *genuine* when all its events share one labelled incident.
3. On the dev split, each candidate in rules_v2.LINKAGE_RULES is scored by the
   difference in genuine share between escalated and non-escalated groups;
   the highest wins, ties go to the earlier (declared) candidate.
4. The winner is fixed as rules_v2.SELECTED_LINKAGE_RULE. Only then is the
   test split evaluated, once, with a scenario-level bootstrap CI, and compared
   with the provisional v1 group policy (3+ domains -> HIGH).

The scenarios carry relatedness labels written by the scenario author, not
severity labels: this measures whether escalation picks out groups that are one
real incident, not whether each level is "right".

    python presentation/backend/validation/decision_v2_validation.py

Writes results/decision_v2_validation.{md,json}.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from decision import rules_v2  # noqa: E402
from presentation.backend.app.unified_severity import group_severity_provisional_v1  # noqa: E402
from reasoning.uncertainty.bayesian_correlation import is_abnormal, load_knowledge_base  # noqa: E402
from reasoning.uncertainty.evaluate import components, load_scenarios, score_rows  # noqa: E402

RESULTS = Path(__file__).resolve().parent / "results"
SEED = 20261011
DRAWS = 2000


def groups(scenarios: list[dict], rows: list[dict]) -> list[dict]:
    result = []
    for scenario in scenarios:
        events = {e["event_id"]: e for e in scenario["events"] if is_abnormal(e)}
        links = [tuple(r["event_ids"]) for r in rows if r["scenario_id"] == scenario["scenario_id"] and r["crisp"]]
        for members in components(list(events), links):
            if len(members) < 2:
                continue
            group = [events[m] for m in sorted(members)]
            incidents = {e["ground_truth_incident"] for e in group}
            v1_view = [{"kind": e["domain"].lower(), "domain": e["domain"],
                        "effective_state": e.get("authorization") or e["state"], "active_concern": True} for e in group]
            result.append({"scenario_id": scenario["scenario_id"], "split": scenario["split"], "size": len(group),
                           "genuine": len(incidents) == 1 and None not in incidents, "events": group,
                           "v1_severity": group_severity_provisional_v1(v1_view)["severity"]})
    return result


def share(items: list[dict]) -> float | None:
    return sum(g["genuine"] for g in items) / len(items) if items else None


def separation(items: list[dict], rule: str) -> dict:
    up = [g for g in items if rules_v2.decide_group(g["events"], rule)["escalated"]]
    down = [g for g in items if not rules_v2.decide_group(g["events"], rule)["escalated"]]
    a, b = share(up), share(down)
    return {"escalated": len(up), "escalated_genuine": sum(g["genuine"] for g in up),
            "not_escalated": len(down), "not_escalated_genuine": sum(g["genuine"] for g in down),
            "difference": None if a is None or b is None else round(a - b, 3)}


def select(dev: list[dict]) -> tuple[str, dict]:
    scores = {rule: separation(dev, rule) for rule in rules_v2.LINKAGE_RULES}
    best = max(rules_v2.LINKAGE_RULES, key=lambda r: (scores[r]["difference"] if scores[r]["difference"] is not None else -9,
                                                       -list(rules_v2.LINKAGE_RULES).index(r)))
    return best, scores


def bootstrap(items: list[dict], rule: str, rng: random.Random) -> list[float]:
    by_scenario: dict[str, list[dict]] = {}
    for g in items:
        by_scenario.setdefault(g["scenario_id"], []).append(g)
    ids = sorted(by_scenario)
    values = []
    for _ in range(DRAWS):
        sample = [g for sid in (rng.choice(ids) for _ in ids) for g in by_scenario[sid]]
        d = separation(sample, rule)["difference"]
        if d is not None:
            values.append(d)
    values.sort()
    return [round(values[int(0.025 * (len(values) - 1))], 3), round(values[int(0.975 * (len(values) - 1))], 3)]


def level_table(items: list[dict], key) -> list[str]:
    lines = ["| Severity | Groups | Genuine | Share genuine |", "|---|---:|---:|---:|"]
    for level in ("HIGH", "MEDIUM", "LOW"):
        chosen = [g for g in items if key(g) == level]
        s = share(chosen)
        lines.append(f"| {level} | {len(chosen)} | {sum(g['genuine'] for g in chosen)} | {'–' if s is None else f'{s:.0%}'} |")
    return lines


def main() -> int:
    scenarios = load_scenarios()
    rows = score_rows(scenarios, load_knowledge_base())
    all_groups = groups(scenarios, rows)
    dev = [g for g in all_groups if g["split"] == "dev"]
    test = [g for g in all_groups if g["split"] == "test"]
    chosen, dev_scores = select(dev)
    print("Dev split selection:", chosen)
    for rule, s in dev_scores.items():
        print(f"  {rule}: {s}")
    if rules_v2.SELECTED_LINKAGE_RULE is None:
        print("SELECTED_LINKAGE_RULE is not fixed yet: set it in decision/rules_v2.py, then rerun. Test split not evaluated.")
        return 1
    if rules_v2.SELECTED_LINKAGE_RULE != chosen:
        print(f"Fixed rule {rules_v2.SELECTED_LINKAGE_RULE} differs from the dev selection {chosen}.")
        return 1

    rule = rules_v2.SELECTED_LINKAGE_RULE
    test_result = separation(test, rule)
    ci = bootstrap(test, rule, random.Random(SEED))
    v2_level = lambda g: rules_v2.decide_group(g["events"], rule)["severity"]
    report = {"policy": rules_v2.POLICY, "selected_rule": rule, "dev_scores": dev_scores,
              "test": {**test_result, "difference_ci95": ci, "groups": len(test),
                       "unified_groups_3plus": sum(g["size"] >= 3 for g in test)},
              "labels": "scenario author (no independent labelling round)", "bootstrap": {"draws": DRAWS, "unit": "scenario", "seed": SEED}}
    lines = ["# DCG-DECISION-v2 group rule — selection and validation", "",
             "Generated by `presentation/backend/validation/decision_v2_validation.py`. Groups are formed as in the live "
             "system (crisp-correlated abnormal events, 2+). A group is **genuine** when all its events belong to one "
             "labelled incident. Labels were written by the scenario author; the scenarios have no severity labels, so this "
             "tests whether escalation picks out real incidents, not whether each level is right.", "",
             "## 1. Selection on the dev split", "",
             "Criterion, declared before scoring: genuine share among escalated groups minus genuine share among the rest; "
             "ties go to the earlier candidate.", "",
             "| Candidate | Escalated (genuine) | Not escalated (genuine) | Difference |", "|---|---:|---:|---:|"]
    for name, s in dev_scores.items():
        lines.append(f"| {name}{' **(selected)**' if name == rule else ''} | {s['escalated']} ({s['escalated_genuine']}) | "
                     f"{s['not_escalated']} ({s['not_escalated_genuine']}) | {s['difference']} |")
    lines += ["", f"## 2. Held-out test split, evaluated once ({rule})", "",
              f"{len(test)} groups ({report['test']['unified_groups_3plus']} with 3+ events).", "",
              "| | Groups | Genuine | Share genuine |", "|---|---:|---:|---:|",
              f"| Escalated | {test_result['escalated']} | {test_result['escalated_genuine']} | "
              f"{test_result['escalated_genuine'] / max(1, test_result['escalated']):.0%} |",
              f"| Not escalated | {test_result['not_escalated']} | {test_result['not_escalated_genuine']} | "
              f"{test_result['not_escalated_genuine'] / max(1, test_result['not_escalated']):.0%} |", "",
              f"Difference {test_result['difference']}, 95% CI {ci[0]} to {ci[1]} (scenario bootstrap, {DRAWS} draws).", "",
              "### Severity levels on the test split", "", "**v2 (this rule)**", "", *level_table(test, v2_level), "",
              "**Provisional v1 group policy (3+ domains → HIGH), for comparison**", "",
              *level_table(test, lambda g: g["v1_severity"]), "",
              "## Caveats", "",
              "- Author labels: the rule was designed and tested against labels written by the same author, and the known-mechanism "
              "list mirrors the scenario design. Independent labels (the blind labelling pack) are needed before stronger claims.",
              "- Small sample: few test groups, so the interval is wide.",
              "- Single-event severities are an operator-approved policy and are not validated by these labels.", ""]
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "decision_v2_validation.md").write_text("\n".join(lines), encoding="utf-8")
    (RESULTS / "decision_v2_validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Test ({rule}): {test_result}  CI95 {ci}")
    print("Report: presentation/backend/validation/results/decision_v2_validation.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
