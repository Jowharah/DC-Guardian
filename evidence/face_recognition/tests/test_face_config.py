"""
DC-Guardian Phase 1
Frozen Face Recognition Configuration Contract
"""

import json
from pathlib import Path


FACE_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

CONFIG_FILE = (
    FACE_ROOT
    / "models"
    / "face_recognition_config.json"
)


print(
    "\n============================================"
)

print(
    "DC-GUARDIAN FACE CONFIG CONTRACT TEST"
)

print(
    "============================================"
)


assert CONFIG_FILE.is_file()


with CONFIG_FILE.open(
    "r",
    encoding="utf-8",
) as file:

    config = json.load(file)


print(
    "PASS: Frozen configuration exists."
)


assert (
    config[
        "artifact_type"
    ]
    == "DC_GUARDIAN_FACE_RECOGNITION_CONFIG"
)

assert (
    config[
        "artifact_version"
    ]
    == "1.0"
)

assert (
    config[
        "model_name"
    ]
    == "ArcFace"
)

assert (
    config[
        "detector_backend"
    ]
    == "retinaface"
)

assert (
    config[
        "distance_metric"
    ]
    == "cosine"
)

assert (
    config[
        "embedding_dimension"
    ]
    == 512
)


print(
    "PASS: ArcFace/RetinaFace contract."
)


assert (
    config[
        "recognition_threshold"
    ]
    == 0.50
)

assert (
    config[
        "decision_rule"
    ]
    == "distance <= threshold"
)

assert (
    config[
        "threshold_source"
    ]
    == "validation_only"
)

assert (
    config[
        "configuration_frozen"
    ]
    is True
)


print(
    "PASS: Recognition threshold = 0.50."
)

print(
    "PASS: Threshold source = validation only."
)


known_max = config[
    "validation_known_distance_max"
]

unknown_min = config[
    "validation_unknown_distance_min"
]

threshold = config[
    "recognition_threshold"
]


assert (
    known_max
    < threshold
    < unknown_min
)


print(
    "PASS: Frozen threshold lies inside "
    "observed validation separation."
)


assert (
    config[
        "validation_known_identification"
    ]
    == "7/7"
)

assert (
    config[
        "validation_unknown_rejection"
    ]
    == "6/6"
)

assert (
    config[
        "validation_false_acceptances"
    ]
    == 0
)

assert (
    config[
        "validation_false_rejections"
    ]
    == 0
)

assert (
    config[
        "validation_misidentifications"
    ]
    == 0
)


print(
    "PASS: Validation operating-point "
    "results preserved."
)


assert (
    config[
        "final_test_accessed"
    ]
    is False
)


print(
    "PASS: Final-test data remained untouched "
    "when configuration was frozen."
)


print(
    "\n============================================"
)

print(
    "FACE CONFIGURATION SUMMARY"
)

print(
    "============================================"
)

print(
    "Model:      ",
    config[
        "model_name"
    ],
)

print(
    "Detector:   ",
    config[
        "detector_backend"
    ],
)

print(
    "Metric:     ",
    config[
        "distance_metric"
    ],
)

print(
    "Threshold:  ",
    config[
        "recognition_threshold"
    ],
)

print(
    "Known max:  ",
    f"{known_max:.6f}",
)

print(
    "Unknown min:",
    f"{unknown_min:.6f}",
)


print(
    "\n============================================"
)

print(
    "FACE CONFIG CONTRACT PASSED"
)

print(
    "============================================"
)