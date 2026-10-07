"""
DC-Guardian Evidence
Final PPE Configuration Contract Test

Verifies the complete frozen PPE-v1 runtime configuration:
- YOLOv8n detector
- SH17 dataset identity
- frozen development configuration
- runtime thresholds
- person/PPE association
- PPE-POLICY-v1
"""

from pathlib import Path
import json

from ultralytics import YOLO

from evidence.ppe_detection.src.ppe_policy import (
    POLICY_NAME,
    POLICY_VERSION,
    REQUIRED_PPE,
)


# ============================================================
# Paths
# ============================================================

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[3]
)

PPE_ROOT = (
    PROJECT_ROOT
    / "evidence"
    / "ppe_detection"
)

CONFIG_FILE = (
    PPE_ROOT
    / "models"
    / "ppe_config.json"
)

MODEL_FILE = (
    PPE_ROOT
    / "models"
    / "ppe_yolov8_best.pt"
)

DATASET_YAML = (
    PPE_ROOT
    / "data"
    / "processed"
    / "sh17_yolo"
    / "dataset.yaml"
)

TEST_MANIFEST = (
    PPE_ROOT
    / "data"
    / "processed"
    / "sh17_yolo"
    / "test_files.txt"
)


EXPECTED_CLASSES = {
    0: "person",
    1: "ear",
    2: "ear-mufs",
    3: "face",
    4: "face-guard",
    5: "face-mask-medical",
    6: "foot",
    7: "tools",
    8: "glasses",
    9: "gloves",
    10: "helmet",
    11: "hands",
    12: "head",
    13: "medical-suit",
    14: "shoes",
    15: "safety-suit",
    16: "safety-vest",
}


print(
    "\n============================================"
)
print(
    "DC-GUARDIAN PPE CONFIG CONTRACT TEST"
)
print(
    "============================================"
)


# ============================================================
# Required artifacts
# ============================================================

for path in [
    CONFIG_FILE,
    MODEL_FILE,
    DATASET_YAML,
    TEST_MANIFEST,
]:

    if not path.exists():

        raise AssertionError(
            f"Required PPE artifact missing: {path}"
        )


print(
    "PASS: Frozen PPE configuration exists."
)


# ============================================================
# Configuration
# ============================================================

config = json.loads(
    CONFIG_FILE.read_text(
        encoding="utf-8"
    )
)


# ============================================================
# Detector identity
# ============================================================

assert (
    config["configuration_version"]
    == "PPE-v1"
)

assert (
    config["configuration_frozen"]
    is True
)

assert (
    config["model_family"]
    == "YOLOv8"
)

assert (
    config["architecture"]
    == "YOLOv8n"
)

assert (
    config["weights"]
    == "ppe_yolov8_best.pt"
)

assert (
    config["dataset"]
    == "SH17"
)

assert (
    config["class_count"]
    == 17
)


print(
    "PASS: YOLOv8n / SH17 detector identity frozen."
)


# ============================================================
# Training configuration
# ============================================================

assert (
    config["image_size"]
    == 640
)

assert (
    config["training_epochs"]
    == 50
)

assert (
    config["batch_size"]
    == 16
)

assert (
    config["seed"]
    == 42
)


print(
    "PASS: Detector training configuration frozen."
)


# ============================================================
# Dataset boundary
# ============================================================

assert (
    config["train_images"]
    == 6479
)

assert (
    config["validation_images"]
    == 810
)

assert (
    config["locked_test_images"]
    == 810
)

assert (
    config["model_selection_source"]
    == "training_and_validation_only"
)

assert (
    config["locked_test_accessed_when_frozen"]
    is False
)


print(
    "PASS: Detector frozen using development data only."
)

print(
    "PASS: Locked final test was untouched "
    "when detector was frozen."
)


# ============================================================
# Frozen operating point
# ============================================================

assert (
    float(
        config[
            "confidence_threshold"
        ]
    )
    == 0.25
)

assert (
    float(
        config[
            "iou_threshold"
        ]
    )
    == 0.70
)

assert (
    float(
        config[
            "association_minimum_containment"
        ]
    )
    == 0.50
)


