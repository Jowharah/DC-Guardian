"""
DC-Guardian Evidence
PPE Detection - Locked Final Evaluation

Runs the frozen PPE-v1 YOLOv8n detector exactly once against
the locked 810-image SH17 final-test population.

No training, fitting, model selection, threshold tuning,
or PPE-compliance policy selection occurs here.
"""

from pathlib import Path
import json
import time

import torch
import yaml
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
    / "evidence"
    / "ppe_detection"
)

MODEL_DIR = PPE_ROOT / "models"

PROCESSED_ROOT = (
    PPE_ROOT
    / "data"
    / "processed"
    / "sh17_yolo"
)

RAW_ROOT = (
    PPE_ROOT
    / "data"
    / "raw"
    / "SH17"
)

IMAGE_DIR = RAW_ROOT / "images"

MODEL_FILE = (
    MODEL_DIR
    / "ppe_yolov8_best.pt"
)

CONFIG_FILE = (
    MODEL_DIR
    / "ppe_config.json"
)

TEST_MANIFEST = (
    PROCESSED_ROOT
    / "test_files.txt"
)

RESULTS_DIR = (
    PPE_ROOT
    / "results"
    / "final_test"
)

TEST_IMAGE_LIST = (
    RESULTS_DIR
    / "locked_test_images.txt"
)

TEST_YAML = (
    RESULTS_DIR
    / "locked_test_dataset.yaml"
)

SUMMARY_FILE = (
    RESULTS_DIR
    / "ppe_final_test.json"
)


