"""
DC-Guardian Reasoning
PPE Compliance Event Adapter

Converts the frozen Evidence-layer PPECompliancePipeline output
into DC-Guardian Common Event Schema v1.0.

Important:
    PPE not detected != proof of physical absence.

This adapter preserves PPE compliance evidence only.
Camera/topology placement, employee identity, authorization,
and cross-domain correlation remain Reasoning-layer responsibilities.
"""

from copy import deepcopy
from datetime import datetime, timezone


# ============================================================
# Contract
# ============================================================

SCHEMA_VERSION = "1.0"

DOMAIN = "SAFETY"

EVENT_TYPE = "PPE_COMPLIANCE_ASSESSMENT"

COMPONENT = "DC_GUARDIAN_PPE_COMPLIANCE"

COMPONENT_VERSION = "1.0"


SUPPORTED_STATUSES = {
    "COMPLIANT",
    "NON_COMPLIANT",
    "NO_PERSON",
}


STATE_MAP = {
    "COMPLIANT":
        "PPE_COMPLIANT",

    "NON_COMPLIANT":
        "PPE_NON_COMPLIANT",

    "NO_PERSON":
        "NO_PERSON_DETECTED",
}


# ============================================================
# Helpers
# ============================================================

def _normalize_timestamp(
    timestamp,
):
    """
    Return an ISO-8601 timestamp.

    Controlled tests should normally supply it explicitly.
    """

    if timestamp is None:

        return (
            datetime.now(
                timezone.utc
            )
            .isoformat()
        )


    if not isinstance(
        timestamp,
        str,
    ):

        raise ValueError(
            "timestamp must be an ISO-8601 string."
        )


    if not timestamp.strip():

        raise ValueError(
            "timestamp cannot be empty."
        )


    return timestamp


# ============================================================
# Adapter
# ============================================================

