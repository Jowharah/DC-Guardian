"""
Score the DC-GUARDIAN usability study (docs/usability_study/).

Input: a copy of docs/usability_study/results_template.csv, one row per
participant (P01...). Task cells may be left empty for optional tasks not run.
- tN_success 1 / 0.5 / 0, tN_time_s, tN_errors, tN_help, tN_seq (1-7)
- sus1..sus10 1-5 (System Usability Scale, Brooke 1996)
- q1..q6 concept check: T, F or ? (not sure)
- r1..r5 trust and clarity 1-5 (r5 is reverse-intended: low agreement is desired)

    python presentation/backend/validation/usability_score.py docs/usability_study/results.csv

Writes results_summary.md next to the input.
"""

from __future__ import annotations

import csv
import statistics
import sys
from pathlib import Path

TASKS = [f"t{i}" for i in range(1, 10)]
CONCEPT_KEY = {"q1": "F", "q2": "T", "q3": "F", "q4": "F", "q5": "F", "q6": "T"}
TRUST = {"r1": "Understood why an alert had its severity", "r2": "Could tell detector from human input",
         "r3": "Dashboard showed what the system does not know", "r4": "Would trust it to prioritise my work",
         "r5": "Would trust it to decide without checking (low is desired)"}


def sus_score(row: dict) -> float:
    """Standard SUS: odd items score-1, even items 5-score, sum x 2.5 (0-100)."""
    values = [int(row[f"sus{i}"]) for i in range(1, 11)]
    if any(v < 1 or v > 5 for v in values):
        raise ValueError(f"{row['participant']}: SUS answers must be 1-5")
    total = sum((v - 1) if i % 2 == 1 else (5 - v) for i, v in enumerate(values, start=1))
    return total * 2.5


def sus_adjective(score: float) -> str:
    """Bangor, Kortum & Miller (2009) adjective bands (approximate)."""
    for limit, word in ((85.5, "excellent"), (72.6, "good"), (52.0, "OK"), (39.2, "poor")):
        if score >= limit:
            return word
    return "awful"


def number(value: str) -> float | None:
    value = (value or "").strip()
    return float(value) if value else None


def summarise(rows: list[dict]) -> dict:
    tasks = {}
    for task in TASKS:
        done = [r for r in rows if number(r[f"{task}_success"]) is not None]
        if not done:
            continue
        times = [number(r[f"{task}_time_s"]) for r in done if number(r[f"{task}_time_s"]) is not None]
        seq = [number(r[f"{task}_seq"]) for r in done if number(r[f"{task}_seq"]) is not None]
        tasks[task] = {"n": len(done),
                       "success_rate": statistics.fmean(number(r[f"{task}_success"]) for r in done),
                       "median_time_s": statistics.median(times) if times else None,
                       "mean_errors": statistics.fmean(number(r[f"{task}_errors"]) or 0 for r in done),
                       "help_given": sum(number(r[f"{task}_help"]) or 0 for r in done),
                       "mean_seq": statistics.fmean(seq) if seq else None}
    sus = {r["participant"]: sus_score(r) for r in rows}
    concept = {r["participant"]: sum(r[q].strip().upper() == a for q, a in CONCEPT_KEY.items()) for r in rows}
    per_item = {q: sum(r[q].strip().upper() == a for r in rows) for q, a in CONCEPT_KEY.items()}
    trust = {k: statistics.fmean(int(r[k]) for r in rows) for k in TRUST}
    return {"participants": len(rows), "tasks": tasks, "sus": sus, "concept": concept,
            "concept_per_item": per_item, "trust": trust}


def report(summary: dict) -> str:
    n = summary["participants"]
    sus_values = list(summary["sus"].values())
    sus_mean = statistics.fmean(sus_values)
    lines = ["# Usability study results", "",
             f"{n} participants. Formative study: small sample, results describe these sessions, not all users.", "",
             "## Tasks", "",
             "| Task | n | Success rate | Median time (s) | Mean errors | Help given | Mean ease (SEQ, 1-7) |",
             "|---|---:|---:|---:|---:|---:|---:|"]
    for task, t in summary["tasks"].items():
        time = "–" if t["median_time_s"] is None else f"{t['median_time_s']:.0f}"
        seq = "–" if t["mean_seq"] is None else f"{t['mean_seq']:.1f}"
        lines.append(f"| {task.upper()} | {t['n']} | {t['success_rate']:.0%} | {time} | {t['mean_errors']:.1f} | "
                     f"{t['help_given']:.0f} | {seq} |")
    lines += ["", "## System Usability Scale", "",
              f"Mean **{sus_mean:.1f}** ({sus_adjective(sus_mean)}), range {min(sus_values):.1f}–{max(sus_values):.1f}. "
              "About 68 is the cross-study average.", "",
              "| Participant | SUS |", "|---|---:|", *(f"| {p} | {s:.1f} |" for p, s in summary["sus"].items()), "",
              "## Concept check (what the system claims)", "",
              f"Mean {statistics.fmean(summary['concept'].values()):.1f} of 6 correct.", "",
              "| Statement | Correct answer | Answered correctly |", "|---|---|---:|"]
    labels = {"q1": "Grouped means caused", "q2": "Severity from fixed rules", "q3": "Verdict overwrites detector",
              "q4": "Acts by itself", "q5": "Non-compliant proves absence", "q6": "Every alert human-checked"}
    for q, answer in CONCEPT_KEY.items():
        lines.append(f"| {q.upper()} {labels[q]} | {'True' if answer == 'T' else 'False'} | "
                     f"{summary['concept_per_item'][q]} of {n} |")
    lines += ["", "## Trust and clarity (1-5)", "", "| Item | Mean |", "|---|---:|",
              *(f"| {TRUST[k]} | {v:.1f} |" for k, v in summary["trust"].items()), ""]
    return "\n".join(lines)


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    path = Path(sys.argv[1])
    rows = [r for r in csv.DictReader(open(path, encoding="utf-8-sig")) if r.get("participant", "").strip()]
    if not rows:
        raise SystemExit("No participant rows in the file.")
    text = report(summarise(rows))
    out = path.with_name("results_summary.md")
    out.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
