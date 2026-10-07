"""
DC-Guardian Phase 1
PPE Person-Object Association Contract
"""

from evidence.ppe_detection.src.ppe_association import (
    associate_ppe_to_people,
    containment_ratio,
)


def detection(
    class_id,
    class_name,
    confidence,
    box,
):

    return {
        "class_id":
            class_id,

        "class_name":
            class_name,

        "confidence":
            confidence,

        "bbox_xyxy":
            box,
    }


print(
    "\n============================================"
)
print(
    "DC-GUARDIAN PPE ASSOCIATION TEST"
)
print(
    "============================================"
)


# ============================================================
# Containment sanity check
# ============================================================

ratio = containment_ratio(
    [20, 20, 40, 40],
    [0, 0, 100, 200],
)


assert ratio == 1.0


print(
    "PASS: PPE containment calculation."
)


# ============================================================
# One person
# ============================================================

result = associate_ppe_to_people(
    [
        detection(
            0,
            "person",
            0.95,
            [0, 0, 100, 200],
        ),

        detection(
            10,
            "helmet",
            0.90,
            [20, 5, 70, 45],
        ),

        detection(
            16,
            "safety-vest",
            0.88,
            [20, 60, 80, 140],
        ),
    ]
)


assert len(
    result["people"]
) == 1


associated_classes = {
    item["class_name"]
    for item
    in result[
        "people"
    ][0][
        "associated_detections"
    ]
}


assert associated_classes == {
    "helmet",
    "safety-vest",
}


assert not result[
    "unassigned_detections"
]


print(
    "PASS: Helmet and vest associated "
    "with one person."
)


# ============================================================
# Two separated people
# ============================================================

result = associate_ppe_to_people(
    [
        detection(
            0,
            "person",
            0.96,
            [0, 0, 100, 200],
        ),

        detection(
            0,
            "person",
            0.97,
            [200, 0, 300, 200],
        ),

        # Person 0
        detection(
            10,
            "helmet",
            0.91,
            [20, 5, 70, 45],
        ),

        detection(
            16,
            "safety-vest",
            0.89,
            [20, 60, 80, 140],
        ),

        # Person 1
        detection(
            10,
            "helmet",
            0.87,
            [220, 5, 270, 45],
        ),
    ]
)


assert len(
    result["people"]
) == 2


person_0_classes = {
    item["class_name"]
    for item
    in result[
        "people"
    ][0][
        "associated_detections"
    ]
}


person_1_classes = {
    item["class_name"]
    for item
    in result[
        "people"
    ][1][
        "associated_detections"
    ]
}


assert person_0_classes == {
    "helmet",
    "safety-vest",
}


assert person_1_classes == {
    "helmet",
}


print(
    "PASS: PPE kept separate across two people."
)


# ============================================================
# PPE outside every person
# ============================================================

result = associate_ppe_to_people(
    [
        detection(
            0,
            "person",
            0.95,
            [0, 0, 100, 200],
        ),

        detection(
            10,
            "helmet",
            0.90,
            [250, 10, 300, 50],
        ),
    ]
)


assert len(
    result[
        "people"
    ][0][
        "associated_detections"
    ]
) == 0


assert len(
    result[
        "unassigned_detections"
    ]
) == 1


assert (
    result[
        "unassigned_detections"
    ][0][
        "unassigned_reason"
    ]
    == "NO_PERSON_MATCH"
)


print(
    "PASS: Unrelated PPE not assigned to person."
)


# ============================================================
# No person
# ============================================================

result = associate_ppe_to_people(
    [
        detection(
            10,
            "helmet",
            0.90,
            [20, 5, 70, 45],
        )
    ]
)


assert result[
    "people"
] == []


assert len(
    result[
        "unassigned_detections"
    ]
) == 1


print(
    "PASS: PPE without a detected person remains unassigned."
)


# ============================================================
# Overlapping people
# ============================================================

result = associate_ppe_to_people(
    [
        detection(
            0,
            "person",
            0.95,
            [0, 0, 150, 220],
        ),

        detection(
            0,
            "person",
            0.94,
            [100, 0, 250, 220],
        ),

        # More strongly contained by person 1.
        detection(
            10,
            "helmet",
            0.92,
            [150, 10, 210, 50],
        ),
    ]
)


assigned_counts = [
    len(
        person[
            "associated_detections"
        ]
    )
    for person
    in result[
        "people"
    ]
]


assert sum(
    assigned_counts
) == 1


assert assigned_counts[
    1
] == 1


print(
    "PASS: Ambiguous PPE assigned to only "
    "the strongest person match."
)


# ============================================================
# Input immutability
# ============================================================

original = [
    detection(
        0,
        "person",
        0.95,
        [0, 0, 100, 200],
    ),

    detection(
        10,
        "helmet",
        0.90,
        [20, 5, 70, 45],
    ),
]


snapshot = [
    {
        **item,
        "bbox_xyxy":
            list(
                item[
                    "bbox_xyxy"
                ]
            ),
    }
    for item
    in original
]


associate_ppe_to_people(
    original
)


assert original == snapshot


print(
    "PASS: Original detections remain unchanged."
)


print(
    "\n============================================"
)
print(
    "PPE ASSOCIATION CONTRACT SUMMARY"
)
print(
    "============================================"
)

print(
    "PASS: Single-person association."
)

print(
    "PASS: Multi-person separation."
)

print(
    "PASS: Unrelated PPE rejection."
)

print(
    "PASS: No-person handling."
)

print(
    "PASS: Ambiguous-object single assignment."
)

print(
    "PASS: Detection immutability."
)


print(
    "\n============================================"
)
print(
    "PPE ASSOCIATION CONTRACT PASSED"
)
print(
    "============================================"
)