def adapt_ppe_assessment(
    assessment,
    *,
    dataset_name,
    source_type,
    event_id,
    timestamp=None,
):
    """
    Convert one frozen Evidence-layer PPE assessment into the
    DC-Guardian Common Event Schema.

    This function does NOT:
        - run YOLO
        - modify PPE policy
        - assign a camera
        - assign a zone
        - identify an employee
        - evaluate authorization
        - create synthetic topology
        - correlate events
    """

    if not isinstance(
        assessment,
        dict,
    ):

        raise ValueError(
            "PPE assessment must be a dictionary."
        )


    required_fields = {
        "domain",
        "event_type",
        "model_family",
        "architecture",
        "model_weights",
        "detector_configuration",
        "detector_configuration_frozen",
        "policy_version",
        "policy_name",
        "policy_frozen",
        "policy_source",
        "required_ppe",
        "confidence_threshold",
        "iou_threshold",
        "association_method",
        "association_minimum_containment",
        "person_assignment",
        "person_detected",
        "person_count",
        "overall_status",
        "people",
        "latency_ms",
    }


    missing = (
        required_fields
        - set(
            assessment
        )
    )


    if missing:

        raise ValueError(
            "PPE assessment missing fields: "
            f"{sorted(missing)}"
        )


    # ========================================================
    # Evidence-layer contract
    #
    # Evidence-layer currently emits PHYSICAL_SECURITY because PPE
    # originates from camera-based physical observations.
    #
    # Reasoning layer normalizes PPE into the dedicated SAFETY domain.
    # ========================================================

    if (
        assessment[
            "domain"
        ]
        != "PHYSICAL_SECURITY"
    ):

        raise ValueError(
            "Evidence-layer PPE assessment domain must be "
            "PHYSICAL_SECURITY."
        )


    if (
        assessment[
            "event_type"
        ]
        != "PPE_COMPLIANCE_ASSESSMENT"
    ):

        raise ValueError(
            "Unexpected PPE assessment event type."
        )


    if (
        assessment[
            "detector_configuration_frozen"
        ]
        is not True
    ):

        raise ValueError(
            "PPE assessment must come from "
            "the frozen detector configuration."
        )


    if (
        assessment[
            "policy_frozen"
        ]
        is not True
    ):

        raise ValueError(
            "PPE assessment must use "
            "the frozen PPE policy."
        )


    # ========================================================
    # PPE status
    # ========================================================

    status = assessment[
        "overall_status"
    ]


    if status not in SUPPORTED_STATUSES:

        raise ValueError(
            "Unsupported PPE status: "
            f"{status}"
        )


    state = STATE_MAP[
        status
    ]


    # PPE non-compliance is safety-anomaly evidence.
    #
    # COMPLIANT and NO_PERSON are not anomaly evidence.

    anomaly_detected = (
        status
        == "NON_COMPLIANT"
    )


    # ========================================================
    # Person evidence consistency
    # ========================================================

    people = deepcopy(
        assessment[
            "people"
        ]
    )


    person_count = int(
        assessment[
            "person_count"
        ]
    )


    person_detected = bool(
        assessment[
            "person_detected"
        ]
    )


    if person_count != len(
        people
    ):

        raise ValueError(
            "PPE person_count does not match "
            "person evidence."
        )


    if (
        person_count > 0
        and not person_detected
    ):

        raise ValueError(
            "PPE assessment contains people but "
            "person_detected is false."
        )


    if (
        person_count == 0
        and person_detected
    ):

        raise ValueError(
            "person_detected is true but "
            "person_count is zero."
        )


    # ========================================================
    # Confidence
    #
    # PPE is a multi-object assessment, so there is no single
    # model confidence that truthfully represents the complete
    # compliance decision.
    #
    # Preserve detector threshold in evidence instead.
    # ========================================================

    confidence = None

    score = None


    # ========================================================
    # Evidence
    # ========================================================

    evidence = {
        "ppe_status":
            status,

        "person_detected":
            person_detected,

        "person_count":
            person_count,

        "people":
            people,

        "required_ppe":
            deepcopy(
                assessment[
                    "required_ppe"
                ]
            ),

        "detector_configuration":
            assessment[
                "detector_configuration"
            ],

        "detector_configuration_frozen":
            assessment[
                "detector_configuration_frozen"
            ],

        "model_family":
            assessment[
                "model_family"
            ],

        "architecture":
            assessment[
                "architecture"
            ],

        "model_weights":
            assessment[
                "model_weights"
            ],

        "confidence_threshold":
            assessment[
                "confidence_threshold"
            ],

        "iou_threshold":
            assessment[
                "iou_threshold"
            ],

        "association_method":
            assessment[
                "association_method"
            ],

        "association_minimum_containment":
            assessment[
                "association_minimum_containment"
            ],

        "person_assignment":
            assessment[
                "person_assignment"
            ],

        "policy_version":
            assessment[
                "policy_version"
            ],

        "policy_name":
            assessment[
                "policy_name"
            ],

        "policy_frozen":
            assessment[
                "policy_frozen"
            ],

        "policy_source":
            assessment[
                "policy_source"
            ],

        "latency_ms":
            assessment[
                "latency_ms"
            ],

        "required_ppe_not_detected_semantics":
            (
                "Required PPE not detected is safety "
                "evidence and does not prove physical absence."
            ),

        "employee_identity_evaluated":
            False,

        "authorization_evaluated":
            False,
    }


    # ========================================================
    # Common Event Schema
    # ========================================================

    event_timestamp = (
        _normalize_timestamp(
            timestamp
        )
    )


    event = {
        "event_id":
            event_id,

        "schema_version":
            SCHEMA_VERSION,

        "timestamp":
            event_timestamp,

        "window":
            None,

        "domain":
            DOMAIN,

        "event_type":
            EVENT_TYPE,

        "source": {
            "component":
                COMPONENT,

            "component_version":
                COMPONENT_VERSION,

            "model_name":
                assessment[
                    "architecture"
                ],
        },

        "entities": {
            "person_id":
                None,

            "source_ip":
                None,

            "asset_id":
                None,

            "server_id":
                None,

            "camera_id":
                None,

            "sensor_id":
                None,

            "equipment_id":
                None,
        },

        "location": {
            "data_center_id":
                None,

            "zone_id":
                None,

            "rack_id":
                None,

            "access_point_id":
                None,
        },

        "assessment": {
            "state":
                state,

            "confidence":
                confidence,

            "score":
                score,

            "anomaly_detected":
                anomaly_detected,
        },

        "evidence":
            evidence,

        "provenance": {
            "source_type":
                source_type,

            "dataset_name":
                dataset_name,

            "original_event_id":
                None,

            "synthetic_mapping":
                False,

            "mapping_type":
                "NONE",

            "original_timestamp":
                event_timestamp,

            "scenario_id":
                None,
        },
    }


    return event