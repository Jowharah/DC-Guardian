"""
DC-Guardian Evidence
PPE Locked Final-Test Artifact Contract

Verifies that the frozen PPE-v1 detector was evaluated against
the locked SH17 final-test population without training,
model selection, threshold tuning, or compliance-policy tuning.
"""

from pathlib import Path
import json
import math


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

FINAL_RESULT_FILE = (
    PPE_ROOT
    / "results"
    / "final_test"
    / "ppe_final_test.json"
)


EXPECTED_CLASSES = {
    "person",
    "ear",
    "ear-mufs",
    "face",
    "face-guard",
    "face-mask-medical",
    "foot",
    "tools",
    "glasses",
    "gloves",
    "helmet",
    "hands",
    "head",
    "medical-suit",
    "shoes",
    "safety-suit",
    "safety-vest",
}


# These are the locked final-test results already produced by
# the frozen PPE-v1 detector.
EXPECTED_PRECISION = 0.6889
EXPECTED_RECALL = 0.5241
EXPECTED_MAP50 = 0.5447
EXPECTED_MAP50_95 = 0.3363

METRIC_TOLERANCE = 0.0001


def close_enough(
    actual,
    expected,
    tolerance=METRIC_TOLERANCE,
):

    return math.isclose(
        actual,
        expected,
        abs_tol=tolerance,
        rel_tol=0.0,
    )


print(
    "\n============================================"
)
print(
    "DC-GUARDIAN PPE FINAL TEST ARTIFACT TEST"
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
    FINAL_RESULT_FILE,
]:

    if not path.exists():

        raise AssertionError(
            f"Required PPE final artifact missing: {path}"
        )


print(
    "PASS: Final-test artifacts exist."
)


# ============================================================
# Load artifacts
# ============================================================

config = json.loads(
    CONFIG_FILE.read_text(
        encoding="utf-8"
    )
)

result = json.loads(
    FINAL_RESULT_FILE.read_text(
        encoding="utf-8"
    )
)


# ============================================================
# Frozen detector identity
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
    result["configuration_version"]
    == "PPE-v1"
)

assert (
    result["configuration_frozen"]
    is True
)

assert (
    result["model_family"]
    == "YOLOv8"
)

assert (
    result["architecture"]
    == "YOLOv8n"
)

assert (
    result["weights"]
    == "ppe_yolov8_best.pt"
)

assert (
    result["dataset"]
    == "SH17"
)

assert (
    result["image_size"]
    == 640
)

assert (
    result["class_count"]
    == 17
)


print(
    "PASS: Frozen PPE-v1 detector identity preserved."
)


# ============================================================
# Locked evaluation identity
# ============================================================

assert (
    result["evaluation"]
    == "LOCKED_FINAL_TEST"
)

assert (
    result["evaluation_complete"]
    is True
)

assert (
    result["final_test_images"]
    == 810
)


print(
    "PASS: Locked 810-image final-test population preserved."
)


# ============================================================
# No development during final test
# ============================================================

assert (
    result["training_performed"]
    is False
)

assert (
    result["model_selection_performed"]
    is False
)

assert (
    result["threshold_selection_performed"]
    is False
)

assert (
    result[
        "compliance_policy_selection_performed"
    ]
    is False
)


print(
    "PASS: No training performed during final evaluation."
)

print(
    "PASS: No model selection performed during final evaluation."
)

print(
    "PASS: No threshold selection performed during final evaluation."
)

print(
    "PASS: No PPE compliance-policy selection performed."
)


# ============================================================
# Overall final metrics
# ============================================================

overall = result[
    "overall"
]


for metric_name in [
    "precision",
    "recall",
    "map50",
    "map50_95",
]:

    metric_value = float(
        overall[
            metric_name
        ]
    )


    if not (
        0.0
        <= metric_value
        <= 1.0
    ):

        raise AssertionError(
            f"Invalid {metric_name}: {metric_value}"
        )


