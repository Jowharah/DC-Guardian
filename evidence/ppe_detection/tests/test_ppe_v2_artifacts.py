"""PPE-v2 artifacts: v1 stays frozen, v2 was selected on validation and tested once.

No GPU needed: checks files, hashes and the recorded protocol.
"""
import hashlib
import json
from pathlib import Path

PPE = Path(__file__).resolve().parents[1]
MODELS = PPE / "models"
V1_WEIGHTS_SHA256 = "0f0577e37241e423faac75a3c3999538260abc55c220e0b2626bbe7c4bf5bc74"
V2_WEIGHTS_SHA256 = "b1ee6e2b11369bdccc82ce2827a4c45d0a6bbf7936d5406f9438785a3d269c75"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(*parts) -> dict:
    return json.loads(PPE.joinpath(*parts).read_text(encoding="utf-8-sig"))


def test_v1_weights_and_config_are_unchanged():
    assert _sha(MODELS / "ppe_yolov8_best.pt") == V1_WEIGHTS_SHA256
    config = _json("models", "ppe_config.json")
    assert config["configuration_version"] == "PPE-v1" and config["weights"] == "ppe_yolov8_best.pt"
    assert config["image_size"] == 640 and config["configuration_frozen"] is True


def test_v2_was_selected_on_validation_by_the_declared_rule():
    selection = _json("results", "selection_v2", "selection_v2.json")
    assert selection["locked_test_accessed"] is False and selection["validation_images"] == 810
    results = selection["results"]
    candidates = {k: v for k, v in results.items() if k.startswith("v2")}
    assert set(candidates) == {"v2n1024", "v2s1024", "v2m1024"}
    top = max(v["criterion_required_map50"] for v in candidates.values())
    eligible = [k for k, v in candidates.items() if v["criterion_required_map50"] >= top - 0.01]
    order = ("yolov8n", "yolov8s", "yolov8m")
    assert selection["selected"] == min(eligible, key=lambda k: order.index(candidates[k]["architecture"]))
    assert candidates[selection["selected"]]["criterion_required_map50"] > results["PPE-v1 (frozen)"]["criterion_required_map50"]
    assert selection["selected_sha256"] == V2_WEIGHTS_SHA256 == _sha(MODELS / "ppe_yolov8_v2_best.pt")


def test_v2_locked_test_used_the_selected_weights_once():
    result = _json("results", "final_test_v2", "ppe_final_test_v2.json")
    meta = _json("models", "ppe_v2_training_metadata.json")
    assert result["candidate"] == meta["candidate"] == "v2s1024"
    assert result["weights_sha256"] == V2_WEIGHTS_SHA256 and result["final_test_images"] == 810
    assert meta["locked_test_accessed"] is False and meta["image_size"] == result["image_size"] == 1024
    assert not result["training_performed"] and not result["model_selection_performed"]
    v1 = _json("results", "final_test", "ppe_final_test.json")
    assert v1["final_test_images"] == result["final_test_images"]


def test_posthoc_analysis_is_labelled_and_never_replaces_the_official_result():
    posthoc = _json("results", "posthoc_v2", "posthoc_v2.json")
    assert posthoc["label"].startswith("POST-HOC") and posthoc["official_ppe_v2"] == "v2s1024"
    for name, check in posthoc["consistency_with_official"].items():
        assert check["official_map50"] == check["rescored_map50"], name
    assert posthoc["weights_sha256"]["PPE-v1"] == V1_WEIGHTS_SHA256
    assert posthoc["weights_sha256"]["v2s1024"] == V2_WEIGHTS_SHA256
    # The combined detector is built only when every v2 candidate is worse than v1 on vests.
    assert (posthoc["combined"] is None) == (not posthoc["all_v2_worse_than_v1_on_vests"])
    assert _json("results", "selection_v2", "selection_v2.json")["selected"] == "v2s1024"
