"""Usability study scoring: SUS formula, concept key, optional tasks, template columns."""
import csv
from pathlib import Path

from presentation.backend.validation import usability_score as us

TEMPLATE = Path(__file__).resolve().parents[3] / "docs" / "usability_study" / "results_template.csv"


def row(**values):
    base = {c: "" for c in next(csv.reader(open(TEMPLATE, encoding="utf-8")))}
    base.update({"participant": "P01", **{f"sus{i}": "3" for i in range(1, 11)},
                 **{f"q{i}": "?" for i in range(1, 7)}, **{f"r{i}": "3" for i in range(1, 6)}})
    base.update(values)
    return base


def test_sus_uses_the_standard_formula():
    best = row(**{f"sus{i}": ("5" if i % 2 else "1") for i in range(1, 11)})
    worst = row(**{f"sus{i}": ("1" if i % 2 else "5") for i in range(1, 11)})
    assert us.sus_score(best) == 100.0 and us.sus_score(worst) == 0.0 and us.sus_score(row()) == 50.0
    assert us.sus_adjective(68) == "OK" and us.sus_adjective(90) == "excellent"


def test_concept_key_and_optional_tasks():
    rows = [row(participant="P01", q1="F", q2="T", q3="F", q4="F", q5="F", q6="T",
                t1_success="1", t1_time_s="40", t1_seq="6"),
            row(participant="P02", q1="T", q2="T", t1_success="0.5", t1_time_s="80", t1_seq="4")]
    summary = us.summarise(rows)
    assert summary["concept"] == {"P01": 6, "P02": 1}
    assert summary["tasks"]["t1"]["success_rate"] == 0.75 and summary["tasks"]["t1"]["median_time_s"] == 60
    assert "t8" not in summary["tasks"]  # optional task not run
    assert "Usability study results" in us.report(summary)


def test_template_has_every_column_the_scorer_reads():
    columns = set(next(csv.reader(open(TEMPLATE, encoding="utf-8"))))
    needed = {"participant"} | {f"{t}_{m}" for t in us.TASKS for m in ("success", "time_s", "errors", "help", "seq")}
    needed |= {f"sus{i}" for i in range(1, 11)} | set(us.CONCEPT_KEY) | set(us.TRUST)
    assert needed <= columns
