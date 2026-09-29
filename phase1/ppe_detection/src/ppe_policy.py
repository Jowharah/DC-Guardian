"""
DC-Guardian Phase 1
PPE Compliance Policy

Applies an explicit operational PPE policy to already-associated
person/PPE detections.

This module does NOT perform object detection or person/PPE
association.
"""

from __future__ import annotations


POLICY_VERSION = "PPE-POLICY-v1"

POLICY_NAME = "BASELINE_DC_MAINTENANCE"


REQUIRED_PPE = (
    "helmet",
    "safety-vest",
)


OBSERVED_OPTIONAL_PPE = (
    "ear-mufs",
    "face-guard",
    "face-mask-medical",
    "glasses",
    "gloves",
    "medical-suit",
    "safety-suit",
    "shoes",
)


VALID_PERSON_STATUSES = {
    "COMPLIANT",
    "NON_COMPLIANT",
}


VALID_OVERALL_STATUSES = {
    "COMPLIANT",
    "NON_COMPLIANT",
    "NO_PERSON",
}


def evaluate_person(
    person_entry,
):
    """
    Evaluate one already-associated person.

    Compliance is based only on REQUIRED_PPE.
    """

    person_index = int(
        person_entry[
            "person_index"
        ]
    )

    associated = person_entry[
        "associated_detections"
    ]


    detected_classes = sorted(
        {
            detection[
                "class_name"
            ]
            for detection
            in associated
        }
    )


    required_ppe_not_detected = [
        item
        for item
        in REQUIRED_PPE
        if item not in detected_classes
    ]


    required_detected = [
        item
        for item
        in REQUIRED_PPE
        if item in detected_classes
    ]


    optional_detected = [
        item
        for item
        in OBSERVED_OPTIONAL_PPE
        if item in detected_classes
    ]


    if required_ppe_not_detected:

        status = "NON_COMPLIANT"

    else:

        status = "COMPLIANT"


    return {
        "person_index":
            person_index,

        "status":
            status,

        "required_ppe":
            list(
                REQUIRED_PPE
            ),

        "required_ppe_detected":
            required_detected,

        "required_ppe_not_detected":
            required_ppe_not_detected,

        "optional_ppe_detected":
            optional_detected,

        "all_associated_classes":
            detected_classes,
    }


def evaluate_ppe_policy(
    association_result,
):
    """
    Apply PPE-POLICY-v1 to an association result.

    Overall rules:

    no detected people
        -> NO_PERSON

    all people compliant
        -> COMPLIANT

    one or more people non-compliant
        -> NON_COMPLIANT
    """

    people = association_result[
        "people"
    ]


    if not people:

        return {
            "policy_version":
                POLICY_VERSION,

            "policy_name":
                POLICY_NAME,

            "required_ppe":
                list(
                    REQUIRED_PPE
                ),

            "person_detected":
                False,

            "person_count":
                0,

            "people":
                [],

            "overall_status":
                "NO_PERSON",
        }


    evaluations = [
        evaluate_person(
            person
        )
        for person
        in people
    ]


    if all(
        person[
            "status"
        ]
        == "COMPLIANT"

        for person
        in evaluations
    ):

        overall_status = (
            "COMPLIANT"
        )

    else:

        overall_status = (
            "NON_COMPLIANT"
        )


    return {
        "policy_version":
            POLICY_VERSION,

        "policy_name":
            POLICY_NAME,

        "required_ppe":
            list(
                REQUIRED_PPE
            ),

        "person_detected":
            True,

        "person_count":
            len(
                evaluations
            ),

        "people":
            evaluations,

        "overall_status":
            overall_status,
    }