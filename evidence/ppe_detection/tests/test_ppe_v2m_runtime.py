"""PPE-v2m runtime detector: same frozen policy as v1, test-informed choice recorded, v1 still selectable.

No GPU needed: checks files, hashes and configuration.
"""
import hashlib
import json
from pathlib import Path

PPE = Path(__file__).resolve().parents[1]
MODELS = PPE / "models"
V1_WEIGHTS_SHA256 = "0f0577e37241e423faac75a3c3999538260abc55c220e0b2626bbe7c4bf5bc74"
V2M_WEIGHTS_SHA256 = "ae2e58d55623401035219fbd5800ab706b8b2caa5631d9101e0ab75438cd0a7c"
# Everything the compliance outcome depends on besides the detector itself.
POLICY_FIELDS = ("policy_version", "policy_name", "required_ppe", "confidence_threshold", "iou_threshold",
                 "association_method", "association_minimum_containment", "person_assignment",
                 "runtime_statuses", "policy_semantics", "class_count", "dataset")


def _json(name: str) -> dict:
    return json.loads((MODELS / name).read_text(encoding="utf-8-sig"))


def test_v2m_weights_are_the_post_hoc_evaluated_model():
    weights = MODELS / "ppe_yolov8_v2m_best.pt"
    assert hashlib.sha256(weights.read_bytes()).hexdigest() == V2M_WEIGHTS_SHA256
    posthoc = json.loads((PPE / "results" / "posthoc_v2" / "posthoc_v2.json").read_text(encoding="utf-8"))
    assert posthoc["weights_sha256"]["v2m1024"] == V2M_WEIGHTS_SHA256


def test_v2m_config_keeps_the_v1_policy_and_changes_only_the_detector():
    v1, v2m = _json("ppe_config.json"), _json("ppe_config_v2m.json")
    for field in POLICY_FIELDS:
        assert v2m[field] == v1[field], field
    assert v2m["configuration_frozen"] is True and v2m["compliance_policy_frozen"] is True
    assert (v2m["configuration_version"], v2m["architecture"], v2m["image_size"]) == ("PPE-v2m", "YOLOv8m", 1024)
    assert v2m["weights"] == "ppe_yolov8_v2m_best.pt"


def test_v2m_is_recorded_as_test_informed():
    config = _json("ppe_config_v2m.json")
    meta = _json(config["metadata"])
    assert config["model_selection_source"] == "test_informed_post_hoc"
    assert config["locked_test_accessed_when_frozen"] is True
    assert meta["selection_status"] == "TEST_INFORMED_POST_HOC"
    assert meta["locked_test_accessed_before_runtime_choice"] is True
    assert meta["weights_sha256"] == V2M_WEIGHTS_SHA256 and meta["candidate"] == "v2m1024"


def test_v1_stays_frozen_and_selectable():
    assert hashlib.sha256((MODELS / "ppe_yolov8_best.pt").read_bytes()).hexdigest() == V1_WEIGHTS_SHA256
    assert _json("ppe_config.json")["configuration_version"] == "PPE-v1"
    source = (PPE / "src" / "ppe_pipeline.py").read_text(encoding="utf-8-sig")
    assert '"v1": CONFIG_FILE' in source and '"v2m": PPE_ROOT / "models" / "ppe_config_v2m.json"' in source
    assert 'def __init__(self, detector: str = "v1")' in source
