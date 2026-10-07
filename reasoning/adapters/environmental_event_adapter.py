from datetime import datetime, timezone
from uuid import uuid4


SCHEMA_VERSION = "1.0"

DOMAIN = "ENVIRONMENTAL"

EVENT_TYPE = "ENVIRONMENTAL_CONDITION_ASSESSMENT"

COMPONENT = "environmental_detector"

COMPONENT_VERSION = "1.0"


def normalize_datetime(value):

    if value is None:
        return None

    if isinstance(value, datetime):

        if value.tzinfo is None:
            return value.isoformat()

        return (
            value
            .astimezone(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )

    value = str(value)

    if value.endswith("Z"):
        return value

    return value


def generate_event_id():

    return (
        "EVT-ENV-"
        + uuid4().hex.upper()
    )


def adapt_environmental_assessment(
    environmental_assessment,
    *,
    dataset_name=None,
    source_type="LIVE",
    event_id=None,
):
    """
    Convert one Evidence layer environmental assessment into
    DC-Guardian Common Event Schema v1.0.

    No synthetic infrastructure location is introduced here.
    """

    if not isinstance(
        environmental_assessment,
        dict,
    ):
        raise TypeError(
            "environmental_assessment must "
            "be a dictionary."
        )


    required = [
        "domain",
        "event_type",
        "component",
        "component_version",
        "source_class",
        "source_id",
        "source_asset_type",
        "observation_timestamp",
        "assessment",
        "anomaly_detected",
        "measurements",
        "evidence",
    ]


    missing = [
        field
        for field in required
        if field
        not in environmental_assessment
    ]


    if missing:

        raise ValueError(
            "Environmental assessment is missing "
            "required fields: "
            + ", ".join(missing)
        )


    if (
        environmental_assessment["domain"]
        != DOMAIN
    ):

        raise ValueError(
            "Unexpected environmental domain."
        )


    if (
        environmental_assessment["event_type"]
        != EVENT_TYPE
    ):

        raise ValueError(
            "Unexpected environmental event type."
        )


    source_class = (
        environmental_assessment[
            "source_class"
        ]
    )

    source_id = str(
        environmental_assessment[
            "source_id"
        ]
    )

    asset_type = (
        environmental_assessment[
            "source_asset_type"
        ]
    )


    timestamp = normalize_datetime(
        environmental_assessment[
            "observation_timestamp"
        ]
    )


    if event_id is None:
        event_id = generate_event_id()


    # ========================================================
    # Entity identity
    # ========================================================

    sensor_id = None
    asset_id = None
    server_id = None
    equipment_id = None


    if (
        source_class
        == "ENVIRONMENTAL_SENSOR"
    ):

        sensor_id = source_id


    elif (
        source_class
        == "HARDWARE_TELEMETRY"
    ):

        asset_id = source_id

        if asset_type == "SERVER":
            server_id = source_id

        elif asset_type == "COOLING_SYSTEM":
            equipment_id = source_id

        elif asset_type != "HARD_DRIVE":

            raise ValueError(
                "Unsupported environmental "
                f"hardware asset type: {asset_type}"
            )


    else:

        raise ValueError(
            "Unsupported environmental source class: "
            f"{source_class}"
        )


    # ========================================================
    # Evidence
    # ========================================================

    evidence = {
        "source_class":
            source_class,

        "source_asset_type":
            asset_type,

        "measurements":
            environmental_assessment[
                "measurements"
            ],

        "environmental":
            environmental_assessment[
                "evidence"
            ],
    }


    common_event = {
        "event_id":
            event_id,

        "schema_version":
            SCHEMA_VERSION,

        "timestamp":
            timestamp,

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
                environmental_assessment[
                    "component"
                ],

            "component_version":
                environmental_assessment[
                    "component_version"
                ],

            "model_name":
                None,
        },

        "entities": {
            "person_id":
                None,

            "source_ip":
                None,

            "asset_id":
                asset_id,

            "server_id":
                server_id,

            "camera_id":
                None,

            "sensor_id":
                sensor_id,

            "equipment_id":
                equipment_id,
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
                environmental_assessment[
                    "assessment"
                ],

            "confidence":
                None,

            "score":
                None,

            "anomaly_detected":
                bool(
                    environmental_assessment[
                        "anomaly_detected"
                    ]
                ),
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
                timestamp,

            "scenario_id":
                None,
        },
    }


    return common_event