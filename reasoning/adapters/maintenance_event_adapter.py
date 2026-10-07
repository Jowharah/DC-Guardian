from datetime import datetime, timezone
from uuid import uuid4


# ============================================================
# Constants
# ============================================================

SCHEMA_VERSION = "1.0"

DOMAIN = "MAINTENANCE"

EVENT_TYPE = "STORAGE_FAILURE_RISK_ASSESSMENT"

COMPONENT = "maintenance_detector"

COMPONENT_VERSION = "1.0"

MODEL_NAME = "DC_Guardian_Temporal_RF_v2"


# ============================================================
# Timestamp helper
# ============================================================

def normalize_datetime(value):
    """
    Convert a maintenance observation timestamp into
    an ISO-8601 UTC-compatible string.
    """

    if value is None:
        return None

    if isinstance(
        value,
        datetime,
    ):

        if value.tzinfo is None:
            return value.isoformat()

        return (
            value
            .astimezone(
                timezone.utc
            )
            .isoformat()
            .replace(
                "+00:00",
                "Z",
            )
        )

    value = str(
        value
    )

    if value.endswith(
        "Z"
    ):
        return value

    return value


# ============================================================
# Event ID
# ============================================================

def generate_event_id():
    """
    Generate a unique Reasoning layer maintenance event ID.
    """

    return (
        "EVT-MAINT-"
        + uuid4().hex.upper()
    )


# ============================================================
# Convert Evidence layer maintenance assessment
# ============================================================

def adapt_maintenance_assessment(
    maintenance_assessment,
    *,
    dataset_name=None,
    source_type="LIVE",
    event_id=None,
):
    """
    Convert one frozen Predictive Maintenance assessment
    into DC-Guardian Common Event Schema v1.0.

    Infrastructure topology is deliberately unresolved here.
    A separate Reasoning layer topology component may later map the
    drive to synthetic equipment/server/rack/location entities.
    """

    if not isinstance(
        maintenance_assessment,
        dict,
    ):

        raise TypeError(
            "maintenance_assessment must be "
            "a dictionary."
        )


    # ========================================================
    # Validate minimum Evidence layer contract
    # ========================================================

    required_fields = [
        "domain",
        "event_type",
        "model_name",
        "asset_type",
        "serial_number",
        "observation_timestamp",
        "assessment",
        "failure_probability",
        "operating_threshold",
        "failure_horizon_days",
        "evidence",
    ]


    missing_fields = [
        field
        for field in required_fields
        if field
        not in maintenance_assessment
    ]


    if missing_fields:

        raise ValueError(
            "Maintenance assessment is missing "
            "required fields: "
            + ", ".join(
                missing_fields
            )
        )


    # ========================================================
    # Validate frozen semantic contract
    # ========================================================

    if (
        maintenance_assessment[
            "domain"
        ]
        != "MAINTENANCE"
    ):

        raise ValueError(
            "Unexpected maintenance domain."
        )


    if (
        maintenance_assessment[
            "event_type"
        ]
        != "STORAGE_FAILURE_RISK_ASSESSMENT"
    ):

        raise ValueError(
            "Unexpected maintenance event type."
        )


    assessment_state = (
        maintenance_assessment[
            "assessment"
        ]
    )


    if assessment_state not in {
        "NORMAL",
        "AT_RISK",
    }:

        raise ValueError(
            "Unexpected maintenance assessment "
            f"state: {assessment_state}"
        )


    probability = float(
        maintenance_assessment[
            "failure_probability"
        ]
    )


    threshold = float(
        maintenance_assessment[
            "operating_threshold"
        ]
    )


    if not (
        0.0
        <= probability
        <= 1.0
    ):

        raise ValueError(
            "failure_probability must be "
            "between 0 and 1."
        )


    if not (
        0.0
        <= threshold
        <= 1.0
    ):

        raise ValueError(
            "operating_threshold must be "
            "between 0 and 1."
        )


    # Ensure state and frozen threshold agree.
    expected_at_risk = (
        probability
        >= threshold
    )


    if (
        assessment_state
        == "AT_RISK"
    ) != expected_at_risk:

        raise ValueError(
            "Maintenance assessment state does "
            "not agree with failure probability "
            "and operating threshold."
        )


    # ========================================================
    # Timestamp
    # ========================================================

    timestamp = normalize_datetime(
        maintenance_assessment[
            "observation_timestamp"
        ]
    )


    # ========================================================
    # Event ID
    # ========================================================

    if event_id is None:

        event_id = (
            generate_event_id()
        )


    # ========================================================
    # Preserve maintenance evidence
    # ========================================================

    evidence = {
        "asset_type":
            maintenance_assessment[
                "asset_type"
            ],

        "serial_number":
            str(
                maintenance_assessment[
                    "serial_number"
                ]
            ),

        "failure_probability":
            probability,

        "operating_threshold":
            threshold,

        "failure_horizon_days":
            int(
                maintenance_assessment[
                    "failure_horizon_days"
                ]
            ),

        "smart":
            maintenance_assessment[
                "evidence"
            ],
    }


    # ========================================================
    # Common Event Schema
    # ========================================================

    common_event = {
        "event_id":
            event_id,

        "schema_version":
            SCHEMA_VERSION,

        "timestamp":
            timestamp,

        # Maintenance is a point-in-time assessment.
        "window": {
            "start":
                timestamp,

            "end":
                timestamp,
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
                maintenance_assessment[
                    "model_name"
                ],
        },

        # ----------------------------------------------------
        # Domain entities
        #
        # serial_number is genuine Evidence layer evidence.
        #
        # It is represented as asset_id at the common-event
        # boundary. Infrastructure topology is not inferred.
        # ----------------------------------------------------

        "entities": {
            "person_id":
                None,

            "source_ip":
                None,

            "asset_id":
                str(
                    maintenance_assessment[
                        "serial_number"
                    ]
                ),

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
        # Location remains unresolved.
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
        # Common assessment
        # ----------------------------------------------------

        "assessment": {
            "state":
                assessment_state,

            "confidence":
                None,

            "score":
                probability,

            "anomaly_detected":
                bool(
                    assessment_state
                    == "AT_RISK"
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
                timestamp,

            "scenario_id":
                None,
        },
    }


    return common_event