SH17_CLASS_NAMES = {
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


# ============================================================
# Start
# ============================================================

print(
    "\n============================================"
)
print(
    "DC-GUARDIAN PPE DETECTION"
)
print(
    "LOCKED FINAL TEST"
)
print(
    "============================================"
)


# ============================================================
# Frozen configuration
# ============================================================

config = json.loads(
    CONFIG_FILE.read_text(
        encoding="utf-8"
    )
)


if config["configuration_frozen"] is not True:

    raise AssertionError(
        "PPE detector configuration is not frozen."
    )


if (
    config[
        "locked_test_accessed_when_frozen"
    ]
    is not False
):

    raise AssertionError(
        "Locked test boundary was not preserved "
        "when the detector was frozen."
    )


if config["weights"] != MODEL_FILE.name:

    raise AssertionError(
        "Frozen weight filename mismatch."
    )


print(
    "PASS: Frozen PPE-v1 configuration loaded."
)

print(
    "Model:",
    config["architecture"],
)

print(
    "Image size:",
    config["image_size"],
)

print(
    "IMPORTANT:"
)

print(
    "No training, fitting, model selection, "
    "or PPE-policy selection will occur."
)


# ============================================================
# Unlock locked manifest
# ============================================================

test_names = [
    line.strip()
    for line in TEST_MANIFEST.read_text(
        encoding="utf-8"
    ).splitlines()
    if line.strip()
]


if len(test_names) != 810:

    raise AssertionError(
        "Locked final-test population mismatch. "
        f"Expected 810, found {len(test_names)}."
    )


test_paths = []


for image_name in test_names:

    image_path = (
        IMAGE_DIR
        / image_name
    )


    if not image_path.exists():

        raise FileNotFoundError(
            f"Locked test image missing: {image_path}"
        )


    test_paths.append(
        image_path.resolve()
    )


print(
    "PASS: Locked final-test population opened."
)

print(
    "Final-test images:",
    len(test_paths),
)


# ============================================================
# Build evaluation-only Ultralytics configuration
# ============================================================

RESULTS_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


TEST_IMAGE_LIST.write_text(
    "\n".join(
        str(path)
        for path in test_paths
    )
    + "\n",
    encoding="utf-8",
)


test_dataset_config = {
    "path": str(
        RAW_ROOT.resolve()
    ),

    # Ultralytics requires train/val keys in some versions.
    # Both point to the locked TEST list for this standalone
    # evaluation-only YAML. No training is invoked.
    "train": str(
        TEST_IMAGE_LIST.resolve()
    ),

    "val": str(
        TEST_IMAGE_LIST.resolve()
    ),

    "test": str(
        TEST_IMAGE_LIST.resolve()
    ),

    "nc": 17,

    "names": [
        SH17_CLASS_NAMES[
            class_id
        ]
        for class_id in range(17)
    ],
}


with TEST_YAML.open(
    "w",
    encoding="utf-8",
) as file:

    yaml.safe_dump(
        test_dataset_config,
        file,
        sort_keys=False,
    )


print(
    "PASS: Evaluation-only test configuration created."
)


# ============================================================
# Load frozen model
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


if model_names != SH17_CLASS_NAMES:

    raise AssertionError(
        "Frozen model class vocabulary changed."
    )


print(
    "PASS: Frozen YOLOv8n checkpoint loaded."
)


# ============================================================
# Locked evaluation
# ============================================================

if not torch.cuda.is_available():

    raise RuntimeError(
        "CUDA unavailable for PPE final evaluation."
    )


start = time.perf_counter()


metrics = model.val(
    data=str(TEST_YAML),
    split="test",
    imgsz=config["image_size"],
    batch=config["batch_size"],
    device=0,
    workers=0,
    plots=True,
    project=str(RESULTS_DIR),
    name="ultralytics_eval",
    exist_ok=True,
    verbose=True,
)


elapsed_seconds = (
    time.perf_counter()
    - start
)


print(
    "PASS: Locked final evaluation completed."
)


# ============================================================
# Overall metrics
# ============================================================

precision = float(
    metrics.box.mp
)

recall = float(
    metrics.box.mr
)

map50 = float(
    metrics.box.map50
)

map50_95 = float(
    metrics.box.map
)


# ============================================================
# Per-class metrics
# ============================================================

per_class = {}


for class_id, class_name in (
    SH17_CLASS_NAMES.items()
):

    # Ultralytics Results stores AP arrays indexed by class.
    ap50 = float(
        metrics.box.ap50[
            class_id
        ]
    )

    ap50_95 = float(
        metrics.box.ap[
            class_id
        ]
    )


    # class_result returns:
    # precision, recall, AP50, AP50-95
    class_result = (
        metrics.box.class_result(
            class_id
        )
    )


    class_precision = float(
        class_result[0]
    )

    class_recall = float(
        class_result[1]
    )


    per_class[
        class_name
    ] = {
        "class_id":
            class_id,

        "precision":
            class_precision,

        "recall":
            class_recall,

        "map50":
            ap50,

        "map50_95":
            ap50_95,
    }


# ============================================================
# Runtime information
# ============================================================

speed = {
    key:
        float(value)

    for key, value
    in metrics.speed.items()
}


# ============================================================
# Save immutable result summary
# ============================================================

summary = {
    "evaluation": "LOCKED_FINAL_TEST",

    "evaluation_complete": True,

    "configuration_version":
        config["configuration_version"],

    "configuration_frozen": True,

    "model_family":
        config["model_family"],

    "architecture":
        config["architecture"],

    "weights":
        config["weights"],

    "dataset":
        config["dataset"],

    "image_size":
        config["image_size"],

    "class_count": 17,

    "final_test_images":
        len(test_paths),

    "training_performed":
        False,

    "model_selection_performed":
        False,

    "threshold_selection_performed":
        False,

    "compliance_policy_selection_performed":
        False,

    "overall": {
        "precision":
            precision,

        "recall":
            recall,

        "map50":
            map50,

        "map50_95":
            map50_95,
    },

    "per_class":
        per_class,

    "speed_ms_per_image":
        speed,

    "evaluation_elapsed_seconds":
        elapsed_seconds,

    "gpu":
        torch.cuda.get_device_name(
            0
        ),
}


SUMMARY_FILE.write_text(
    json.dumps(
        summary,
        indent=2,
    ),
    encoding="utf-8",
)


# ============================================================
# Display
# ============================================================

print(
    "\n============================================"
)
print(
    "FINAL LOCKED PPE DETECTION RESULTS"
)
print(
    "============================================"
)

print(
    f"Precision:      {precision:.4f}"
)

print(
    f"Recall:         {recall:.4f}"
)

print(
    f"mAP@0.5:        {map50:.4f}"
)

print(
    f"mAP@0.5:0.95:   {map50_95:.4f}"
)


print(
    "\nPer-class results:"
)


for class_name, values in (
    per_class.items()
):

    print(
        f"{class_name:<20} "
        f"P={values['precision']:.3f} "
        f"R={values['recall']:.3f} "
        f"mAP50={values['map50']:.3f} "
        f"mAP50-95={values['map50_95']:.3f}"
    )


print(
    "\nRuntime:"
)

for key, value in speed.items():

    print(
        f"  {key}: {value:.3f} ms/image"
    )


print(
    f"\nEvaluation elapsed: "
    f"{elapsed_seconds:.2f} seconds"
)


print(
    "\nFrozen detector changed: NO"
)

print(
    "Training performed: NO"
)

print(
    "Model selection performed: NO"
)

print(
    "PPE compliance policy selected: NO"
)


print(
    "\nSaved:",
    SUMMARY_FILE,
)


print(
    "\n============================================"
)
print(
    "LOCKED PPE FINAL EVALUATION COMPLETE"
)
print(
    "============================================"
)