print(
    "PASS: Confidence threshold = 0.25."
)

print(
    "PASS: IoU threshold = 0.70."
)

print(
    "PASS: Association containment = 0.50."
)


# ============================================================
# Association configuration
# ============================================================

assert (
    config[
        "association_method"
    ]
    == "object_containment"
)

assert (
    config[
        "person_assignment"
    ]
    == "strongest_eligible_match"
)


print(
    "PASS: Person/PPE association configuration frozen."
)


# ============================================================
# PPE policy
# ============================================================

assert (
    config[
        "compliance_policy_frozen"
    ]
    is True
)

assert (
    config[
        "policy_version"
    ]
    == POLICY_VERSION
)

assert (
    config[
        "policy_name"
    ]
    == POLICY_NAME
)

assert (
    config[
        "required_ppe"
    ]
    == list(
        REQUIRED_PPE
    )
)

assert (
    config[
        "policy_source"
    ]
    == "project_defined_baseline"
)

assert (
    config[
        "policy_development_source"
    ]
    == "development_validation_only"
)


print(
    "PASS: PPE-POLICY-v1 frozen."
)

print(
    "PASS: Baseline required PPE = "
    "helmet + safety-vest."
)

print(
    "PASS: Policy source explicitly project-defined."
)


# ============================================================
# Runtime statuses
# ============================================================

assert set(
    config[
        "runtime_statuses"
    ]
) == {
    "COMPLIANT",
    "NON_COMPLIANT",
    "NO_PERSON",
}


print(
    "PASS: PPE runtime status vocabulary frozen."
)


# ============================================================
# Policy semantics
# ============================================================

semantics = config[
    "policy_semantics"
]


if (
    "does not prove physical absence"
    not in semantics
):

    raise AssertionError(
        "PPE policy semantics must preserve "
        "the detection-vs-absence distinction."
    )


print(
    "PASS: Required-PPE-not-detected semantics preserved."
)


# ============================================================
# Frozen model vocabulary
# ============================================================

model = YOLO(
    str(
        MODEL_FILE
    )
)


model_names = {
    int(class_id):
        str(class_name)

    for class_id, class_name
    in model.names.items()
}


assert (
    model_names
    == EXPECTED_CLASSES
)


print(
    "PASS: Frozen checkpoint preserves "
    "the 17-class SH17 vocabulary."
)


# ============================================================
# Development YAML boundary
# ============================================================

yaml_text = DATASET_YAML.read_text(
    encoding="utf-8"
)


if "test_files.txt" in yaml_text:

    raise AssertionError(
        "Locked test leaked into development dataset.yaml."
    )


if "test:" in yaml_text:

    raise AssertionError(
        "Development dataset.yaml exposes locked test."
    )


print(
    "PASS: Development dataset configuration "
    "still excludes locked final test."
)


# ============================================================
# Summary
# ============================================================

print(
    "\n============================================"
)
print(
    "PPE FINAL CONFIGURATION SUMMARY"
)
print(
    "============================================"
)

print(
    "Configuration:       PPE-v1"
)

print(
    "Model:               YOLOv8n"
)

print(
    "Dataset:             SH17"
)

print(
    "Classes:             17"
)

print(
    "Image size:          640"
)

print(
    "Epochs:              50"
)

print(
    "Batch:               16"
)

print(
    "Seed:                42"
)

print(
    "Train:               6479"
)

print(
    "Validation:          810"
)

print(
    "Locked test:         810"
)

print(
    "Confidence:          0.25"
)

print(
    "IoU:                 0.70"
)

print(
    "Containment:         0.50"
)

print(
    "Association:         object_containment"
)

print(
    "Policy:              PPE-POLICY-v1"
)

print(
    "Profile:             BASELINE_DC_MAINTENANCE"
)

print(
    "Required PPE:        helmet + safety-vest"
)

print(
    "Detector:            FROZEN"
)

print(
    "Policy:              FROZEN"
)


print(
    "\n============================================"
)
print(
    "PPE FINAL CONFIG CONTRACT PASSED"
)
print(
    "============================================"
)
