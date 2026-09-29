"""
DC-Guardian Phase 1
Face Recognition Runtime Pipeline Contract Test

Verifies that the frozen runtime pipeline reproduces
expected decisions for one known and one unknown image.

No fitting, enrollment, or threshold selection occurs.
"""

from phase1.face_recognition.src.config import (
    TEST_KNOWN_DIR,
    TEST_UNKNOWN_DIR,
)

from phase1.face_recognition.src.face_pipeline import (
    FaceRecognitionPipeline,
)


print(
    "\n============================================"
)

print(
    "DC-GUARDIAN FACE RUNTIME PIPELINE TEST"
)

print(
    "============================================"
)


# ============================================================
# Initialize frozen runtime
# ============================================================

pipeline = (
    FaceRecognitionPipeline()
)


assert (
    pipeline.threshold
    == 0.50
)


print(
    "PASS: Frozen face pipeline loaded."
)

print(
    "PASS: Recognition threshold = 0.50."
)


# ============================================================
# Known test case
# ============================================================

known_image = (
    TEST_KNOWN_DIR
    / "P001"
    / "P001_test_01.jpg"
)


known_result = (
    pipeline.recognize(
        known_image
    )
)


assert (
    known_result[
        "domain"
    ]
    == "PHYSICAL_SECURITY"
)

assert (
    known_result[
        "event_type"
    ]
    == "FACE_IDENTIFICATION_ASSESSMENT"
)

assert (
    known_result[
        "person_id"
    ]
    == "P001"
)

assert (
    known_result[
        "recognition_status"
    ]
    == "RECOGNIZED"
)

assert (
    known_result[
        "face_detected"
    ]
    is True
)

assert (
    known_result[
        "face_count"
    ]
    == 1
)

assert (
    known_result[
        "distance"
    ]
    <= 0.50
)

assert (
    known_result[
        "nearest_employee_id"
    ]
    == "P001"
)


print(
    "\nPASS: Known employee recognized."
)

print(
    "  Person:",
    known_result[
        "person_id"
    ],
)

print(
    "  Distance:",
    f"{known_result['distance']:.6f}",
)

print(
    "  Status:",
    known_result[
        "recognition_status"
    ],
)


# ============================================================
# Unknown test case
# ============================================================

unknown_image = (
    TEST_UNKNOWN_DIR
    / "U005"
    / "U005_test_02.jpg"
)


unknown_result = (
    pipeline.recognize(
        unknown_image
    )
)


assert (
    unknown_result[
        "domain"
    ]
    == "PHYSICAL_SECURITY"
)

assert (
    unknown_result[
        "person_id"
    ]
    == "UNKNOWN"
)

assert (
    unknown_result[
        "recognition_status"
    ]
    == "UNKNOWN"
)

assert (
    unknown_result[
        "face_detected"
    ]
    is True
)

assert (
    unknown_result[
        "face_count"
    ]
    == 1
)

assert (
    unknown_result[
        "distance"
    ]
    > 0.50
)


print(
    "\nPASS: Unenrolled person rejected."
)

print(
    "  Person:",
    unknown_result[
        "person_id"
    ],
)

print(
    "  Nearest enrolled identity:",
    unknown_result[
        "nearest_employee_id"
    ],
)

print(
    "  Distance:",
    f"{unknown_result['distance']:.6f}",
)

print(
    "  Status:",
    unknown_result[
        "recognition_status"
    ],
)


# ============================================================
# Frozen runtime metadata
# ============================================================

for result in [
    known_result,
    unknown_result,
]:

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

    assert (
        result[
            "threshold"
        ]
        == 0.50
    )

    assert (
        result[
            "threshold_source"
        ]
        == "validation_only"
    )

    assert (
        result[
            "configuration_frozen"
        ]
        is True
    )

    assert (
        result[
            "latency_ms"
        ]
        > 0
    )


print(
    "\nPASS: Frozen model metadata preserved."
)

print(
    "PASS: Runtime latency recorded."
)

print(
    "PASS: No fitting or threshold selection "
    "performed."
)


# ============================================================
# Summary
# ============================================================

print(
    "\n============================================"
)

print(
    "FACE RUNTIME OUTPUT"
)

print(
    "============================================"
)


print(
    "Known:"
)

print(
    known_result
)


print(
    "\nUnknown:"
)

print(
    unknown_result
)


print(
    "\n============================================"
)

print(
    "FACE RUNTIME PIPELINE CONTRACT PASSED"
)

print(
    "============================================"
)