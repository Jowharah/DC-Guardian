"""
DC-GUARDIAN against isolated single-domain monitoring, on the labelled scenarios.

Research question (proposal, 2026): does combining multi-domain evidence with
graph context and deterministic rules improve incident correlation and
prioritisation compared with isolated single-domain monitoring?

Protocol (fixed before any result was computed, 2026-10-13):
1. Isolated monitoring: every abnormal event is its own alert, with the
   DCG-DECISION-v2 single-event severity. Using the same single-event policy
   means the only difference between the two systems is correlation.
2. DC-GUARDIAN: crisp-correlated abnormal events form one alert per connected
   group (as the live system does), with the v2 group severity; uncorrelated
   events keep their single-event severity.
3. Each system's alerts form one review queue per split, sorted by severity.
   Within a level the order is random, averaged over TIE_ORDERS orders.
   An alert is *relevant* when it contains an event of a labelled incident.
4. Metrics: alerts shown, noise alerts (no incident event), incidents seen in one
   alert, precision of the top severity level, average precision of the queue,
   alerts reviewed until every incident has been seen at least once and until
   every incident event has been seen.
5. Primary result: the held-out test split, with a 95% interval for the
   difference (bootstrap over whole scenarios). The dev split, on which the v2
   linkage rule was selected, is shown for reference only.

Labels were written by the scenario author (no independent labelling round; dropped 2026-10-21).

    python presentation/backend/validation/baseline_comparison.py                   # v1 (published)
    python presentation/backend/validation/baseline_comparison.py --set v2          # operator's blind relabel
    python presentation/backend/validation/baseline_comparison.py --set v2-chatgpt  # ChatGPT labels (sensitivity)

Writes results/baseline_comparison{,_v2,_v2_chatgpt}.{md,json}.
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from decision import rules_v2  # noqa: E402
from reasoning.uncertainty.bayesian_correlation import is_abnormal, load_knowledge_base  # noqa: E402
from reasoning.uncertainty.evaluate import SCENARIO_SETS, components, load_scenarios, score_rows  # noqa: E402

RESULTS = Path(__file__).resolve().parent / "results"
SEED = 20261013
TIE_ORDERS = 500
BOOTSTRAP_DRAWS = 1000
BOOTSTRAP_TIE_ORDERS = 20
SYSTEMS = ("isolated", "dc_guardian")
LABEL = {"isolated": "Isolated single-domain", "dc_guardian": "DC-GUARDIAN (correlated)"}


# ------------------------------------------------------------------ alerts
def alerts_for(scenario: dict, rows: list[dict], system: str) -> list[dict]:
    events = {e["event_id"]: e for e in scenario["events"] if is_abnormal(e)}
    if system == "isolated":
        groups = [{eid} for eid in events]
    else:
        links = [tuple(r["event_ids"]) for r in rows if r["scenario_id"] == scenario["scenario_id"] and r["crisp"]]
        groups = components(list(events), links)
    alerts = []
    for members in groups:
        group = [events[m] for m in sorted(members)]
        if len(group) == 1:
            severity = rules_v2.event_severity(group[0])[0]
        else:
            severity = rules_v2.decide_group(group)["severity"]
        incidents = {(scenario["scenario_id"], e["ground_truth_incident"])
                     for e in group if e["ground_truth_incident"] is not None}
        alerts.append({"scenario_id": scenario["scenario_id"], "severity": severity,
                       "events": [e["event_id"] for e in group], "incidents": incidents})
    return alerts


def incident_events(scenarios: list[dict]) -> dict:
    truth: dict[tuple, set] = {}
    for scenario in scenarios:
        for e in scenario["events"]:
            if is_abnormal(e) and e["ground_truth_incident"] is not None:
                truth.setdefault((scenario["scenario_id"], e["ground_truth_incident"]), set()).add(e["event_id"])
    return truth


# ------------------------------------------------------------------ queue metrics
def ordered(alerts: list[dict], rng: random.Random) -> list[dict]:
    keyed = [(-rules_v2.SEVERITY_ORDER[a["severity"]], rng.random(), i) for i, a in enumerate(alerts)]
    return [alerts[i] for *_, i in sorted(keyed)]


def queue_metrics(queue: list[dict], truth: dict) -> dict:
    hits, precisions = 0, []
    first_seen, events_seen = {}, set()
    all_events = set().union(*truth.values()) if truth else set()
    full_context_at = None
    for rank, alert in enumerate(queue, start=1):
        if alert["incidents"]:
            hits += 1
            precisions.append(hits / rank)
        for incident in alert["incidents"]:
            first_seen.setdefault(incident, rank)
        events_seen.update(alert["events"])
        if full_context_at is None and all_events <= events_seen:
            full_context_at = rank
    return {"average_precision": sum(precisions) / hits if hits else 0.0,
            "alerts_until_every_incident_seen": max(first_seen.values()) if first_seen else 0,
            "alerts_until_every_incident_event_seen": full_context_at or len(queue),
            "mean_rank_first_sight": statistics.fmean(first_seen.values()) if first_seen else 0.0}


def expected_queue(alerts: list[dict], truth: dict, rng: random.Random, orders: int) -> dict:
    runs = [queue_metrics(ordered(alerts, rng), truth) for _ in range(orders)]
    return {k: statistics.fmean(r[k] for r in runs) for k in runs[0]}


def static_metrics(alerts: list[dict], truth: dict) -> dict:
    levels = {}
    for level in ("HIGH", "MEDIUM", "LOW"):
        at = [a for a in alerts if a["severity"] == level]
        levels[level] = {"alerts": len(at), "relevant": sum(bool(a["incidents"]) for a in at)}
    top = next(level for level in ("HIGH", "MEDIUM", "LOW") if levels[level]["alerts"])
    whole = sum(1 for members in truth.values()
                if any(members <= set(a["events"]) for a in alerts))
    multi = [k for k, members in truth.items() if len(members) > 1]
    whole_multi = sum(1 for k in multi if any(truth[k] <= set(a["events"]) for a in alerts))
    fragments = [sum(1 for a in alerts if k in a["incidents"]) for k in multi]
    return {"alerts": len(alerts), "noise_alerts": sum(1 for a in alerts if not a["incidents"]),
            "relevant_alerts": sum(1 for a in alerts if a["incidents"]),
            "levels": levels, "top_level": top,
            "top_level_precision": levels[top]["relevant"] / levels[top]["alerts"],
            "incidents": len(truth), "incidents_in_one_alert": whole,
            "multi_event_incidents": len(multi), "multi_event_incidents_in_one_alert": whole_multi,
            "mean_alerts_per_multi_event_incident": statistics.fmean(fragments) if fragments else 0.0}


def evaluate_split(scenarios: list[dict], rows: list[dict], rng: random.Random, orders: int = TIE_ORDERS) -> dict:
    truth = incident_events(scenarios)
    result = {}
    for system in SYSTEMS:
        alerts = [a for s in scenarios for a in alerts_for(s, rows, system)]
        result[system] = {**static_metrics(alerts, truth), **expected_queue(alerts, truth, rng, orders)}
    return result


def bootstrap(scenarios: list[dict], rows: list[dict], rng: random.Random) -> dict:
    keys = ("average_precision", "alerts_until_every_incident_event_seen", "alerts")
    diffs = {k: [] for k in keys}
    for _ in range(BOOTSTRAP_DRAWS):
        sample = []
        for i, s in enumerate(rng.choice(scenarios) for _ in scenarios):
            copy = {**s, "scenario_id": f"{s['scenario_id']}#{i}",
                    "events": [{**e, "event_id": f"{e['event_id']}#{i}"} for e in s["events"]]}
            sample.append(copy)
        sample_rows = [{**r, "scenario_id": c["scenario_id"],
                        "event_ids": [f"{x}#{c['scenario_id'].split('#')[1]}" for x in r["event_ids"]]}
                       for c in sample for r in rows if r["scenario_id"] == c["scenario_id"].split("#")[0]]
        result = evaluate_split(sample, sample_rows, rng, BOOTSTRAP_TIE_ORDERS)
        for k in keys:
            diffs[k].append(result["dc_guardian"][k] - result["isolated"][k])
    out = {}
    for k, values in diffs.items():
        values.sort()
        out[k] = [round(values[int(0.025 * (len(values) - 1))], 3), round(values[int(0.975 * (len(values) - 1))], 3)]
    return out


# ------------------------------------------------------------------ report
def fmt(x) -> str:
    return f"{x:.3f}" if isinstance(x, float) else str(x)


def table(split: dict, ci: dict | None = None) -> list[str]:
    iso, dcg = split["isolated"], split["dc_guardian"]
    rows = [
        ("Alerts shown", "alerts", "fewer is better"),
        ("Noise alerts (no incident event)", "noise_alerts", "fewer is better"),
        ("Incidents shown whole in one alert", "incidents_in_one_alert", f"of {iso['incidents']}"),
        ("Multi-event incidents shown whole in one alert", "multi_event_incidents_in_one_alert",
         f"of {iso['multi_event_incidents']}"),
        ("Mean alerts per multi-event incident", "mean_alerts_per_multi_event_incident", "1.0 is ideal"),
        ("Top-severity precision", "top_level_precision", "share of top-level alerts that are incidents"),
        ("Average precision of the queue", "average_precision", "higher is better"),
        ("Alerts reviewed until every incident seen once", "alerts_until_every_incident_seen", "fewer is better"),
        ("Alerts reviewed until every incident event seen", "alerts_until_every_incident_event_seen", "fewer is better"),
        ("Mean queue position where an incident is first seen", "mean_rank_first_sight", "lower is better"),
    ]
    lines = [f"| Metric | {LABEL['isolated']} | {LABEL['dc_guardian']} | Note |", "|---|---:|---:|---|"]
    for name, key, note in rows:
        value_iso, value_dcg = iso[key], dcg[key]
        if key == "top_level_precision":
            value_iso = f"{value_iso:.0%} ({iso['top_level']})"
            value_dcg = f"{value_dcg:.0%} ({dcg['top_level']})"
        extra = f"; difference 95% CI {ci[key][0]} to {ci[key][1]}" if ci and key in ci else ""
        lines.append(f"| {name} | {fmt(value_iso)} | {fmt(value_dcg)} | {note}{extra} |")
    return lines


def level_lines(split: dict) -> list[str]:
    lines = ["| Severity | Isolated: alerts (incident) | DC-GUARDIAN: alerts (incident) |", "|---|---:|---:|"]
    for level in ("HIGH", "MEDIUM", "LOW"):
        a, b = split["isolated"]["levels"][level], split["dc_guardian"]["levels"][level]
        lines.append(f"| {level} | {a['alerts']} ({a['relevant']}) | {b['alerts']} ({b['relevant']}) |")
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--set", dest="scenario_set", choices=sorted(SCENARIO_SETS), default="v1")
    args = parser.parse_args(argv)
    path, suffix, set_labels = SCENARIO_SETS[args.scenario_set]
    scenarios = load_scenarios(path)
    rows = score_rows(scenarios, load_knowledge_base())
    rng = random.Random(SEED)
    report = {"protocol": "fixed 2026-10-13 before results; see module docstring",
              "policy": rules_v2.POLICY, "linkage_rule": rules_v2.SELECTED_LINKAGE_RULE,
              "labels": set_labels or "scenario author (no independent labelling round)",
              "tie_orders": TIE_ORDERS, "seed": SEED, "splits": {}}
    if set_labels:
        report["scenario_set"] = args.scenario_set
    for split in ("test", "dev"):
        chosen = [s for s in scenarios if s["split"] == split]
        report["splits"][split] = evaluate_split(chosen, [r for r in rows if r["split"] == split], rng)
    test = [s for s in scenarios if s["split"] == "test"]
    report["test_difference_ci95"] = bootstrap(test, [r for r in rows if r["split"] == "test"], random.Random(SEED + 1))
    report["bootstrap"] = {"draws": BOOTSTRAP_DRAWS, "unit": "scenario", "tie_orders_per_draw": BOOTSTRAP_TIE_ORDERS}

    t, d = report["splits"]["test"], report["splits"]["dev"]
    command = "baseline_comparison.py" + ("" if not set_labels else f"` with `--set {args.scenario_set}")
    lines = ["# DC-GUARDIAN against isolated single-domain monitoring"
             + ("" if not set_labels else f" — scenario set {args.scenario_set}"), "",
             f"Generated by `presentation/backend/validation/{command}` on the labelled uncertainty scenarios. "
             "Both systems use the same DCG-DECISION-v2 single-event severities, so the comparison isolates the effect "
             "of correlation and group severity. A queue is sorted by severity with ties in random order "
             f"(averaged over {TIE_ORDERS} orders); an alert is relevant when it contains an event of a labelled incident. "
             + (set_labels or "Labels were written by the scenario author."), "",
             f"## 1. Held-out test split ({sum(1 for s in test)} scenarios, primary result)", "",
             *table(t, report["test_difference_ci95"]), "",
             f"Intervals: DC-GUARDIAN minus isolated, bootstrap over scenarios ({BOOTSTRAP_DRAWS} draws, "
             f"{BOOTSTRAP_TIE_ORDERS} tie orders each).", "",
             "### Severity levels (test)", "", *level_lines(t), "",
             "## 2. Dev split (reference only: the v2 linkage rule was selected here)", "",
             *table(d), "", "### Severity levels (dev)", "", *level_lines(d), "",
             "## What this shows and what it does not", "",
             "- **Shows:** on these scenarios, correlation reduces the number of alerts, presents multi-event incidents "
             "as one alert instead of fragments, and moves incidents up the review queue, because only linked groups "
             "reach HIGH.",
             "- **Does not show:** performance on real site data (the scenarios and topology are synthetic); that severity "
             "levels are correct (the scenarios have relatedness labels, not severity labels); or anything about response "
             "recommendations, which need a separate user evaluation.",
             "- **Bias:** the scenarios, the labels, the linkage rule and its known-mechanism list come from the same "
             "author; the linkage rule was selected on the dev split. Independent labels are pending."
             + ("" if args.scenario_set != "v2-chatgpt" else
                " Here ChatGPT's labels replace the author's, which removes the author from the labels but not from "
                "the scenarios or the rule."),
             "- **Baseline design:** isolated monitoring here uses DC-GUARDIAN's own single-event policy, which caps "
             "single events at MEDIUM. A real single-domain tool might rank differently; the comparison measures the "
             "added value of correlation, not of any particular commercial tool.", ""]
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / f"baseline_comparison{suffix}.md").write_text("\n".join(lines), encoding="utf-8")
    serialisable = json.loads(json.dumps(report, default=list))
    (RESULTS / f"baseline_comparison{suffix}.json").write_text(json.dumps(serialisable, indent=2), encoding="utf-8")
    print("\n".join(table(t, report["test_difference_ci95"])))
    print(f"Report: presentation/backend/validation/results/baseline_comparison{suffix}.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
