"""External helmet/vest test: recorded protocol and model identity (no GPU, no dataset needed)."""
import hashlib
import json
from pathlib import Path

PPE = Path(__file__).resolve().parents[1]
RESULTS = PPE / "results" / "external_helmet_jacket"


def _json(name: str) -> dict:
    return json.loads((RESULTS / name).read_text(encoding="utf-8"))


def test_external_test_is_independent_and_scores_the_committed_models():
    report = _json("external_helmet_jacket.json")
    assert report["label"].startswith("EXTERNAL TEST")
    assert report["images_evaluated"] == report["source_images"] - report["near_duplicates_of_sh17_excluded"]
    assert report["instances"]["helmet"] > 3000 and report["instances"]["safety-vest"] > 2000
    weights = {"PPE-v1": "ppe_yolov8_best.pt", "PPE-v2 official (v2s1024)": "ppe_yolov8_v2_best.pt",
               "PPE-v2m (runtime)": "ppe_yolov8_v2m_best.pt"}
    for name, file in weights.items():
        assert report["weights_sha256"][name] == hashlib.sha256((PPE / "models" / file).read_bytes()).hexdigest()
        for cls in ("helmet", "safety-vest"):
            ci = report["results"][name][cls]["at_runtime_conf"]["recall_ci95"]
            assert ci[0] <= report["results"][name][cls]["at_runtime_conf"]["recall"] <= ci[1]


def test_sensitivity_is_labelled_explanatory():
    report = _json("external_sensitivity_640.json")
    assert report["label"].startswith("SENSITIVITY") and "not used to choose" in report["label"]
    assert set(report["at_640"]) == {"PPE-v2 official (v2s1024)", "PPE-v2m (runtime)"}
