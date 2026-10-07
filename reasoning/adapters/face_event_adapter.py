"""
DC-Guardian Reasoning
Face Recognition Event Adapter

Converts the frozen Evidence-layer FaceRecognitionPipeline output
into DC-Guardian Common Event Schema v1.0.

Important:
    Identification != authorization.

This adapter preserves identity evidence only.
Camera/topology placement and authorization decisions remain
Reasoning-layer responsibilities.
"""

from copy import deepcopy
from datetime import datetime, timezone


# ============================================================
# Contract
# ============================================================

SCHEMA_VERSION = "1.0"

DOMAIN = "PHYSICAL_SECURITY"

EVENT_TYPE = "FACE_IDENTIFICATION_ASSESSMENT"

COMPONENT = "DC_GUARDIAN_FACE_RECOGNITION"

COMPONENT_VERSION = "1.0"


SUPPORTED_STATUSES = {
    "RECOGNIZED",
    "UNKNOWN",
    "NO_FACE",
    "MULTIPLE_FACES",
}


STATE_MAP = {
    "RECOGNIZED":
        "RECOGNIZED_PERSON",

    "UNKNOWN":
        "UNKNOWN_PERSON",

    "NO_FACE":
        "NO_FACE_DETECTED",

    "MULTIPLE_FACES":
        "MULTIPLE_FACES_DETECTED",
}


# ============================================================
# Helpers
# ============================================================

def _normalize_timestamp(
    timestamp,
):
    """
    Return an ISO-8601 UTC timestamp.

    If timestamp is omitted, the adapter uses current UTC time.
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

def adapt_face_assessment(
    assessment,
    *,
    dataset_name,
    source_type,
    event_id,
    timestamp=None,
):
    """
    Convert one Evidence-layer face-recognition result into the
    DC-Guardian Common Event Schema.

    This function does NOT:
        - assign a camera
        - assign a zone
        - decide authorization
        - create synthetic topology
        - correlate events
    """

    if not isinstance(
        assessment,
        dict,
    ):

        raise ValueError(
            "Face assessment must be a dictionary."
        )


    required_fields = {
        "domain",
        "event_type",
        "person_id",
        "recognition_status",
        "face_detected",
        "face_count",
        "distance",
        "similarity",
        "nearest_employee_id",
        "threshold",
        "threshold_source",
        "model_name",
        "detector_backend",
        "distance_metric",
        "configuration_frozen",
    }


    missing = (
        required_fields
        - set(
            assessment
        )
    )


    if missing:

        raise ValueError(
            "Face assessment missing fields: "
            f"{sorted(missing)}"
        )


    # ========================================================
    # Evidence-layer contract
    # ========================================================

    if (
        assessment[
            "domain"
        ]
        != DOMAIN
    ):

        raise ValueError(
            "Face assessment domain must be "
            "PHYSICAL_SECURITY."
        )


    if (
        assessment[
            "event_type"
        ]
        != EVENT_TYPE
    ):

        raise ValueError(
            "Unexpected face assessment event type."
        )


    status = assessment[
        "recognition_status"
    ]


    if status not in SUPPORTED_STATUSES:

        raise ValueError(
            "Unsupported face recognition status: "
            f"{status}"
        )


    if (
        assessment[
            "configuration_frozen"
        ]
        is not True
    ):

        raise ValueError(
            "Face assessment must come from "
            "the frozen Evidence-layer configuration."
        )


    if (
        assessment[
            "threshold_source"
        ]
        != "validation_only"
    ):

        raise ValueError(
            "Face recognition threshold must "
            "come from validation only."
        )


    # ========================================================
    # Identity semantics
    # ========================================================

    person_id = assessment[
        "person_id"
    ]


    if status == "RECOGNIZED":

        if (
            not isinstance(
                person_id,
                str,
            )
            or
            not person_id.startswith(
                "P"
            )
        ):

            raise ValueError(
                "RECOGNIZED face must preserve "
                "an enrolled Pxxx identity."
            )


    else:

        if person_id != "UNKNOWN":

            raise ValueError(
                "Non-recognized face states must "
                "use person_id=UNKNOWN."
            )


    # ========================================================
    # Assessment state
    # ========================================================

    state = STATE_MAP[
        status
    ]


    # Unknown person is abnormal physical-security evidence.
    #
    # Recognition alone is NOT abnormal because authorization
    # is evaluated later against topology/permissions.

    anomaly_detected = (
        status
        == "UNKNOWN"
    )


    # ========================================================
    # Confidence
    #
    # Preserve a numeric similarity only when a face was
    # successfully embedded/matched.
    # ========================================================

    similarity = assessment.get(
        "similarity"
    )


    confidence = (
        float(
            similarity
        )
        if similarity
        is not None
        else None
    )


    distance = assessment.get(
        "distance"
    )


    score = (
        float(
            distance
        )
        if distance
        is not None
        else None
    )


    # ========================================================
    # Evidence
    # ========================================================

    evidence = {
        "recognition_status":
            status,

        "person_id":
            person_id,

        "face_detected":
            assessment[
                "face_detected"
            ],

        "face_count":
            assessment[
                "face_count"
            ],

        "distance":
            distance,

        "similarity":
            similarity,

        "threshold":
            assessment[
                "threshold"
            ],

        "threshold_source":
            assessment[
                "threshold_source"
            ],

        "nearest_employee_id":
            assessment[
                "nearest_employee_id"
            ],

        "detector_backend":
            assessment[
                "detector_backend"
            ],

        "distance_metric":
            assessment[
                "distance_metric"
            ],

        "face_confidence":
            assessment.get(
                "face_confidence"
            ),

        "facial_area":
            deepcopy(
                assessment.get(
                    "facial_area"
                )
            ),

        "latency_ms":
            assessment.get(
                "latency_ms"
            ),

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
                    "model_name"
                ],
        },

        "entities": {
            "person_id":
                person_id,

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