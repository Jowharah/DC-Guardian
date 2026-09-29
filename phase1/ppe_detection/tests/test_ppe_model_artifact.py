"""
DC-Guardian Phase 1
PPE Model Artifact Contract Test

Verifies the selected YOLOv8n model artifact and training
metadata before the locked final-test population is accessed.
"""

from pathlib import Path
import json

import torch
from ultralytics import YOLO


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
    / "phase1"
    / "ppe_detection"
)

MODEL_FILE = (
    PPE_ROOT
    / "models"
    / "ppe_yolov8_best.pt"
)

METADATA_FILE = (
    PPE_ROOT
    / "models"
    / "ppe_training_metadata.json"
)

DATASET_YAML = (
    PPE_ROOT
    / "data"
    / "processed"
    / "sh17_yolo"
    / "dataset.yaml"
)

LOCKED_TEST_MANIFEST = (
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
    "DC-GUARDIAN PPE MODEL ARTIFACT TEST"
)
print(
    "============================================"
)


# ============================================================
# Required artifacts
# ============================================================

for path in [
    MODEL_FILE,
    METADATA_FILE,
    DATASET_YAML,
    LOCKED_TEST_MANIFEST,
]:

    if not path.exists():

        raise AssertionError(
            f"Required PPE artifact missing: {path}"
        )


print(
    "PASS: Required PPE model artifacts exist."
)


# ============================================================
# Training metadata
# ============================================================

metadata = json.loads(
    METADATA_FILE.read_text(
        encoding="utf-8"
    )
)


assert metadata[
    "model_family"
] == "YOLOv8"

assert metadata[
    "architecture"
] == "YOLOv8n"

assert metadata[
    "dataset"
] == "SH17"

assert metadata[
    "class_count"
] == 17

assert metadata[
    "train_images"
] == 6479

assert metadata[
    "validation_images"
] == 810

assert metadata[
    "locked_test_images"
] == 810

assert metadata[
    "epochs"
] == 50

assert metadata[
    "image_size"
] == 640

assert metadata[
    "batch_size"
] == 16

assert metadata[
    "seed"
] == 42

assert metadata[
    "smoke_test"
] is False

assert metadata[
    "locked_test_accessed"
] is False


print(
    "PASS: Frozen training configuration preserved."
)

print(
    "PASS: Locked final-test boundary preserved."
)


# ============================================================
# dataset.yaml must not expose final test
# ============================================================

yaml_text = DATASET_YAML.read_text(
    encoding="utf-8"
)


if "test_files.txt" in yaml_text:

    raise AssertionError(
        "Locked test manifest leaked into dataset.yaml."
    )


if "test:" in yaml_text:

    raise AssertionError(
        "dataset.yaml must not expose the locked final test."
    )


print(
    "PASS: Training dataset configuration excludes final test."
)


# ============================================================
# Load selected model
# ============================================================

model = YOLO(
    str(
        MODEL_FILE
    )
)


print(
    "PASS: Selected YOLO checkpoint loads."
)


# ============================================================
# Model class contract
# ============================================================

model_names = {
    int(class_id):
        str(class_name)

    for class_id, class_name
    in model.names.items()
}


assert model_names == EXPECTED_CLASSES


print(
    "PASS: SH17 17-class model vocabulary preserved."
)


# ============================================================
# Basic model identity
# ============================================================

if model.task != "detect":

    raise AssertionError(
        f"Expected detection model; found {model.task}"
    )


print(
    "PASS: PPE artifact is an object-detection model."
)


# ============================================================
# CUDA environment
# ============================================================

if not torch.cuda.is_available():

    raise AssertionError(
        "CUDA unavailable in PPE environment."
    )


gpu_name = torch.cuda.get_device_name(
    0
)


print(
    "PASS: CUDA PPE runtime available."
)

print(
    "GPU:",
    gpu_name,
)


# ============================================================
# Checkpoint size
# ============================================================

size_mb = (
    MODEL_FILE.stat().st_size
    / 1024**2
)


if size_mb <= 0:

    raise AssertionError(
        "PPE checkpoint is empty."
    )


print(
    f"PASS: PPE checkpoint size = {size_mb:.2f} MB."
)


# ============================================================
# Final-test manifest existence only
#
# IMPORTANT:
# We intentionally do not read its contents here.
# ============================================================

print(
    "PASS: Locked final-test manifest exists but was not read."
)


# ============================================================
# Summary
# ============================================================

print(
    "\n============================================"
)
print(
    "PPE MODEL ARTIFACT SUMMARY"
)
print(
    "============================================"
)

print(
    "Model:              YOLOv8n"
)

print(
    "Dataset:            SH17"
)

print(
    "Classes:            17"
)

print(
    "Image size:         640"
)

print(
    "Training epochs:    50"
)

print(
    "Batch size:         16"
)

print(
    "Seed:               42"
)

print(
    "Train images:       6479"
)

print(
    "Validation images:  810"
)

print(
    "Locked test images: 810"
)

print(
    "Locked test used:   NO"
)

print(
    f"Checkpoint:          {MODEL_FILE.name}"
)


print(
    "\n============================================"
)
print(
    "PPE MODEL ARTIFACT CONTRACT PASSED"
)
print(
    "============================================"
)