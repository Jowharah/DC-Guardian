"""PPE-v3: trained on SH17 + Kaggle helmet/jacket, accepted on validation by the declared rule, tested once.

No GPU needed: checks files, hashes and the recorded protocol. The runtime detector is not changed by v3.
"""
import hashlib
import json
from pathlib import Path

PPE = Path(__file__).resolve().parents[1]
MODELS = PPE / "models"
FROZEN_SHA256 = {
    "ppe_yolov8_best.pt": "0f0577e37241e423faac75a3c3999538260abc55c220e0b2626bbe7c4bf5bc74",
    "ppe_yolov8_v2_best.pt": "b1ee6e2b11369bdccc82ce2827a4c45d0a6bbf7936d5406f9438785a3d269c75",
    "ppe_yolov8_v2m_best.pt": "ae2e58d55623401035219fbd5800ab706b8b2caa5631d9101e0ab75438cd0a7c",
}
V3_SHA256 = "92a0a00f94b5166b066f721e4004e46210c1cadcb5c182714952c38baca61471"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(*parts) -> dict:
    return json.loads(PPE.joinpath(*parts).read_text(encoding="utf-8-sig"))


def test_earlier_models_are_unchanged():
    for name, digest in FROZEN_SHA256.items():
        assert _sha(MODELS / name) == digest, name


def test_v3_was_accepted_on_validation_by_the_declared_rule():
    selection = _json("results", "selection_v3", "selection_v3.json")
    assert selection["locked_test_accessed"] is False and selection["kaggle_test_accessed"] is False
    rows = selection["results"]
    v2m, v3 = rows["PPE-v2m (runtime)"], rows["PPE-v3m (v3m1024)"]
    for row in rows.values():
        sh17, kaggle = row["sh17_validation"], row["kaggle_validation"]
        mean = lambda r: (r["helmet"]["map50"] + r["safety-vest"]["map50"]) / 2
        assert abs(row["criterion"] - (mean(sh17) + mean(kaggle)) / 2) < 1e-3
    gain = v3["criterion"] - v2m["criterion"]
    drop = v2m["sh17_validation"]["person"]["map50"] - v3["sh17_validation"]["person"]["map50"]
    assert selection["accepted"] == (gain >= 0.01 and drop <= 0.02) is True
    assert selection["selected_sha256"] == V3_SHA256 == _sha(MODELS / "ppe_yolov8_v3m_best.pt")


def test_v3_training_never_saw_a_test_image():
    meta = _json("models", "ppe_v3m_metadata.json")
    prepare = _json("results", "training_v3", "prepare_summary.json")
    assert meta["locked_test_accessed"] is False and meta["kaggle_test_accessed"] is False
    assert meta["weights_sha256"] == V3_SHA256 and meta["resumed_after_interruption"] is True
    assert prepare["kaggle_train_near_duplicates_dropped"] > 0 and prepare["hamming_max"] == 6
    assert prepare["pseudo_labeller_sha256"] == FROZEN_SHA256["ppe_yolov8_v2m_best.pt"]
    assert "helmet" not in prepare["labels_train"]["pseudo"] and "safety-vest" not in prepare["labels_train"]["pseudo"]


def test_final_test_used_the_selected_weights_and_kept_the_runtime_unchanged():
    final = _json("results", "final_test_v3", "final_test_v3.json")
    assert final["results"]["PPE-v3m (v3m1024)"]["sha256"] == V3_SHA256
    assert "same-source" in final["kaggle_test"] and "already used" in final["sh17_locked_test"]
    source = (PPE.parents[1] / "presentation" / "backend" / "app" / "ppe_image_validation.py").read_text(encoding="utf-8")
    assert 'DEFAULT_PPE_DETECTOR = "v2m"' in source
