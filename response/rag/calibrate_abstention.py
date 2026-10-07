"""Calibrate an evidence-sufficiency threshold on a development-only set."""

from __future__ import annotations

import json
import sys
from pathlib import Path

RAG_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(RAG_ROOT))

from retrieve import retrieve_knowledge  # noqa: E402

CASES_FILE = RAG_ROOT / "evaluation" / "abstention_calibration_cases.json"
OUTPUT_FILE = RAG_ROOT / "evaluation" / "abstention_calibration_report.json"


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> None:
    spec = load_json(CASES_FILE)
    observations = []

    for case in spec["cases"]:
        rows = retrieve_knowledge(
            case["query"],
            domains=case.get("domains"),
            top_k=3,
            ranking="controlled",
        )
        top_score = rows[0]["score"] if rows else 0.0
        observations.append({
            "case_id":case["case_id"],
            "supported":case["supported"],
            "top_score":top_score,
            "top_document":rows[0]["document_id"] if rows else None,
        })
        print(
            f"{case['case_id']} supported={str(case['supported']):5} "
            f"top_score={top_score:.4f} "
            f"top_document={rows[0]['document_id'] if rows else None}"
        )

    supported_scores = [
        x["top_score"] for x in observations if x["supported"]
    ]
    unsupported_scores = [
        x["top_score"] for x in observations if not x["supported"]
    ]

    candidates = sorted(set(
        [0.0, 1.0]
        + supported_scores
        + unsupported_scores
        + [
            (a + b) / 2
            for a in supported_scores
            for b in unsupported_scores
        ]
    ))

    best = None
    for threshold in candidates:
        tp=tn=fp=fn=0
        for item in observations:
            predicted = item["top_score"] >= threshold
            actual = item["supported"]
            if predicted and actual: tp += 1
            elif predicted and not actual: fp += 1
            elif not predicted and not actual: tn += 1
            else: fn += 1

        balanced = (
            (tp / (tp + fn) if tp + fn else 0.0)
            + (tn / (tn + fp) if tn + fp else 0.0)
        ) / 2
        candidate = {
            "threshold":threshold,
            "balanced_accuracy":balanced,
            "tp":tp,"tn":tn,"fp":fp,"fn":fn,
        }
        if (
            best is None
            or candidate["balanced_accuracy"] > best["balanced_accuracy"]
            or (
                candidate["balanced_accuracy"] == best["balanced_accuracy"]
                and candidate["threshold"] > best["threshold"]
            )
        ):
            best=candidate

    report={
        "calibration_version":spec["calibration_version"],
        "ranking_policy":"controlled",
        "decision_rule":"SUPPORTED when top cosine score >= threshold",
        "selected":best,
        "observations":observations,
        "warning":"Development-only calibration. Do not retune this threshold using the frozen 18-case evaluation set.",
    }
    with OUTPUT_FILE.open("w",encoding="utf-8") as handle:
        json.dump(report,handle,indent=2)
        handle.write("\n")

    print()
    print("="*60)
    print("DC-GUARDIAN RAG ABSTENTION CALIBRATION")
    print("="*60)
    print(f"Threshold:         {best['threshold']:.4f}")
    print(f"Balanced accuracy:{best['balanced_accuracy']:9.4f}")
    print(f"TP/TN/FP/FN:       {best['tp']}/{best['tn']}/{best['fp']}/{best['fn']}")
    print(f"Report:            {OUTPUT_FILE}")


if __name__=="__main__":
    main()
