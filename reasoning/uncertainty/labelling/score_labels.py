"""
DC-Guardian Reasoning
Score an independent labeller's labels.csv against the author labels and
re-evaluate the crisp rule and the Bayesian model on the independent labels.

    python reasoning/uncertainty/labelling/score_labels.py path/to/labels.csv --name alice

Writes labelling/results/<name>.md and <name>.json:
- agreement with the author labels (percent and Cohen's kappa), overall and
  on the test split;
- crisp vs Bayesian precision/recall/F1 against the independent labels, with
  scenario-bootstrap 95% intervals (test split is the primary result);
- the same on "consensus" pairs, where author and labeller agree;
- every disagreement, for discussion.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from reasoning.uncertainty.bayesian_correlation import load_knowledge_base  # noqa: E402
from reasoning.uncertainty.evaluate import (  # noqa: E402
    BOOTSTRAP_SEED, bootstrap_f1, load_scenarios, prf, score_rows,
)

HERE = Path(__file__).resolve().parent
KEY_PATH = HERE / "pack_key.json"
RESULTS_DIR = HERE / "results"


def read_labels(path: Path, key: dict) -> dict[tuple[str, str], dict]:
    """(original event a, original event b) -> {'related': bool, 'confidence', 'note'}."""
    labels, problems = {}, []
    with open(path, newline="", encoding="utf-8-sig") as handle:
        for line, row in enumerate(csv.DictReader(handle), start=2):
            value = (row.get("related") or "").strip().upper()
            if value not in ("Y", "N", "YES", "NO"):
                problems.append(f"line {line} ({row.get('pair')}): related must be Y or N, got {value or 'empty'}")
                continue
            try:
                a, b = key["events"][row["event_a"].strip()], key["events"][row["event_b"].strip()]
            except KeyError:
                problems.append(f"line {line}: unknown event ID {row.get('event_a')} / {row.get('event_b')}")
                continue
            labels[tuple(sorted((a, b)))] = {"related": value.startswith("Y"),
                                             "confidence": (row.get("confidence") or "").strip(),
                                             "note": (row.get("note") or "").strip(),
                                             "pair": row.get("pair")}
    if problems:
        raise SystemExit("labels.csv has problems:\n- " + "\n- ".join(problems[:30]))
    return labels


def kappa(rows: list[dict]) -> float | None:
    n = len(rows)
    if not n:
        return None
    agree = sum(r["truth"] == r["independent"] for r in rows) / n
    pa, pb = sum(r["truth"] for r in rows) / n, sum(r["independent"] for r in rows) / n
    expected = pa * pb + (1 - pa) * (1 - pb)
    return round((agree - expected) / (1 - expected), 3) if expected < 1 else None


def methods(scenarios: list[dict], rows: list[dict], seed_offset: int = 0) -> dict:
    independent = [{**r, "truth": r["independent"]} for r in rows]
    used = {r["scenario_id"] for r in rows}
    return {"pairs": len(rows), "related": sum(r["independent"] for r in rows),
            "crisp": prf(independent, "crisp"), "bayesian": prf(independent, "bayesian"),
            "bootstrap": bootstrap_f1([s for s in scenarios if s["scenario_id"] in used], rows,
                                      random.Random(BOOTSTRAP_SEED + seed_offset), truth_key="independent")}


def score(labels_path: Path) -> dict:
    key = json.loads(KEY_PATH.read_text(encoding="utf-8"))
    labels = read_labels(labels_path, key)
    scenarios = load_scenarios()
    rows = score_rows(scenarios, load_knowledge_base())
    missing = [r["event_ids"] for r in rows if tuple(sorted(r["event_ids"])) not in labels]
    if missing:
        raise SystemExit(f"labels.csv is missing {len(missing)} candidate pairs; rebuild the pack and relabel.")
    neutral = {v: k for k, v in key["events"].items()}
    for r in rows:
        label = labels[tuple(sorted(r["event_ids"]))]
        r.update(independent=label["related"], confidence=label["confidence"], note=label["note"],
                 neutral_pair=" + ".join(sorted(neutral[e] for e in r["event_ids"])))
    result = {"labelled_pairs": len(rows)}
    for split in ("test", "all"):
        subset = [r for r in rows if split == "all" or r["split"] == split]
        consensus = [r for r in subset if r["truth"] == r["independent"]]
        result[split] = {
            "agreement": round(sum(r["truth"] == r["independent"] for r in subset) / len(subset), 3),
            "cohens_kappa": kappa(subset),
            "independent_labels": methods(scenarios, subset),
            "consensus_pairs": methods(scenarios, consensus, seed_offset=1),
        }
    result["disagreements"] = [{"neutral_pair": r["neutral_pair"], "original_pair": " + ".join(r["event_ids"]),
                                "scenario": r["scenario_id"], "split": r["split"],
                                "author": r["truth"], "labeller": r["independent"],
                                "labeller_confidence": r["confidence"], "note": r["note"],
                                "p_related": r["probability"]}
                               for r in rows if r["truth"] != r["independent"]]
    return result


def report(name: str, result: dict) -> str:
    lines = [f"# Independent labelling results — {name}", "",
             "Generated by `score_labels.py`. Test split is the primary result (dev scenarios were partly scored "
             "by the author while being written).", ""]
    for split in ("test", "all"):
        s = result[split]
        lines += [f"## {split.capitalize()} split", "",
                  f"Agreement with author labels: {100 * s['agreement']:.0f}% · Cohen's kappa {s['cohens_kappa']}", "",
                  "| Labels | Pairs (related) | Method | Precision | Recall | F1 | F1 95% interval |",
                  "|---|---|---|---:|---:|---:|---|"]
        for basis, title in (("independent_labels", "Independent"), ("consensus_pairs", "Consensus")):
            m = s[basis]
            for method in ("crisp", "bayesian"):
                ci = m["bootstrap"][f"{method}_f1_ci95"]
                p = m[method]
                lines.append(f"| {title} | {m['pairs']} ({m['related']}) | {method} | {p['precision']:.3f} | "
                             f"{p['recall']:.3f} | {p['f1']:.3f} | {ci[0]:.3f}–{ci[1]:.3f} |")
            d = m["bootstrap"]["difference_f1_ci95"]
            lines.append(f"| {title} | | Bayesian − crisp | | | | {d[0]:+.3f} to {d[1]:+.3f} |")
        lines.append("")
    lines += ["## Disagreements with the author", "",
              "| Pair (labeller's IDs) | Original | Split | Author | Labeller | Confidence | P(Related) | Note |",
              "|---|---|---|---|---|---|---:|---|"]
    lines += [f"| {d['neutral_pair']} | {d['original_pair']} | {d['split']} | {'Y' if d['author'] else 'N'} | "
              f"{'Y' if d['labeller'] else 'N'} | {d['labeller_confidence']} | {d['p_related']:.2f} | "
              f"{d['note'].replace('|', '/')} |" for d in result["disagreements"]]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("labels", type=Path)
    parser.add_argument("--name", required=True, help="labeller name or code, used in output file names")
    args = parser.parse_args()
    result = score(args.labels)
    RESULTS_DIR.mkdir(exist_ok=True)
    (RESULTS_DIR / f"{args.name}.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (RESULTS_DIR / f"{args.name}.md").write_text(report(args.name, result), encoding="utf-8")
    t = result["test"]
    print(f"{args.name}: test agreement {100 * t['agreement']:.0f}% (kappa {t['cohens_kappa']}); "
          f"independent-label test F1 crisp {t['independent_labels']['crisp']['f1']:.3f} · "
          f"Bayesian {t['independent_labels']['bayesian']['f1']:.3f}")
    print(f"Report: {(RESULTS_DIR / (args.name + '.md')).relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