if not close_enough(
    float(
        overall["precision"]
    ),
    EXPECTED_PRECISION,
):

    raise AssertionError(
        "Locked precision changed."
    )


if not close_enough(
    float(
        overall["recall"]
    ),
    EXPECTED_RECALL,
):

    raise AssertionError(
        "Locked recall changed."
    )


if not close_enough(
    float(
        overall["map50"]
    ),
    EXPECTED_MAP50,
):

    raise AssertionError(
        "Locked mAP@0.5 changed."
    )


if not close_enough(
    float(
        overall["map50_95"]
    ),
    EXPECTED_MAP50_95,
):

    raise AssertionError(
        "Locked mAP@0.5:0.95 changed."
    )


print(
    "PASS: Locked overall PPE metrics preserved."
)


# ============================================================
# Per-class results
# ============================================================

per_class = result[
    "per_class"
]


if set(
    per_class
) != EXPECTED_CLASSES:

    raise AssertionError(
        "Final per-class vocabulary mismatch."
    )


for class_name, metrics in (
    per_class.items()
):

    expected_class_id = {
        "person": 0,
        "ear": 1,
        "ear-mufs": 2,
        "face": 3,
        "face-guard": 4,
        "face-mask-medical": 5,
        "foot": 6,
        "tools": 7,
        "glasses": 8,
        "gloves": 9,
        "helmet": 10,
        "hands": 11,
        "head": 12,
        "medical-suit": 13,
        "shoes": 14,
        "safety-suit": 15,
        "safety-vest": 16,
    }[
        class_name
    ]


    assert (
        metrics["class_id"]
        == expected_class_id
    )


    for metric_name in [
        "precision",
        "recall",
        "map50",
        "map50_95",
    ]:

        value = float(
            metrics[
                metric_name
            ]
        )


        if not (
            0.0
            <= value
            <= 1.0
        ):

            raise AssertionError(
                f"{class_name} has invalid "
                f"{metric_name}: {value}"
            )


print(
    "PASS: All 17 per-class final metrics preserved."
)


# ============================================================
# Runtime
# ============================================================

speed = result[
    "speed_ms_per_image"
]


for key in [
    "preprocess",
    "inference",
    "postprocess",
]:

    if key not in speed:

        raise AssertionError(
            f"Missing runtime component: {key}"
        )


    if float(
        speed[
            key
        ]
    ) < 0:

        raise AssertionError(
            f"Invalid runtime value for {key}."
        )


if float(
    result[
        "evaluation_elapsed_seconds"
    ]
) <= 0:

    raise AssertionError(
        "Final evaluation elapsed time invalid."
    )


print(
    "PASS: Final inference runtime recorded."
)


# ============================================================
# Compliance boundary
# ============================================================

assert (
    config[
        "compliance_policy_frozen"
    ]
    is False
)


print(
    "PASS: Detector evaluation remains separate "
    "from PPE compliance policy."
)


# ============================================================
# Summary
# ============================================================

print(
    "\n============================================"
)
print(
    "PPE FINAL TEST CONTRACT SUMMARY"
)
print(
    "============================================"
)

print(
    f"Final images:       "
    f"{result['final_test_images']}"
)

print(
    f"Precision:          "
    f"{overall['precision']:.4f}"
)

print(
    f"Recall:             "
    f"{overall['recall']:.4f}"
)

print(
    f"mAP@0.5:            "
    f"{overall['map50']:.4f}"
)

print(
    f"mAP@0.5:0.95:       "
    f"{overall['map50_95']:.4f}"
)

print(
    f"Inference:          "
    f"{speed['inference']:.3f} ms/image"
)

print(
    f"Evaluation elapsed: "
    f"{result['evaluation_elapsed_seconds']:.2f} s"
)

print(
    "Detector frozen:    YES"
)

print(
    "PPE policy frozen:  NO"
)


print(
    "\n============================================"
)
print(
    "PPE FINAL TEST ARTIFACT CONTRACT PASSED"
)
print(
    "============================================"
)
