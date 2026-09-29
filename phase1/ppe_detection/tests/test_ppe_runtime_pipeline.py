"""
DC-Guardian Phase 1
PPE Runtime Pipeline Diagnostic

Uses development-validation images only.
Does not access the locked final-test manifest.
"""

from pathlib import Path

from phase1.ppe_detection.src.ppe_pipeline import (
    PPECompliancePipeline,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]

PPE_ROOT = (
    PROJECT_ROOT
    / "phase1"
    / "ppe_detection"
)

RAW_IMAGE_DIR = (
    PPE_ROOT
    / "data"
    / "raw"
    / "SH17"
    / "images"
)

VALIDATION_MANIFEST = (
    PPE_ROOT
    / "data"
    / "processed"
    / "sh17_yolo"
    / "validation_files.txt"
)


print(
    "\n============================================"
)
print(
    "DC-GUARDIAN PPE RUNTIME PIPELINE TEST"
)
print(
    "============================================"
)


pipeline = PPECompliancePipeline()


print(
    "PASS: Frozen PPE detector loaded."
)


validation_names = [
    line.strip()
    for line
    in VALIDATION_MANIFEST.read_text(
        encoding="utf-8"
    ).splitlines()
    if line.strip()
]


if len(validation_names) != 810:
    raise AssertionError(
        "Development-validation population changed."
    )


print(
    "PASS: Development validation population loaded."
)

print(
    "PASS: Locked final-test manifest not accessed."
)


# Use several development images rather than relying on
# one arbitrary frame.
sample_names = validation_names[
    :10
]


valid_statuses = {
    "COMPLIANT",
    "NON_COMPLIANT",
    "NO_PERSON",
}


status_counts = {
    status: 0
    for status
    in valid_statuses
}


for image_name in sample_names:

    image_path = (
        RAW_IMAGE_DIR
        / image_name
    )


    assessment = pipeline.assess(
        image_path
    )


    status = assessment[
        "overall_status"
    ]


    if status not in valid_statuses:
        raise AssertionError(
            f"Unexpected PPE status: {status}"
        )


    status_counts[
        status
    ] += 1


    if (
        assessment[
            "domain"
        ]
        != "PHYSICAL_SECURITY"
    ):
        raise AssertionError(
            "PPE runtime domain changed."
        )


    if (
        assessment[
            "event_type"
        ]
        != "PPE_COMPLIANCE_ASSESSMENT"
    ):
        raise AssertionError(
            "PPE runtime event type changed."
        )


    if (
        assessment[
            "detector_configuration_frozen"
        ]
        is not True
    ):
        raise AssertionError(
            "Frozen detector flag missing."
        )

    # ============================================================
    # Verify frozen runtime configuration
    # ============================================================

    if (
        assessment[
            "policy_frozen"
        ]
        is not True
    ):
        raise AssertionError(
            "Frozen PPE policy flag missing."
        )


    assert (
        assessment[
            "confidence_threshold"
        ]
        == 0.25
    )

    assert (
        assessment[
            "iou_threshold"
        ]
        == 0.70
    )

    assert (
        assessment[
            "association_minimum_containment"
        ]
        == 0.50
    )


    if (
        assessment[
            "latency_ms"
        ]
        <= 0
    ):
        raise AssertionError(
            "Runtime latency not recorded."
        )


    if assessment[
        "latency_ms"
    ] <= 0:

        raise AssertionError(
            "Runtime latency not recorded."
        )


    print()

    print(
        image_name
    )

    print(
        "  Persons:",
        assessment[
            "person_count"
        ],
    )

    print(
        "  Status:",
        status,
    )

    print(
        "  Detections:",
        len(
            assessment[
                "detections"
            ]
        ),
    )

    print(
        "  Unassigned:",
        len(
            assessment[
                "unassigned_detections"
            ]
        ),
    )

    print(
        "  Latency:",
        f"{assessment['latency_ms']:.2f} ms",
    )


print(
    "\n============================================"
)
print(
    "PPE RUNTIME DIAGNOSTIC SUMMARY"
)
print(
    "============================================"
)

for status in [
    "COMPLIANT",
    "NON_COMPLIANT",
    "NO_PERSON",
]:

    print(
        f"{status}: "
        f"{status_counts[status]}"
    )


print(
    "\nPASS: Frozen detector used."
)

print(
    "PASS: Development validation only."
)

print(
    "PASS: Structured PPE assessments produced."
)

print(
    "PASS: Runtime latency recorded."
)

print(
    "PASS: Frozen confidence threshold = 0.25."
)

print(
    "PASS: Frozen IoU threshold = 0.70."
)

print(
    "PASS: Frozen association containment = 0.50."
)

print(
    "PASS: PPE-POLICY-v1 remains frozen."
)


print(
    "\n============================================"
)

print(
    "PPE RUNTIME PIPELINE CONTRACT PASSED"
)

print(
    "============================================"
)