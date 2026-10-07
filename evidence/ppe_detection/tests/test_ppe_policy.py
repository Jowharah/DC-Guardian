"""
DC-Guardian Phase 1
PPE Compliance Policy Contract
"""

from evidence.ppe_detection.src.ppe_policy import (
    POLICY_NAME,
    POLICY_VERSION,
    REQUIRED_PPE,
    evaluate_ppe_policy,
)


def person(
    index,
    classes,
):

    return {
        "person_index":
            index,

        "person_detection": {
            "class_id": 0,
            "class_name": "person",
            "confidence": 0.95,
            "bbox_xyxy": [
                0.0,
                0.0,
                100.0,
                200.0,
            ],
        },

        "associated_detections": [
            {
                "class_id": -1,
                "class_name": class_name,
                "confidence": 0.90,
                "bbox_xyxy": [
                    10.0,
                    10.0,
                    50.0,
                    50.0,
                ],
            }

            for class_name
            in classes
        ],
    }


def association(
    people,
):

    return {
        "people":
            people,

        "unassigned_detections":
            [],
    }


print(
    "\n============================================"
)
print(
    "DC-GUARDIAN PPE POLICY TEST"
)
print(
    "============================================"
)


# ============================================================
# Policy identity
# ============================================================

assert (
    POLICY_VERSION
    == "PPE-POLICY-v1"
)

assert (
    POLICY_NAME
    == "BASELINE_DC_MAINTENANCE"
)

assert (
    REQUIRED_PPE
    == (
        "helmet",
        "safety-vest",
    )
)


print(
    "PASS: PPE policy identity preserved."
)


# ============================================================
# No person
# ============================================================

result = evaluate_ppe_policy(
    association(
        []
    )
)


assert (
    result[
        "overall_status"
    ]
    == "NO_PERSON"
)

assert (
    result[
        "person_detected"
    ]
    is False
)

assert (
    result[
        "person_count"
    ]
    == 0
)


print(
    "PASS: No person -> NO_PERSON."
)


# ============================================================
# Fully compliant person
# ============================================================

result = evaluate_ppe_policy(
    association(
        [
            person(
                0,
                [
                    "helmet",
                    "safety-vest",
                ],
            )
        ]
    )
)


assert (
    result[
        "overall_status"
    ]
    == "COMPLIANT"
)

assert (
    result[
        "people"
    ][0][
        "status"
    ]
    == "COMPLIANT"
)

assert (
    result[
        "people"
    ][0][
        "required_ppe_not_detected"
    ]
    == []
)


print(
    "PASS: Helmet + safety vest -> COMPLIANT."
)


# ============================================================
# Missing vest
# ============================================================

result = evaluate_ppe_policy(
    association(
        [
            person(
                0,
                [
                    "helmet",
                ],
            )
        ]
    )
)


assert (
    result[
        "overall_status"
    ]
    == "NON_COMPLIANT"
)

assert (
    result[
        "people"
    ][0][
        "required_ppe_not_detected"
    ]
    == [
        "safety-vest"
    ]
)


print(
    "PASS: Safety vest not detected -> NON_COMPLIANT."
)


# ============================================================
# Missing helmet
# ============================================================

result = evaluate_ppe_policy(
    association(
        [
            person(
                0,
                [
                    "safety-vest",
                ],
            )
        ]
    )
)


assert (
    result[
        "overall_status"
    ]
    == "NON_COMPLIANT"
)

assert (
    result[
        "people"
    ][0][
        "required_ppe_not_detected"
    ]
    == [
        "helmet"
    ]
)


print(
    "PASS: Helmet not detected -> NON_COMPLIANT."
)


# ============================================================
# Missing both
# ============================================================

result = evaluate_ppe_policy(
    association(
        [
            person(
                0,
                [],
            )
        ]
    )
)


assert (
    result[
        "overall_status"
    ]
    == "NON_COMPLIANT"
)

assert (
    result[
        "people"
    ][0][
        "required_ppe_not_detected"
    ]
    == [
        "helmet",
        "safety-vest",
    ]
)


print(
    "PASS: Required PPE not detected -> NON_COMPLIANT."
)


# ============================================================
# Optional PPE does not substitute for required PPE
# ============================================================

result = evaluate_ppe_policy(
    association(
        [
            person(
                0,
                [
                    "gloves",
                    "glasses",
                    "shoes",
                ],
            )
        ]
    )
)


assert (
    result[
        "overall_status"
    ]
    == "NON_COMPLIANT"
)

assert (
    result[
        "people"
    ][0][
        "required_ppe_not_detected"
    ]
    == [
        "helmet",
        "safety-vest",
    ]
)


print(
    "PASS: Optional PPE does not satisfy required PPE."
)


# ============================================================
# Optional PPE preserved as evidence
# ============================================================

result = evaluate_ppe_policy(
    association(
        [
            person(
                0,
                [
                    "helmet",
                    "safety-vest",
                    "gloves",
                    "glasses",
                ],
            )
        ]
    )
)


assert (
    result[
        "overall_status"
    ]
    == "COMPLIANT"
)

assert set(
    result[
        "people"
    ][0][
        "optional_ppe_detected"
    ]
) == {
    "gloves",
    "glasses",
}


print(
    "PASS: Optional PPE preserved as evidence."
)


# ============================================================
# Multiple people
# ============================================================

result = evaluate_ppe_policy(
    association(
        [
            person(
                0,
                [
                    "helmet",
                    "safety-vest",
                ],
            ),

            person(
                1,
                [
                    "helmet",
                ],
            ),
        ]
    )
)


assert (
    result[
        "person_count"
    ]
    == 2
)

assert (
    result[
        "people"
    ][0][
        "status"
    ]
    == "COMPLIANT"
)

assert (
    result[
        "people"
    ][1][
        "status"
    ]
    == "NON_COMPLIANT"
)

assert (
    result[
        "overall_status"
    ]
    == "NON_COMPLIANT"
)


print(
    "PASS: One non-compliant person makes "
    "overall scene NON_COMPLIANT."
)


# ============================================================
# Multiple compliant people
# ============================================================

result = evaluate_ppe_policy(
    association(
        [
            person(
                0,
                [
                    "helmet",
                    "safety-vest",
                ],
            ),

            person(
                1,
                [
                    "helmet",
                    "safety-vest",
                    "gloves",
                ],
            ),
        ]
    )
)


assert (
    result[
        "overall_status"
    ]
    == "COMPLIANT"
)


print(
    "PASS: All compliant people -> overall COMPLIANT."
)


print(
    "\n============================================"
)
print(
    "PPE POLICY CONTRACT SUMMARY"
)
print(
    "============================================"
)

print(
    "Policy: PPE-POLICY-v1"
)

print(
    "Profile: BASELINE_DC_MAINTENANCE"
)

print(
    "Required: helmet + safety-vest"
)

print(
    "PASS: COMPLIANT semantics."
)

print(
    "PASS: NON_COMPLIANT semantics."
)

print(
    "PASS: NO_PERSON semantics."
)

print(
    "PASS: Multi-person semantics."
)

print(
    "PASS: Optional PPE evidence preserved."
)


print(
    "\n============================================"
)
print(
    "PPE POLICY CONTRACT PASSED"
)
print(
    "============================================"
)
