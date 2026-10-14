"""Operating curve of the frozen Temporal RF v2: validation only, reproduces the published validation point."""
import json
from pathlib import Path

from evidence.predictive_maintenance.src.config import RF_OPERATING_THRESHOLD
from evidence.predictive_maintenance.src.maintenance_detector import MODEL_SHA256

CURVE = Path(__file__).resolve().parents[1] / "results" / "operating_curve" / "operating_curve_validation.json"


def _curve() -> dict:
    return json.loads(CURVE.read_text(encoding="utf-8"))


def test_curve_is_validation_only_and_changes_nothing():
    report = _curve()
    assert report["label"].startswith("VALIDATION ONLY") and "not read" in report["label"]
    assert report["model_sha256"] == MODEL_SHA256
    assert report["frozen_threshold"] == RF_OPERATING_THRESHOLD == 0.45


def test_frozen_point_reproduces_the_published_validation_result():
    # README section 12, Q4 validation: drive recall 49.60%, 1.913 alerts per 1,000, precision 3.14%, median lead 6 days.
    frozen = next(r for r in _curve()["curve"] if r["threshold"] == RF_OPERATING_THRESHOLD)
    assert (frozen["failed_drives_caught"], frozen["failed_drives"]) == (313, 631)
    assert round(frozen["alerts_per_1000_drive_days"], 2) == 1.91
    assert round(100 * frozen["row_precision"], 2) == 3.14
    assert frozen["median_lead_days"] == 6.0


def test_lower_thresholds_catch_more_and_alert_more():
    rows = sorted(_curve()["curve"], key=lambda r: r["threshold"])
    for lower, higher in zip(rows, rows[1:]):
        assert lower["failed_drives_caught"] >= higher["failed_drives_caught"]
        assert lower["drives_flagged"] >= higher["drives_flagged"]
