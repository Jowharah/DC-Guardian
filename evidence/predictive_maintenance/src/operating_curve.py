"""
DC-Guardian Evidence
Predictive maintenance — operating curve of the frozen Temporal RF v2 (validation only)

Temporal RF v2 flags a drive-day as AT_RISK when its 7-day failure
probability reaches the frozen threshold 0.45. On the 2026 Q1 holdout that
caught 48% of failing drives with 3.4% row precision. Raising recall means
more alerts, so the operating point is an operator trade-off, not a model
property. This script lays the trade-off out so it can be chosen with
evidence:

- scores the 2025 Q4 VALIDATION period once with the frozen model (SHA-256
  checked); the 2026 Q1 locked final test is not read;
- sweeps thresholds and reports, with the same definitions as evaluate.py:
  failing drives caught (drive recall), alerts per 1,000 drive-days, drives
  flagged at least once, the share of flagged drives that fail within the
  window (drive precision), row precision and median first-warning lead time;
- changes nothing: the frozen model and threshold 0.45 stay as they are. A
  new operating point would be a new, versioned configuration chosen from
  this validation curve and tested once on the holdout.

Run with the maintenance environment (pyarrow):
    .venv-gru\\Scripts\\python.exe evidence\\predictive_maintenance\\src\\operating_curve.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evidence.predictive_maintenance.src.config import (  # noqa: E402
    FEATURE_DATA_DIR, RF_OPERATING_THRESHOLD, TEMPORAL_RF_FEATURES, VALIDATION_PERIOD)
from evidence.predictive_maintenance.src.evaluate import (  # noqa: E402
    MODEL_FILE, calculate_drive_metrics, calculate_lead_time)
from evidence.predictive_maintenance.src.maintenance_detector import MODEL_SHA256  # noqa: E402
from shared.model_integrity import verify_sha256  # noqa: E402

OUT = PROJECT_ROOT / "evidence" / "predictive_maintenance" / "results" / "operating_curve"
SCORES = PROJECT_ROOT / "evidence" / "predictive_maintenance" / "data" / "processed" / "results" / "validation_scores_rf_v2.parquet"
THRESHOLDS = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.80, 0.90]
CHUNK = 500_000


def validation_scores() -> pd.DataFrame:
    """Validation rows with the frozen model's failure probability (cached; model hash checked).

    Same population as evaluate.load_validation_data (rows with a label), read
    in batches: the full feature table (18.9M rows x 29 columns) does not fit
    in memory twice.
    """
    import pyarrow.parquet as pq

    verify_sha256(MODEL_FILE, MODEL_SHA256)
    if SCORES.exists():
        return pd.read_parquet(SCORES)
    model = joblib.load(MODEL_FILE)
    keep = ["date", "serial_number", "failure_date", "fail_within_7_days"]
    source = pq.ParquetFile(FEATURE_DATA_DIR / f"{VALIDATION_PERIOD}_features.parquet")
    parts = []
    for batch in source.iter_batches(batch_size=CHUNK, columns=keep + TEMPORAL_RF_FEATURES):
        frame = batch.to_pandas()
        frame = frame[frame["fail_within_7_days"].notna()]
        if frame.empty:
            continue
        part = frame[keep].copy()
        part["probability"] = model.predict_proba(frame[TEMPORAL_RF_FEATURES])[:, 1].astype(np.float32)
        parts.append(part)
    scored = pd.concat(parts, ignore_index=True)
    SCORES.parent.mkdir(parents=True, exist_ok=True)
    scored.to_parquet(SCORES, index=False)
    return scored


def point(scored: pd.DataFrame, threshold: float) -> dict:
    prediction = (scored["probability"].to_numpy() >= threshold).astype(int)
    total, detected, drive_recall = calculate_drive_metrics(scored, prediction)
    median_lead, mean_lead, _ = calculate_lead_time(scored, prediction)
    y = scored["fail_within_7_days"].astype(int).to_numpy()
    alerts = int(prediction.sum())
    flagged = scored.loc[prediction == 1, "serial_number"]
    failing = set(scored.loc[y == 1, "serial_number"])
    flagged_drives = int(flagged.nunique())
    flagged_failing = int(flagged[flagged.isin(failing)].nunique())
    return {"threshold": threshold, "failed_drives": int(total), "failed_drives_caught": int(detected),
            "drive_recall": round(float(drive_recall), 4), "alerts": alerts,
            "alerts_per_1000_drive_days": round(1000 * alerts / len(scored), 3),
            "row_precision": round(float(y[prediction == 1].mean()) if alerts else 0.0, 4),
            "drives_flagged": flagged_drives,
            "drive_precision": round(flagged_failing / flagged_drives, 4) if flagged_drives else 0.0,
            "drives_flagged_per_failure_caught": round(flagged_drives / detected, 1) if detected else None,
            "median_lead_days": None if pd.isna(median_lead) else float(median_lead),
            "mean_lead_days": None if pd.isna(mean_lead) else round(float(mean_lead), 2)}


def plot(rows: list[dict]) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7, 4.5))
    x = [r["alerts_per_1000_drive_days"] for r in rows]
    y = [100 * r["drive_recall"] for r in rows]
    ax.plot(x, y, marker="o")
    for r, xi, yi in zip(rows, x, y):
        if r["threshold"] in (0.1, 0.2, 0.3, RF_OPERATING_THRESHOLD, 0.6, 0.8):
            ax.annotate(f"{r['threshold']:.2f}", (xi, yi), textcoords="offset points", xytext=(5, -10), fontsize=8)
    frozen = next(r for r in rows if r["threshold"] == RF_OPERATING_THRESHOLD)
    ax.scatter([frozen["alerts_per_1000_drive_days"]], [100 * frozen["drive_recall"]], s=120, facecolors="none",
               edgecolors="red", label=f"frozen threshold {RF_OPERATING_THRESHOLD}")
    ax.set_xscale("log")
    ax.set_xlabel("Alerts per 1,000 drive-days (log scale)")
    ax.set_ylabel("Failing drives caught within 7 days (%)")
    ax.set_title(f"Temporal RF v2 operating curve — validation {VALIDATION_PERIOD}")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "operating_curve_validation.png", dpi=150)


def main() -> None:
    scored = validation_scores()
    rows = [point(scored, t) for t in THRESHOLDS]
    # Marginal cost of a lower threshold: extra drives flagged per extra failing drive caught,
    # relative to the next higher threshold. Lowering is worth it only if a missed failure costs
    # more than this many drive checks.
    for lower, higher in zip(rows, rows[1:]):
        extra_caught = lower["failed_drives_caught"] - higher["failed_drives_caught"]
        extra_flagged = lower["drives_flagged"] - higher["drives_flagged"]
        lower["extra_checks_per_extra_failure_vs_next_higher"] = (
            round(extra_flagged / extra_caught, 1) if extra_caught > 0 else None)
    rows[-1]["extra_checks_per_extra_failure_vs_next_higher"] = None
    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(OUT / "operating_curve_validation.csv", index=False)
    report = {"label": "VALIDATION ONLY (2025 Q4); frozen Temporal RF v2; locked 2026 Q1 test not read; nothing changed",
              "model_sha256": MODEL_SHA256, "frozen_threshold": RF_OPERATING_THRESHOLD,
              "drive_days": int(len(scored)), "drives": int(scored["serial_number"].nunique()), "curve": rows}
    (OUT / "operating_curve_validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    plot(rows)
    lines = [f"# Temporal RF v2 operating curve (validation {VALIDATION_PERIOD})", "",
             f"{report['label']}. {report['drive_days']:,} drive-days, {report['drives']:,} drives, "
             f"{rows[0]['failed_drives']} drives failing within the 7-day window.", "",
             "| Threshold | Failing drives caught | Alerts / 1,000 drive-days | Drives flagged | Flagged drives that fail | "
             "Drives flagged per failure caught | Extra checks per extra failure (vs next higher) | Row precision | "
             "Median lead (days) |",
             "|---:|---|---:|---:|---:|---:|---:|---:|---:|"]
    for r in rows:
        mark = " **(frozen)**" if r["threshold"] == RF_OPERATING_THRESHOLD else ""
        lines.append(f"| {r['threshold']:.2f}{mark} | {r['failed_drives_caught']} / {r['failed_drives']} "
                     f"({100 * r['drive_recall']:.1f}%) | {r['alerts_per_1000_drive_days']:.2f} | {r['drives_flagged']:,} | "
                     f"{100 * r['drive_precision']:.1f}% | {r['drives_flagged_per_failure_caught']} | "
                     f"{r['extra_checks_per_extra_failure_vs_next_higher'] or '–'} | "
                     f"{100 * r['row_precision']:.2f}% | {r['median_lead_days']} |")
    lines += ["", "![Operating curve](operating_curve_validation.png)", ""]
    (OUT / "operating_curve_validation.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
