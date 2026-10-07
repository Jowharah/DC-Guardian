"""
DC-Guardian Evidence
PPE Person-Object Association

Associates PPE detections with individual detected persons.

IMPORTANT:
- This module does NOT decide PPE compliance.
- It does NOT define which PPE items are required.
- It only associates detected PPE objects with person boxes.
"""

from __future__ import annotations


PERSON_CLASS = "person"


# PPE / body-related detections that may be associated with
# an individual person.
ASSOCIABLE_CLASSES = {
    "ear",
    "ear-mufs",
    "face",
    "face-guard",
    "face-mask-medical",
    "foot",
    "glasses",
    "gloves",
    "hands",
    "head",
    "helmet",
    "medical-suit",
    "safety-suit",
    "safety-vest",
    "shoes",
    "tools",
}


def box_area(
    box,
):
    """
    Calculate XYXY bounding-box area.
    """

    x1, y1, x2, y2 = box

    width = max(
        0.0,
        x2 - x1,
    )

    height = max(
        0.0,
        y2 - y1,
    )

    return (
        width
        * height
    )


def intersection_area(
    box_a,
    box_b,
):
    """
    Calculate intersection area between two XYXY boxes.
    """

    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b

    x1 = max(
        ax1,
        bx1,
    )

    y1 = max(
        ay1,
        by1,
    )

    x2 = min(
        ax2,
        bx2,
    )

    y2 = min(
        ay2,
        by2,
    )

    width = max(
        0.0,
        x2 - x1,
    )

    height = max(
        0.0,
        y2 - y1,
    )

    return (
        width
        * height
    )


def containment_ratio(
    object_box,
    person_box,
):
    """
    Fraction of the PPE object's area that lies inside the
    person's bounding box.

    This is more appropriate than ordinary IoU for PPE
    association because a helmet may be completely contained
    inside a much larger person box while having low IoU.
    """

    object_area = box_area(
        object_box
    )


    if object_area <= 0:

        return 0.0


    intersection = intersection_area(
        object_box,
        person_box,
    )


    return (
        intersection
        / object_area
    )


def box_center(
    box,
):
    """
    Return XY center of an XYXY box.
    """

    x1, y1, x2, y2 = box

    return (
        (x1 + x2) / 2.0,
        (y1 + y2) / 2.0,
    )


def center_inside(
    object_box,
    person_box,
):
    """
    Return True when the object's center lies inside the
    person's bounding box.
    """

    center_x, center_y = box_center(
        object_box
    )

    x1, y1, x2, y2 = person_box

    return (
        x1 <= center_x <= x2
        and
        y1 <= center_y <= y2
    )


def association_score(
    object_box,
    person_box,
):
    """
    Calculate a simple deterministic association score.

    Primary signal:
        fraction of PPE object contained by person box

    Small bonus:
        PPE-object center lies inside person box

    The score is used only to choose between candidate people.
    """

    containment = containment_ratio(
        object_box,
        person_box,
    )

    center_bonus = (
        0.05
        if center_inside(
            object_box,
            person_box,
        )
        else 0.0
    )

    return (
        containment
        + center_bonus
    )


def normalize_detection(
    detection,
):
    """
    Validate and normalize one detector output.

    Expected structure:

    {
        "class_id": 10,
        "class_name": "helmet",
        "confidence": 0.82,
        "bbox_xyxy": [x1, y1, x2, y2]
    }
    """

    required = {
        "class_id",
        "class_name",
        "confidence",
        "bbox_xyxy",
    }


    missing = (
        required
        - set(
            detection
        )
    )


    if missing:

        raise ValueError(
            "Detection missing required field(s): "
            + ", ".join(
                sorted(
                    missing
                )
            )
        )


    box = detection[
        "bbox_xyxy"
    ]


    if len(box) != 4:

        raise ValueError(
            "bbox_xyxy must contain four values."
        )


    normalized_box = [
        float(value)
        for value in box
    ]


    x1, y1, x2, y2 = normalized_box


    if (
        x2 <= x1
        or
        y2 <= y1
    ):

        raise ValueError(
            "Detection contains invalid XYXY box."
        )


    return {
        "class_id":
            int(
                detection[
                    "class_id"
                ]
            ),

        "class_name":
            str(
                detection[
                    "class_name"
                ]
            ),

        "confidence":
            float(
                detection[
                    "confidence"
                ]
            ),

        "bbox_xyxy":
            normalized_box,
    }


def associate_ppe_to_people(
    detections,
    *,
    minimum_containment=0.50,
):
    """
    Associate PPE detections with detected people.

    A PPE object is eligible for association when at least
    `minimum_containment` of its own box lies within a person's
    box.

    If multiple people qualify, the object is assigned only to
    the person with the strongest association score.

    Returns:

    {
        "people": [...],
        "unassigned_detections": [...]
    }
    """

    if not (
        0.0
        <= minimum_containment
        <= 1.0
    ):

        raise ValueError(
            "minimum_containment must lie within [0, 1]."
        )


    normalized = [
        normalize_detection(
            detection
        )
        for detection
        in detections
    ]


    person_detections = [
        detection
        for detection
        in normalized
        if (
            detection[
                "class_name"
            ]
            == PERSON_CLASS
        )
    ]


    other_detections = [
        detection
        for detection
        in normalized
        if (
            detection[
                "class_name"
            ]
            != PERSON_CLASS
        )
    ]


    # Stable ordering makes person_index deterministic.
    person_detections.sort(
        key=lambda detection: (
            detection[
                "bbox_xyxy"
            ][0],
            detection[
                "bbox_xyxy"
            ][1],
        )
    )


    people = []


    for person_index, person in enumerate(
        person_detections
    ):

        people.append(
            {
                "person_index":
                    person_index,

                "person_detection":
                    person,

                "associated_detections":
                    [],
            }
        )


    unassigned = []


    for detection in other_detections:

        class_name = detection[
            "class_name"
        ]


        if class_name not in ASSOCIABLE_CLASSES:

            unassigned.append(
                {
                    **detection,
                    "unassigned_reason":
                        "CLASS_NOT_ASSOCIABLE",
                }
            )

            continue


        candidates = []


        for person_entry in people:

            person_box = (
                person_entry[
                    "person_detection"
                ][
                    "bbox_xyxy"
                ]
            )


            containment = containment_ratio(
                detection[
                    "bbox_xyxy"
                ],
                person_box,
            )


            if (
                containment
                < minimum_containment
            ):

                continue


            score = association_score(
                detection[
                    "bbox_xyxy"
                ],
                person_box,
            )


            candidates.append(
                (
                    score,
                    containment,
                    person_entry[
                        "person_index"
                    ],
                )
            )


        if not candidates:

            unassigned.append(
                {
                    **detection,
                    "unassigned_reason":
                        "NO_PERSON_MATCH",
                }
            )

            continue


        # Highest score wins.
        #
        # If scores are identical, the lower deterministic
        # person_index wins.
        candidates.sort(
            key=lambda item: (
                -item[0],
                item[2],
            )
        )


        best_score, best_containment, best_index = (
            candidates[
                0
            ]
        )


        people[
            best_index
        ][
            "associated_detections"
        ].append(
            {
                **detection,

                "association": {
                    "containment_ratio":
                        best_containment,

                    "score":
                        best_score,
                },
            }
        )


    return {
        "people":
            people,

        "unassigned_detections":
            unassigned,
    }