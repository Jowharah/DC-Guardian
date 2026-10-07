"""
DC-Guardian Phase 1
Face Recognition Final-Test Artifact Contract

Protects the locked controlled final-test result.

This test does NOT perform face recognition again.
It verifies the persisted final-test artifact and ensures
that the frozen threshold/enrollment contract was preserved.
"""

import json
from pathlib import Path


# ============================================================
# Paths
# ============================================================

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

FINAL_RESULT_FILE = (
    FACE_ROOT
    / "results"
    / "final_test"
    / "face_recognition_final_test.json"
)

FINAL_PREDICTIONS_FILE = (
    FACE_ROOT
    / "results"
    / "final_test"
    / "final_test_predictions.csv"
)


# ============================================================
# Frozen expected result
# ============================================================

EXPECTED_THRESHOLD = 0.50

EXPECTED_KNOWN = 6
EXPECTED_UNKNOWN = 9
EXPECTED_TOTAL = 15

EXPECTED_CORRECT_KNOWN = 6
EXPECTED_CORRECT_UNKNOWN = 9

EXPECTED_FALSE_ACCEPTANCES = 0
EXPECTED_FALSE_REJECTIONS = 0
EXPECTED_MISIDENTIFICATIONS = 0


# ============================================================
# Start
# ============================================================

print(
    "\n============================================"
)

print(
    "DC-GUARDIAN FACE FINAL TEST ARTIFACT TEST"
)

print(
    "============================================"
)


# ============================================================
# Artifacts exist
# ============================================================

assert CONFIG_FILE.is_file(), (
    f"Missing frozen configuration: "
    f"{CONFIG_FILE}"
)

assert FINAL_RESULT_FILE.is_file(), (
    f"Missing final result: "
    f"{FINAL_RESULT_FILE}"
)

assert FINAL_PREDICTIONS_FILE.is_file(), (
    f"Missing final predictions: "
    f"{FINAL_PREDICTIONS_FILE}"
)


print(
    "PASS: Final-test artifacts exist."
)


# ============================================================
# Load
# ============================================================

with CONFIG_FILE.open(
    "r",
    encoding="utf-8",
) as file:

    config = json.load(
        file
    )


with FINAL_RESULT_FILE.open(
    "r",
    encoding="utf-8",
) as file:

    result = json.load(
        file
    )


# ============================================================
# Frozen configuration
# ============================================================

assert (
    config[
        "configuration_frozen"
    ]
    is True
)

assert (
    config[
        "recognition_threshold"
    ]
    == EXPECTED_THRESHOLD
)

assert (
    config[
        "threshold_source"
    ]
    == "validation_only"
)


print(
    "PASS: Frozen threshold contract preserved."
)


# ============================================================
# Model identity
# ============================================================

assert (
    result[
        "model_name"
    ]
    == "ArcFace"
)

assert (
    result[
        "detector_backend"
    ]
    == "retinaface"
)

assert (
    result[
        "distance_metric"
    ]
    == "cosine"
)


print(
    "PASS: ArcFace/RetinaFace final-test identity."
)


# ============================================================
# Threshold preservation
# ============================================================

assert (
    result[
        "recognition_threshold"
    ]
    == EXPECTED_THRESHOLD
)

assert (
    result[
        "threshold_source"
    ]
    == "validation_only"
)

assert (
    result[
        "threshold_changed_during_final_test"
    ]
    is False
)

assert (
    result[
        "enrollment_changed_during_final_test"
    ]
    is False
)


print(
    "PASS: No final-test threshold selection."
)

print(
    "PASS: Enrollment remained frozen."
)


# ============================================================
# Final-test population
# ============================================================

assert (
    result[
        "known_test_images"
    ]
    == EXPECTED_KNOWN
)

assert (
    result[
        "unknown_test_images"
    ]
    == EXPECTED_UNKNOWN
)

assert (
    result[
        "total_test_images"
    ]
    == EXPECTED_TOTAL
)


print(
    "PASS: Locked final-test population preserved."
)


# ============================================================
# Known-person results
# ============================================================

assert (
    result[
        "correct_known_identifications"
    ]
    == EXPECTED_CORRECT_KNOWN
)

assert (
    result[
        "known_identification_rate"
    ]
    == 1.0
)

assert (
    result[
        "false_rejections"
    ]
    == EXPECTED_FALSE_REJECTIONS
)

assert (
    result[
        "false_rejection_rate"
    ]
    == 0.0
)

assert (
    result[
        "misidentifications"
    ]
    == EXPECTED_MISIDENTIFICATIONS
)

assert (
    result[
        "misidentification_rate"
    ]
    == 0.0
)


print(
    "PASS: Known-person final metrics preserved."
)


# ============================================================
# Unknown-person results
# ============================================================

assert (
    result[
        "correct_unknown_rejections"
    ]
    == EXPECTED_CORRECT_UNKNOWN
)

assert (
    result[
        "unknown_rejection_rate"
    ]
    == 1.0
)

assert (
    result[
        "false_acceptances"
    ]
    == EXPECTED_FALSE_ACCEPTANCES
)

assert (
    result[
        "false_acceptance_rate"
    ]
    == 0.0
)


print(
    "PASS: Unknown-person final metrics preserved."
)


# ============================================================
# Distance relationship
# ============================================================

known_max = float(
    result[
        "known_distance_max"
    ]
)

unknown_min = float(
    result[
        "unknown_distance_min"
    ]
)


assert (
    known_max
    < EXPECTED_THRESHOLD
)

assert (
    unknown_min
    > EXPECTED_THRESHOLD
)


print(
    "PASS: Final known/unknown distances remain "
    "on the expected sides of the frozen threshold."
)


# ============================================================
# Latency
# ============================================================

assert (
    result[
        "mean_latency_ms"
    ]
    > 0
)

assert (
    result[
        "median_latency_ms"
    ]
    > 0
)


print(
    "PASS: Final inference latency recorded."
)


# ============================================================
# Completion
# ============================================================

assert (
    result[
        "final_test_completed"
    ]
    is True
)


print(
    "PASS: Locked final evaluation marked complete."
)


# ============================================================
# Summary
# ============================================================

print(
    "\n============================================"
)

print(
    "FACE FINAL TEST CONTRACT SUMMARY"
)

print(
    "============================================"
)

print(
    "Known identification: ",
    f"{EXPECTED_CORRECT_KNOWN}/{EXPECTED_KNOWN}",
)

print(
    "Unknown rejection:    ",
    f"{EXPECTED_CORRECT_UNKNOWN}/{EXPECTED_UNKNOWN}",
)

print(
    "False acceptances:    ",
    EXPECTED_FALSE_ACCEPTANCES,
)

print(
    "False rejections:     ",
    EXPECTED_FALSE_REJECTIONS,
)

print(
    "Misidentifications:   ",
    EXPECTED_MISIDENTIFICATIONS,
)

print(
    "Frozen threshold:     ",
    EXPECTED_THRESHOLD,
)

print(
    "Known distance max:   ",
    f"{known_max:.6f}",
)

print(
    "Unknown distance min: ",
    f"{unknown_min:.6f}",
)

print(
    "Mean latency:         ",
    f"{result['mean_latency_ms']:.2f} ms",
)

print(
    "Median latency:       ",
    f"{result['median_latency_ms']:.2f} ms",
)


print(
    "\n============================================"
)

print(
    "FACE FINAL TEST ARTIFACT CONTRACT PASSED"
)

print(
    "============================================"
)