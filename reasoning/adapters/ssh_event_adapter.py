from datetime import datetime, timezone
from uuid import uuid4


# ============================================================
# Constants
# ============================================================

SCHEMA_VERSION = "1.0"

DOMAIN = "CYBERSECURITY"

EVENT_TYPE = "SSH_BEHAVIOR_ASSESSMENT"

COMPONENT = "ssh_detector"

COMPONENT_VERSION = "1.0"

MODEL_NAME = "SSH_HYBRID_V1"


# ============================================================
# Timestamp helper
# ============================================================

def normalize_datetime(value):
    """
    Convert an SSH detector datetime/string into an
    ISO-8601 UTC-compatible string.

    The original SSH Loghub timestamps use a placeholder
    year because the raw syslog records do not contain a year.
    This function does not change that interpretation.
    """

    if value is None:
        return None

    if isinstance(value, datetime):

        # If no timezone exists, preserve the timestamp
        # while representing it in ISO format.
        if value.tzinfo is None:
            return value.isoformat()

        return value.astimezone(
            timezone.utc
        ).isoformat().replace(
            "+00:00",
            "Z"
        )

    value = str(value)

    # Already ISO-like.
    if value.endswith("Z"):
        return value

    return value


# ============================================================
# Generate DC-Guardian event ID
# ============================================================

def generate_event_id():
    """
    Generate a unique Reasoning layer event identifier.
    """

    return (
        "EVT-SSH-"
        + uuid4().hex.upper()
    )


# ============================================================
# Convert one SSH assessment
# ============================================================

def adapt_ssh_assessment(
    ssh_assessment,
    *,
    dataset_name=None,
    source_type="LIVE",
    event_id=None
):
    """
    Convert one frozen SSH Detector v1 assessment into
    DC-Guardian Common Event Schema v1.0.

    Infrastructure location fields remain null here.
    Synthetic topology mapping is performed by a separate
    Reasoning layer component.
    """

    if not isinstance(
        ssh_assessment,
        dict
    ):
        raise TypeError(
            "ssh_assessment must be a dictionary."
        )

    # --------------------------------------------------------
    # Validate minimum SSH contract
    # --------------------------------------------------------

    required_fields = [
        "source_ip",
        "window_start",
        "window_end",
        "anomaly_detected",
        "detector_votes",
        "detector_combination",
        "confidence",
        "evidence_state",
        "explicit_security_signal",
        "security_signals",
        "rule",
        "isolation_forest",
        "autoencoder",
        "evidence",
    ]

    missing_fields = [
        field
        for field in required_fields
        if field not in ssh_assessment
    ]

    if missing_fields:
        raise ValueError(
            "SSH assessment is missing required fields: "
            + ", ".join(missing_fields)
        )

    # --------------------------------------------------------
    # Normalize timestamps
    # --------------------------------------------------------

    window_start = normalize_datetime(
        ssh_assessment[
            "window_start"
        ]
    )

    window_end = normalize_datetime(
        ssh_assessment[
            "window_end"
        ]
    )

    # For a window-based detector, the common event timestamp
    # is defined as the beginning of the assessed window.
    timestamp = window_start

    # --------------------------------------------------------
    # Generate event ID
    # --------------------------------------------------------

    if event_id is None:
        event_id = generate_event_id()

    # --------------------------------------------------------
    # Preserve SSH evidence
    # --------------------------------------------------------

    evidence = {
        "detector_votes":
            int(
                ssh_assessment[
                    "detector_votes"
                ]
            ),

        "detector_combination":
            ssh_assessment[
                "detector_combination"
            ],

        "explicit_security_signal":
            bool(
                ssh_assessment[
                    "explicit_security_signal"
                ]
            ),

        "security_signals":
            list(
                ssh_assessment[
                    "security_signals"
                ]
            ),

        "security_signal_evidence":
            list(
                ssh_assessment.get(
                    "security_signal_evidence",
                    []
                )
            ),

        "rule":
            ssh_assessment[
                "rule"
            ],

        "isolation_forest":
            ssh_assessment[
                "isolation_forest"
            ],

        "autoencoder":
            ssh_assessment[
                "autoencoder"
            ],

        "behavior":
            ssh_assessment[
                "evidence"
            ],
    }

    # --------------------------------------------------------
    # Common DC-Guardian event
    # --------------------------------------------------------

    common_event = {
        "event_id":
            event_id,

        "schema_version":
            SCHEMA_VERSION,

        "timestamp":
            timestamp,

        "window": {
            "start":
                window_start,

            "end":
                window_end,
        },

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
                MODEL_NAME,
        },

        # ----------------------------------------------------
        # Domain entities
        #
        # The source IP is genuine model evidence.
        #
        # Infrastructure IDs are deliberately NOT added here.
        # ----------------------------------------------------

        "entities": {
            "person_id":
                None,

            "source_ip":
                ssh_assessment[
                    "source_ip"
                ],

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

        # ----------------------------------------------------
        # Location is unresolved until topology mapping.
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Original model assessment
        # ----------------------------------------------------

        "assessment": {
            "state":
                ssh_assessment[
                    "evidence_state"
                ],

            "confidence":
                ssh_assessment[
                    "confidence"
                ],

            "score":
                None,

            "anomaly_detected":
                bool(
                    ssh_assessment[
                        "anomaly_detected"
                    ]
                ),
        },

        "evidence":
            evidence,

        # ----------------------------------------------------
        # Provenance
        # ----------------------------------------------------

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
            None,

        "scenario_id":
            None,
        },
    }

    return common_event