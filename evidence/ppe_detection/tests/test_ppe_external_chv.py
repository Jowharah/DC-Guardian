"""Third-dataset (CHV) test: recorded protocol and model identity (no GPU, no dataset needed)."""
import hashlib
import json
from pathlib import Path

PPE = Path(__file__).resolve().parents[1]
REPORT = PPE / "results" / "external_chv" / "external_chv.json"
V3_SHA256 = "92a0a00f94b5166b066f721e4004e46210c1cadcb5c182714952c38baca61471"  # PR #31 metadata


def _report() -> dict:
    return json.loads(REPORT.read_text(encoding="utf-8"))


def test_chv_test_is_independent_and_complete():
    report = _report()
    assert report["label"].startswith("THIRD-DATASET TEST")
    assert report["source_images"] == 1330
    assert report["images_evaluated"] == report["source_images"] - report["near_duplicates_excluded"]
    assert set(report["instances"]) == {"person", "helmet", "safety-vest"}
    assert sum(report["truth_distribution"].values()) == report["images_evaluated"]


def test_chv_scores_the_recorded_models():
    weights = _report()["weights_sha256"]
    for name, file in {"PPE-v1": "ppe_yolov8_best.pt", "PPE-v2 official (v2s1024)": "ppe_yolov8_v2_best.pt",
                       "PPE-v2m (runtime)": "ppe_yolov8_v2m_best.pt"}.items():
        assert weights[name] == hashlib.sha256((PPE / "models" / file).read_bytes()).hexdigest()
    assert weights["PPE-v3m (PR #31)"] == V3_SHA256


def test_compliance_rates_are_consistent():
    for name, r in _report()["compliance"].items():
        assert 0 <= r["missed_violations"] <= 1 - r["violations_caught"] + 1e-9, name
        assert r["images"] == _report()["images_evaluated"], name
