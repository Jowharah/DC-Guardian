from pathlib import Path
import json
import os

from dotenv import load_dotenv
from jsonschema import (
    Draft202012Validator,
    FormatChecker,
)
from neo4j import GraphDatabase


# ============================================================
# Project paths
# ============================================================

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

ENV_FILE = (
    PROJECT_ROOT
    / ".env"
)

SCHEMA_FILE = (
    PROJECT_ROOT
    / "shared"
    / "schemas"
    / "event_schema.json"
)


# ============================================================
# Environment
# ============================================================

if not ENV_FILE.exists():

    raise FileNotFoundError(
        f".env file not found: {ENV_FILE}"
    )


load_dotenv(
    dotenv_path=ENV_FILE
)


NEO4J_URI = os.getenv(
    "NEO4J_URI",
    "bolt://localhost:7687"
)

NEO4J_USER = os.getenv(
    "NEO4J_USER",
    "neo4j"
)

NEO4J_PASSWORD = os.getenv(
    "NEO4J_PASSWORD"
)

NEO4J_DATABASE = os.getenv(
    "NEO4J_DATABASE",
    "neo4j"
)


# ============================================================
# Load JSON
# ============================================================

def load_json(file_path):

    if not file_path.exists():

        raise FileNotFoundError(
            f"File not found: {file_path}"
        )

    with open(
        file_path,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


# ============================================================
# Event schema validation
# ============================================================

def validate_event(
    event
):

    schema = load_json(
        SCHEMA_FILE
    )

    Draft202012Validator.check_schema(
        schema
    )

    validator = Draft202012Validator(
        schema,
        format_checker=FormatChecker()
    )

    errors = sorted(
        validator.iter_errors(
            event
        ),
        key=lambda error: list(
            error.absolute_path
        )
    )

    if errors:

        messages = []

        for error in errors:

            location = ".".join(
                str(item)
                for item
                in error.absolute_path
            )

            if not location:
                location = "<root>"

            messages.append(
                f"{location}: "
                f"{error.message}"
            )

        raise ValueError(
            "Event schema validation failed:\n"
            + "\n".join(messages)
        )


# ============================================================
# Verify event is mapped
# ============================================================

def validate_mapped_event(
    event
):

    provenance = event[
        "provenance"
    ]

    if (
        provenance[
            "synthetic_mapping"
        ]
        is not True
    ):

        raise ValueError(
            "Event must be topology/scenario "
            "mapped before graph ingestion."
        )


    if (
        provenance[
            "mapping_type"
        ]
        != "SYNTHETIC_SCENARIO"
    ):

        raise ValueError(
            "Expected mapping_type "
            "SYNTHETIC_SCENARIO."
        )


    server_id = event[
        "entities"
    ].get(
        "server_id"
    )


    if not server_id:

        raise ValueError(
            "Mapped event has no server_id."
        )


    scenario_id = provenance.get(
        "scenario_id"
    )


    if not scenario_id:

        raise ValueError(
            "Mapped event has no scenario_id."
        )


# ============================================================
# Extract searchable graph properties
# ============================================================

def build_event_properties(
    event
):

    evidence = event.get(
        "evidence",
        {}
    )

    assessment = event[
        "assessment"
    ]

    provenance = event[
        "provenance"
    ]

    source = event[
        "source"
    ]


    return {
        "event_id":
            event[
                "event_id"
            ],

        "schema_version":
            event[
                "schema_version"
            ],

        "timestamp":
            event[
                "timestamp"
            ],

        "window_start":
            (
                event.get(
                    "window"
                )
                or {}
            ).get(
                "start"
            ),

        "window_end":
            (
                event.get(
                    "window"
                )
                or {}
            ).get(
                "end"
            ),

        "domain":
            event[
                "domain"
            ],

        "event_type":
            event[
                "event_type"
            ],

        "component":
            source[
                "component"
            ],

        "component_version":
            source[
                "component_version"
            ],

        "model_name":
            source.get(
                "model_name"
            ),

        "state":
            assessment[
                "state"
            ],

        "confidence":
            assessment.get(
                "confidence"
            ),

        "anomaly_detected":
            assessment.get(
                "anomaly_detected"
            ),

        "score":
            assessment.get(
                "score"
            ),        

        "detector_votes":
            evidence.get(
                "detector_votes"
            ),

        "detector_combination":
            evidence.get(
                "detector_combination"
            ),

        "explicit_security_signal":
            evidence.get(
                "explicit_security_signal"
            ),

        "source_type":
            provenance[
                "source_type"
            ],

        "dataset_name":
            provenance.get(
                "dataset_name"
            ),

        "synthetic_mapping":
            provenance[
                "synthetic_mapping"
            ],

        "mapping_type":
            provenance[
                "mapping_type"
            ],

        "scenario_id":
            provenance[
                "scenario_id"
            ],

        "original_event_id":
            provenance.get(
                "original_event_id"
            ),

        "original_timestamp":
            provenance.get(
                "original_timestamp"
            ),
    }


# ============================================================
# Ingest mapped SSH event
# ============================================================

def ingest_ssh_event(
    event,
    driver
):

    # --------------------------------------------------------
    # Validate BEFORE any graph write
    # --------------------------------------------------------

    validate_event(
        event
    )

    validate_mapped_event(
        event
    )


    if (
        event[
            "domain"
        ]
        != "CYBERSECURITY"
    ):

        raise ValueError(
            "ingest_ssh_event expected "
            "CYBERSECURITY domain."
        )


    if (
        event[
            "event_type"
        ]
        != "SSH_BEHAVIOR_ASSESSMENT"
    ):

        raise ValueError(
            "ingest_ssh_event expected "
            "SSH_BEHAVIOR_ASSESSMENT."
        )


    server_id = event[
        "entities"
    ][
        "server_id"
    ]

    source_ip = event[
        "entities"
    ].get(
        "source_ip"
    )


    if not source_ip:

        raise ValueError(
            "SSH event has no source_ip."
        )


    properties = build_event_properties(
        event
    )


    with driver.session(
        database=NEO4J_DATABASE
    ) as session:

        # ====================================================
        # Ensure target server already exists
        # ====================================================

        record = session.run(
            """
            MATCH (s:Server {
                server_id: $server_id
            })

            RETURN
                s.server_id AS server_id
            """,
            server_id=server_id,
        ).single()


        if record is None:

            raise ValueError(
                "Target server does not exist "
                f"in Neo4j: {server_id}"
            )


        # ====================================================
        # Event + SourceIP + relationships
        #
        # One transaction prevents a partially inserted event.
        # ====================================================

        query = """
        MATCH (server:Server {
            server_id: $server_id
        })

        MERGE (event:Event {
            event_id: $event_id
        })

        SET
            event.schema_version =
                $schema_version,

            event.timestamp =
                datetime($timestamp),

            event.window_start =
                datetime($window_start),

            event.window_end =
                datetime($window_end),

            event.domain =
                $domain,

            event.event_type =
                $event_type,

            event.component =
                $component,

            event.component_version =
                $component_version,

            event.model_name =
                $model_name,

            event.state =
                $state,

            event.confidence =
                $confidence,

            event.anomaly_detected =
                $anomaly_detected,

            event.detector_votes =
                $detector_votes,

            event.detector_combination =
                $detector_combination,

            event.explicit_security_signal =
                $explicit_security_signal,

            event.source_type =
                $source_type,

            event.dataset_name =
                $dataset_name,

            event.synthetic_mapping =
                $synthetic_mapping,

            event.mapping_type =
                $mapping_type,

            event.scenario_id =
                $scenario_id,

            event.original_event_id =
                $original_event_id,

            event.original_timestamp =
                datetime($original_timestamp)

        MERGE (ip:SourceIP {
            address: $source_ip
        })

        MERGE
            (event)-[:TARGETS]->(server)

        MERGE
            (event)-[:ORIGINATED_FROM]->(ip)

        RETURN
            event.event_id AS event_id,
            server.server_id AS server_id,
            ip.address AS source_ip
        """


        parameters = {
            **properties,

            "server_id":
                server_id,

            "source_ip":
                source_ip,
        }


        result = session.run(
            query,
            **parameters
        ).single()


        if result is None:

            raise RuntimeError(
                "Neo4j event ingestion "
                "returned no result."
            )


        return {
            "event_id":
                result[
                    "event_id"
                ],

            "server_id":
                result[
                    "server_id"
                ],

            "source_ip":
                result[
                    "source_ip"
                ],
        }

# ============================================================
# Ingest mapped maintenance event
# ============================================================

def ingest_maintenance_event(
    event,
    driver,
):

    # --------------------------------------------------------
    # Validate BEFORE graph write
    # --------------------------------------------------------

    validate_event(
        event
    )

    validate_mapped_event(
        event
    )


    if (
        event[
            "domain"
        ]
        != "MAINTENANCE"
    ):

        raise ValueError(
            "ingest_maintenance_event expected "
            "MAINTENANCE domain."
        )


    if (
        event[
            "event_type"
        ]
        != "STORAGE_FAILURE_RISK_ASSESSMENT"
    ):

        raise ValueError(
            "ingest_maintenance_event expected "
            "STORAGE_FAILURE_RISK_ASSESSMENT."
        )


    asset_id = (
        event[
            "entities"
        ]
        .get(
            "asset_id"
        )
    )


    server_id = (
        event[
            "entities"
        ]
        .get(
            "server_id"
        )
    )


    if not asset_id:

        raise ValueError(
            "Maintenance event has no asset_id."
        )


    if not server_id:

        raise ValueError(
            "Maintenance event has no server_id."
        )


    # Critical maintenance semantic:
    # drive identity and host server must remain distinct.
    if asset_id == server_id:

        raise ValueError(
            "Maintenance asset_id must represent "
            "the hard drive, not the host server."
        )


    evidence = event.get(
        "evidence",
        {}
    )


    properties = build_event_properties(
        event
    )


    failure_probability = (
        evidence.get(
            "failure_probability"
        )
    )


    operating_threshold = (
        evidence.get(
            "operating_threshold"
        )
    )


    failure_horizon_days = (
        evidence.get(
            "failure_horizon_days"
        )
    )


    asset_type = (
        evidence.get(
            "asset_type",
            "HARD_DRIVE",
        )
    )


    serial_number = (
        evidence.get(
            "serial_number",
            asset_id,
        )
    )


    with driver.session(
        database=NEO4J_DATABASE
    ) as session:

        # ====================================================
        # Host server must already exist in loaded topology.
        # ====================================================

        record = session.run(
            """
            MATCH (s:Server {
                server_id: $server_id
            })

            RETURN
                s.server_id AS server_id
            """,
            server_id=server_id,
        ).single()


        if record is None:

            raise ValueError(
                "Target server does not exist "
                f"in Neo4j: {server_id}"
            )


        # ====================================================
        # Event + drive asset + relationships
        # ====================================================

        query = """
        MATCH (server:Server {
            server_id: $server_id
        })

        MERGE (asset:Asset {
            asset_id: $asset_id
        })

        SET
            asset.asset_type =
                $asset_type,

            asset.serial_number =
                $serial_number

        MERGE
            (asset)-[:HOSTED_BY]->(server)

        MERGE (event:Event {
            event_id: $event_id
        })

        SET
            event.schema_version =
                $schema_version,

            event.timestamp =
                datetime($timestamp),

            event.window_start =
                datetime($window_start),

            event.window_end =
                datetime($window_end),

            event.domain =
                $domain,

            event.event_type =
                $event_type,

            event.component =
                $component,

            event.component_version =
                $component_version,

            event.model_name =
                $model_name,

            event.state =
                $state,

            event.confidence =
                $confidence,

            event.score =
                $score,

            event.anomaly_detected =
                $anomaly_detected,

            event.failure_probability =
                $failure_probability,

            event.operating_threshold =
                $operating_threshold,

            event.failure_horizon_days =
                $failure_horizon_days,

            event.source_type =
                $source_type,

            event.dataset_name =
                $dataset_name,

            event.synthetic_mapping =
                $synthetic_mapping,

            event.mapping_type =
                $mapping_type,

            event.scenario_id =
                $scenario_id,

            event.original_event_id =
                $original_event_id,

            event.original_timestamp =
                datetime($original_timestamp)

        MERGE
            (event)-[:TARGETS]->(asset)

        RETURN
            event.event_id
                AS event_id,

            asset.asset_id
                AS asset_id,

            server.server_id
                AS server_id
        """


        parameters = {
            **properties,

            "asset_id":
                asset_id,

            "server_id":
                server_id,

            "asset_type":
                asset_type,

            "serial_number":
                serial_number,

            "failure_probability":
                failure_probability,

            "operating_threshold":
                operating_threshold,

            "failure_horizon_days":
                failure_horizon_days,
        }


        result = session.run(
            query,
            **parameters
        ).single()


        if result is None:

            raise RuntimeError(
                "Neo4j maintenance event "
                "ingestion returned no result."
            )


        return {
            "event_id":
                result[
                    "event_id"
                ],

            "asset_id":
                result[
                    "asset_id"
                ],

            "server_id":
                result[
                    "server_id"
                ],
        }

# ============================================================
# Ingest mapped environmental event
# ============================================================

def ingest_environmental_event(
    event,
    driver,
):
    """
    Persist one mapped environmental event.

    Supported sources:
        ENVIRONMENTAL_SENSOR
        HARD_DRIVE
        SERVER
        COOLING_SYSTEM
    """

    # ========================================================
    # Validate common-event contract
    # ========================================================

    validate_event(
        event
    )


    if (
        event[
            "domain"
        ]
        != "ENVIRONMENTAL"
    ):

        raise ValueError(
            "ingest_environmental_event expected "
            "ENVIRONMENTAL domain."
        )


    if (
        event[
            "event_type"
        ]
        != "ENVIRONMENTAL_CONDITION_ASSESSMENT"
    ):

        raise ValueError(
            "ingest_environmental_event expected "
            "ENVIRONMENTAL_CONDITION_ASSESSMENT."
        )


    # ========================================================
    # Validate scenario/topology mapping
    #
    # We intentionally do NOT use validate_mapped_event()
    # here because a dedicated environmental sensor or
    # cooling-system event may legitimately have no server_id.
    # ========================================================

    provenance = event[
        "provenance"
    ]


    if (
        provenance[
            "synthetic_mapping"
        ]
        is not True
    ):

        raise ValueError(
            "Environmental event must be "
            "topology/scenario mapped before ingestion."
        )


    if (
        provenance[
            "mapping_type"
        ]
        != "SYNTHETIC_SCENARIO"
    ):

        raise ValueError(
            "Expected mapping_type "
            "SYNTHETIC_SCENARIO."
        )


    if not provenance.get(
        "scenario_id"
    ):

        raise ValueError(
            "Mapped environmental event "
            "has no scenario_id."
        )


    # ========================================================
    # Environmental evidence
    # ========================================================

    evidence = event.get(
        "evidence",
        {}
    )


    source_class = evidence.get(
        "source_class"
    )


    source_asset_type = evidence.get(
        "source_asset_type"
    )


    entities = event[
        "entities"
    ]


    properties = build_event_properties(
        event
    )


    measurements = evidence.get(
        "measurements",
        {}
    )


    temperature_c = measurements.get(
        "temperature_c"
    )


    humidity_pct = measurements.get(
        "humidity_pct"
    )


    topology_resolution = evidence.get(
        "topology_resolution",
        {}
    )


    topology_mapping_source = (
        topology_resolution.get(
            "mapping_source"
        )
    )


    # ========================================================
    # Resolve environmental target kind
    # ========================================================

    if (
        source_class
        == "ENVIRONMENTAL_SENSOR"
    ):

        target_kind = "SENSOR"

        target_id = entities.get(
            "sensor_id"
        )


        if not target_id:

            raise ValueError(
                "Environmental sensor event "
                "has no sensor_id."
            )


    elif (
        source_class
        == "HARDWARE_TELEMETRY"
    ):

        if (
            source_asset_type
            == "SERVER"
        ):

            target_kind = "SERVER"

            target_id = entities.get(
                "server_id"
            )


        elif (
            source_asset_type
            == "COOLING_SYSTEM"
        ):

            target_kind = "EQUIPMENT"

            target_id = entities.get(
                "equipment_id"
            )


        elif (
            source_asset_type
            == "HARD_DRIVE"
        ):

            target_kind = "ASSET"

            target_id = entities.get(
                "asset_id"
            )


        else:

            raise ValueError(
                "Unsupported environmental "
                "hardware asset type: "
                f"{source_asset_type}"
            )


        if not target_id:

            raise ValueError(
                "Environmental hardware event "
                "has no target identity."
            )


    else:

        raise ValueError(
            "Unsupported environmental "
            f"source class: {source_class}"
        )


    # ========================================================
    # Neo4j persistence
    # ========================================================

    with driver.session(
        database=NEO4J_DATABASE
    ) as session:


        # ====================================================
        # Verify / prepare target
        # ====================================================

        if (
            target_kind
            == "SENSOR"
        ):

            target_record = session.run(
                """
                MATCH (target:Sensor {
                    sensor_id: $target_id
                })

                RETURN
                    target.sensor_id
                        AS target_id
                """,

                target_id=
                    target_id,
            ).single()


            if target_record is None:

                raise ValueError(
                    "Environmental sensor does "
                    "not exist in Neo4j: "
                    f"{target_id}"
                )


            target_query = """
            MATCH (event:Event {
                event_id: $event_id
            })

            MATCH (target:Sensor {
                sensor_id: $target_id
            })

            MERGE
                (event)-[:TARGETS]->(target)
            """


        # ====================================================
        # Existing server
        # ====================================================

        elif (
            target_kind
            == "SERVER"
        ):

            target_record = session.run(
                """
                MATCH (target:Server {
                    server_id: $target_id
                })

                RETURN
                    target.server_id
                        AS target_id
                """,

                target_id=
                    target_id,
            ).single()


            if target_record is None:

                raise ValueError(
                    "Environmental server does "
                    "not exist in Neo4j: "
                    f"{target_id}"
                )


            target_query = """
            MATCH (event:Event {
                event_id: $event_id
            })

            MATCH (target:Server {
                server_id: $target_id
            })

            MERGE
                (event)-[:TARGETS]->(target)
            """


        # ====================================================
        # Existing cooling equipment
        # ====================================================

        elif (
            target_kind
            == "EQUIPMENT"
        ):

            target_record = session.run(
                """
                MATCH (target:Equipment {
                    equipment_id: $target_id
                })

                RETURN
                    target.equipment_id
                        AS target_id
                """,

                target_id=
                    target_id,
            ).single()


            if target_record is None:

                raise ValueError(
                    "Environmental equipment does "
                    "not exist in Neo4j: "
                    f"{target_id}"
                )


            target_query = """
            MATCH (event:Event {
                event_id: $event_id
            })

            MATCH (target:Equipment {
                equipment_id: $target_id
            })

            MERGE
                (event)-[:TARGETS]->(target)
            """


        # ====================================================
        # Hard-drive asset
        # ====================================================

        elif (
            target_kind
            == "ASSET"
        ):

            server_id = entities.get(
                "server_id"
            )


            if not server_id:

                raise ValueError(
                    "Mapped environmental hard-drive "
                    "event has no host server_id."
                )


            server_record = session.run(
                """
                MATCH (server:Server {
                    server_id: $server_id
                })

                RETURN
                    server.server_id
                        AS server_id
                """,

                server_id=
                    server_id,
            ).single()


            if server_record is None:

                raise ValueError(
                    "Environmental hard-drive host "
                    "server does not exist: "
                    f"{server_id}"
                )


            # ------------------------------------------------
            # Create/reuse drive asset and hosting relation
            # ------------------------------------------------

            session.run(
                """
                MATCH (server:Server {
                    server_id: $server_id
                })

                MERGE (asset:Asset {
                    asset_id: $asset_id
                })

                SET
                    asset.asset_type =
                        "HARD_DRIVE",

                    asset.serial_number =
                        $asset_id

                MERGE
                    (asset)-[:HOSTED_BY]->(server)
                """,

                server_id=
                    server_id,

                asset_id=
                    target_id,
            ).consume()


            target_query = """
            MATCH (event:Event {
                event_id: $event_id
            })

            MATCH (target:Asset {
                asset_id: $target_id
            })

            MERGE
                (event)-[:TARGETS]->(target)
            """


        else:

            raise RuntimeError(
                "Unexpected environmental "
                f"target kind: {target_kind}"
            )


        # ====================================================
        # Persist Event node
        # ====================================================

        event_query = """
        MERGE (event:Event {
            event_id: $event_id
        })

        SET
            event.schema_version =
                $schema_version,

            event.timestamp =
                datetime($timestamp),

            event.window_start =
                datetime($window_start),

            event.window_end =
                datetime($window_end),

            event.domain =
                $domain,

            event.event_type =
                $event_type,

            event.component =
                $component,

            event.component_version =
                $component_version,

            event.model_name =
                $model_name,

            event.state =
                $state,

            event.confidence =
                $confidence,

            event.score =
                $score,

            event.anomaly_detected =
                $anomaly_detected,

            event.environmental_source_class =
                $environmental_source_class,

            event.environmental_asset_type =
                $environmental_asset_type,

            event.temperature_c =
                $temperature_c,

            event.humidity_pct =
                $humidity_pct,

            event.topology_mapping_source =
                $topology_mapping_source,

            event.source_type =
                $source_type,

            event.dataset_name =
                $dataset_name,

            event.synthetic_mapping =
                $synthetic_mapping,

            event.mapping_type =
                $mapping_type,

            event.scenario_id =
                $scenario_id,

            event.original_event_id =
                $original_event_id,

            event.original_timestamp =
                datetime($original_timestamp)
        """


        parameters = {
            **properties,

            "environmental_source_class":
                source_class,

            "environmental_asset_type":
                source_asset_type,

            "temperature_c":
                temperature_c,

            "humidity_pct":
                humidity_pct,

            "topology_mapping_source":
                topology_mapping_source,
        }


        session.run(
            event_query,
            **parameters
        ).consume()


        # ====================================================
        # Event -> target
        #
        # IMPORTANT:
        # target_query is a separate Cypher execution.
        # Therefore both event_id and target_id must be
        # supplied explicitly.
        # ====================================================

        session.run(
            target_query,

            event_id=
                event[
                    "event_id"
                ],

            target_id=
                target_id,
        ).consume()


        # ====================================================
        # Verify Event -> TARGETS relationship
        # ====================================================

        if (
            target_kind
            == "SENSOR"
        ):

            verification_query = """
            MATCH
                (event:Event {
                    event_id: $event_id
                })
                -[:TARGETS]->
                (target:Sensor {
                    sensor_id: $target_id
                })

            RETURN
                event.event_id
                    AS event_id
            """


        elif (
            target_kind
            == "SERVER"
        ):

            verification_query = """
            MATCH
                (event:Event {
                    event_id: $event_id
                })
                -[:TARGETS]->
                (target:Server {
                    server_id: $target_id
                })

            RETURN
                event.event_id
                    AS event_id
            """


        elif (
            target_kind
            == "EQUIPMENT"
        ):

            verification_query = """
            MATCH
                (event:Event {
                    event_id: $event_id
                })
                -[:TARGETS]->
                (target:Equipment {
                    equipment_id: $target_id
                })

            RETURN
                event.event_id
                    AS event_id
            """


        else:

            verification_query = """
            MATCH
                (event:Event {
                    event_id: $event_id
                })
                -[:TARGETS]->
                (target:Asset {
                    asset_id: $target_id
                })

            RETURN
                event.event_id
                    AS event_id
            """


        target_verification = session.run(
            verification_query,

            event_id=
                event[
                    "event_id"
                ],

            target_id=
                target_id,
        ).single()


        if target_verification is None:

            raise RuntimeError(
                "Environmental Event -> TARGETS "
                "relationship was not created."
            )


        # ====================================================
        # Return persisted event context
        # ====================================================

        record = session.run(
            """
            MATCH (event:Event {
                event_id: $event_id
            })

            RETURN
                event.event_id
                    AS event_id,

                event.environmental_source_class
                    AS source_class,

                event.environmental_asset_type
                    AS source_asset_type,

                event.state
                    AS state,

                event.temperature_c
                    AS temperature_c,

                event.humidity_pct
                    AS humidity_pct
            """,

            event_id=
                event[
                    "event_id"
                ],
        ).single()


        if record is None:

            raise RuntimeError(
                "Environmental event ingestion "
                "returned no event."
            )


        return {
            "event_id":
                record[
                    "event_id"
                ],

            "source_class":
                record[
                    "source_class"
                ],

            "source_asset_type":
                record[
                    "source_asset_type"
                ],

            "state":
                record[
                    "state"
                ],

            "temperature_c":
                record[
                    "temperature_c"
                ],

            "humidity_pct":
                record[
                    "humidity_pct"
                ],

            "target_kind":
                target_kind,

            "target_id":
                target_id,
        }


# ============================================================
# Ingest mapped Face Recognition event
# ============================================================

def ingest_face_event(
    event,
    driver,
):
    """
    Persist one mapped Face Recognition event.

    Recognized identity:
        Event -[:OBSERVED_BY]-> Camera
        Event -[:IDENTIFIES]-> Person

    Unknown identity:
        Event -[:OBSERVED_BY]-> Camera

        No Person:UNKNOWN node is created.

    Authorization is NOT determined by the Face model.
    This function reports graph-derived authorization context
    for recognized identities only.
    """

    # ========================================================
    # Common Event Schema
    # ========================================================

    validate_event(
        event
    )


    if (
        event[
            "domain"
        ]
        != "PHYSICAL_SECURITY"
    ):

        raise ValueError(
            "ingest_face_event expected "
            "PHYSICAL_SECURITY domain."
        )


    if (
        event[
            "event_type"
        ]
        != "FACE_IDENTIFICATION_ASSESSMENT"
    ):

        raise ValueError(
            "ingest_face_event expected "
            "FACE_IDENTIFICATION_ASSESSMENT."
        )


    # ========================================================
    # Mapping contract
    #
    # Do not use validate_mapped_event():
    # Face observations do not require server_id.
    # ========================================================

    provenance = event[
        "provenance"
    ]


    if (
        provenance[
            "synthetic_mapping"
        ]
        is not True
    ):

        raise ValueError(
            "Face event must be topology/scenario "
            "mapped before graph ingestion."
        )


    if (
        provenance[
            "mapping_type"
        ]
        != "SYNTHETIC_SCENARIO"
    ):

        raise ValueError(
            "Expected mapping_type "
            "SYNTHETIC_SCENARIO."
        )


    if not provenance.get(
        "scenario_id"
    ):

        raise ValueError(
            "Mapped face event has no scenario_id."
        )


    # ========================================================
    # Observation context
    # ========================================================

    entities = event[
        "entities"
    ]

    location = event[
        "location"
    ]

    evidence = event.get(
        "evidence",
        {}
    )


    person_id = entities.get(
        "person_id"
    )

    camera_id = entities.get(
        "camera_id"
    )

    zone_id = location.get(
        "zone_id"
    )

    access_point_id = location.get(
        "access_point_id"
    )


    if not person_id:

        raise ValueError(
            "Mapped face event has no person_id."
        )


    if not camera_id:

        raise ValueError(
            "Mapped face event has no camera_id."
        )


    if not zone_id:

        raise ValueError(
            "Mapped face event has no zone_id."
        )


    recognition_status = evidence.get(
        "recognition_status"
    )


    if recognition_status not in {
        "RECOGNIZED",
        "UNKNOWN",
        "NO_FACE",
        "MULTIPLE_FACES",
    }:

        raise ValueError(
            "Unsupported face recognition status: "
            f"{recognition_status}"
        )


    if (
        recognition_status
        == "RECOGNIZED"
        and person_id
        == "UNKNOWN"
    ):

        raise ValueError(
            "RECOGNIZED face cannot use "
            "person_id=UNKNOWN."
        )


    if (
        recognition_status
        != "RECOGNIZED"
        and person_id
        != "UNKNOWN"
    ):

        raise ValueError(
            "Non-recognized face state must "
            "use person_id=UNKNOWN."
        )


    properties = build_event_properties(
        event
    )


    distance = evidence.get(
        "distance"
    )

    similarity = evidence.get(
        "similarity"
    )

    threshold = evidence.get(
        "threshold"
    )

    nearest_employee_id = (
        evidence.get(
            "nearest_employee_id"
        )
    )

    face_count = evidence.get(
        "face_count"
    )

    face_confidence = evidence.get(
        "face_confidence"
    )

    latency_ms = evidence.get(
        "latency_ms"
    )


    # ========================================================
    # Neo4j persistence
    # ========================================================

    with driver.session(
        database=NEO4J_DATABASE
    ) as session:


        # ====================================================
        # Camera must already exist in loaded topology.
        # ====================================================

        camera_record = session.run(
            """
            MATCH (camera:Camera {
                camera_id: $camera_id
            })

            RETURN
                camera.camera_id
                    AS camera_id
            """,

            camera_id=
                camera_id,
        ).single()


        if camera_record is None:

            raise ValueError(
                "Face observation camera does not "
                "exist in Neo4j: "
                f"{camera_id}"
            )


        # ====================================================
        # Verify mapped Zone exists.
        # ====================================================

        zone_record = session.run(
            """
            MATCH (zone:Zone {
                zone_id: $zone_id
            })

            RETURN
                zone.zone_id
                    AS zone_id
            """,

            zone_id=
                zone_id,
        ).single()


        if zone_record is None:

            raise ValueError(
                "Face observation zone does not "
                "exist in Neo4j: "
                f"{zone_id}"
            )


        # ====================================================
        # Verify camera actually monitors mapped Zone.
        # ====================================================

        camera_zone = session.run(
            """
            MATCH
                (camera:Camera {
                    camera_id: $camera_id
                })
                -[:MONITORS]->
                (zone:Zone {
                    zone_id: $zone_id
                })

            RETURN
                camera.camera_id
                    AS camera_id,

                zone.zone_id
                    AS zone_id
            """,

            camera_id=
                camera_id,

            zone_id=
                zone_id,
        ).single()


        if camera_zone is None:

            raise ValueError(
                "Mapped face camera does not monitor "
                f"mapped zone: {camera_id} -> {zone_id}"
            )


        # ====================================================
        # If an access point is supplied, verify that too.
        # ====================================================

        if access_point_id:

            camera_access = session.run(
                """
                MATCH
                    (camera:Camera {
                        camera_id: $camera_id
                    })
                    -[:MONITORS]->
                    (access:AccessPoint {
                        access_point_id:
                            $access_point_id
                    })

                RETURN
                    access.access_point_id
                        AS access_point_id
                """,

                camera_id=
                    camera_id,

                access_point_id=
                    access_point_id,
            ).single()


            if camera_access is None:

                raise ValueError(
                    "Mapped face camera does not "
                    "monitor mapped access point: "
                    f"{camera_id} -> "
                    f"{access_point_id}"
                )


        # ====================================================
        # Persist Event node
        # ====================================================

        event_query = """
        MERGE (event:Event {
            event_id: $event_id
        })

        SET
            event.schema_version =
                $schema_version,

            event.timestamp =
                datetime($timestamp),

            event.window_start =
                datetime($window_start),

            event.window_end =
                datetime($window_end),

            event.domain =
                $domain,

            event.event_type =
                $event_type,

            event.component =
                $component,

            event.component_version =
                $component_version,

            event.model_name =
                $model_name,

            event.state =
                $state,

            event.confidence =
                $confidence,

            event.score =
                $score,

            event.anomaly_detected =
                $anomaly_detected,

            event.recognition_status =
                $recognition_status,

            event.person_id =
                $person_id,

            event.camera_id =
                $camera_id,

            event.zone_id =
                $zone_id,

            event.access_point_id =
                $access_point_id,

            event.face_distance =
                $face_distance,

            event.face_similarity =
                $face_similarity,

            event.face_threshold =
                $face_threshold,

            event.nearest_employee_id =
                $nearest_employee_id,

            event.face_count =
                $face_count,

            event.face_confidence =
                $face_confidence,

            event.latency_ms =
                $latency_ms,

            event.source_type =
                $source_type,

            event.dataset_name =
                $dataset_name,

            event.synthetic_mapping =
                $synthetic_mapping,

            event.mapping_type =
                $mapping_type,

            event.scenario_id =
                $scenario_id,

            event.original_event_id =
                $original_event_id,

            event.original_timestamp =
                datetime($original_timestamp)
        """


        parameters = {
            **properties,

            "recognition_status":
                recognition_status,

            "person_id":
                person_id,

            "camera_id":
                camera_id,

            "zone_id":
                zone_id,

            "access_point_id":
                access_point_id,

            "face_distance":
                distance,

            "face_similarity":
                similarity,

            "face_threshold":
                threshold,

            "nearest_employee_id":
                nearest_employee_id,

            "face_count":
                face_count,

            "face_confidence":
                face_confidence,

            "latency_ms":
                latency_ms,
        }


        session.run(
            event_query,
            **parameters
        ).consume()


        # ====================================================
        # Event -> Camera
        # ====================================================

        session.run(
            """
            MATCH (event:Event {
                event_id: $event_id
            })

            MATCH (camera:Camera {
                camera_id: $camera_id
            })

            MERGE
                (event)-[:OBSERVED_BY]->(camera)
            """,

            event_id=
                event[
                    "event_id"
                ],

            camera_id=
                camera_id,
        ).consume()


        # ====================================================
        # Recognized identity -> existing Person node
        #
        # IMPORTANT:
        # Do not MERGE a Person here.
        #
        # Person identity/authorization belongs to the loaded
        # topology. This avoids inventing P004/P005 or UNKNOWN.
        # ====================================================

        person_exists = False


        if recognition_status == "RECOGNIZED":

            person_record = session.run(
                """
                MATCH (person:Person {
                    person_id: $person_id
                })

                RETURN
                    person.person_id
                        AS person_id
                """,

                person_id=
                    person_id,
            ).single()


            if person_record is not None:

                person_exists = True


                session.run(
                    """
                    MATCH (event:Event {
                        event_id: $event_id
                    })

                    MATCH (person:Person {
                        person_id: $person_id
                    })

                    MERGE
                        (event)-[:IDENTIFIES]->(person)
                    """,

                    event_id=
                        event[
                            "event_id"
                        ],

                    person_id=
                        person_id,
                ).consume()


        # ====================================================
        # Authorization resolution
        #
        # UNKNOWN:
        #     NOT_APPLICABLE
        #
        # Recognized but no topology Person:
        #     AUTHORIZATION_UNKNOWN
        #
        # Recognized Person with matching AUTHORIZED_FOR Zone:
        #     AUTHORIZED
        #
        # Recognized Person exists but lacks relation:
        #     UNAUTHORIZED
        # ====================================================

        if recognition_status != "RECOGNIZED":

            authorization_status = (
                "NOT_APPLICABLE"
            )


        elif not person_exists:

            authorization_status = (
                "AUTHORIZATION_UNKNOWN"
            )


        else:

            authorization_record = session.run(
                """
                MATCH (person:Person {
                    person_id: $person_id
                })

                MATCH (zone:Zone {
                    zone_id: $zone_id
                })

                OPTIONAL MATCH
                    (person)
                    -[authorization:AUTHORIZED_FOR]->
                    (zone)

                RETURN
                    count(authorization)
                        AS authorization_count
                """,

                person_id=
                    person_id,

                zone_id=
                    zone_id,
            ).single()


            if (
                authorization_record[
                    "authorization_count"
                ]
                > 0
            ):

                authorization_status = (
                    "AUTHORIZED"
                )


            else:

                authorization_status = (
                    "UNAUTHORIZED"
                )


        # ====================================================
        # Persist graph-derived authorization context
        #
        # This is Phase 2 context, not a Phase 1 model output.
        # ====================================================

        session.run(
            """
            MATCH (event:Event {
                event_id: $event_id
            })

            SET
                event.authorization_status =
                    $authorization_status
            """,

            event_id=
                event[
                    "event_id"
                ],

            authorization_status=
                authorization_status,
        ).consume()


        # ====================================================
        # Return persisted context
        # ====================================================

        record = session.run(
            """
            MATCH
                (event:Event {
                    event_id: $event_id
                })
                -[:OBSERVED_BY]->
                (camera:Camera)

            RETURN
                event.event_id
                    AS event_id,

                event.state
                    AS state,

                event.recognition_status
                    AS recognition_status,

                event.person_id
                    AS person_id,

                event.authorization_status
                    AS authorization_status,

                camera.camera_id
                    AS camera_id,

                event.zone_id
                    AS zone_id,

                event.access_point_id
                    AS access_point_id
            """,

            event_id=
                event[
                    "event_id"
                ],
        ).single()


        if record is None:

            raise RuntimeError(
                "Face event ingestion returned "
                "no event/camera context."
            )


        return {
            "event_id":
                record[
                    "event_id"
                ],

            "state":
                record[
                    "state"
                ],

            "recognition_status":
                record[
                    "recognition_status"
                ],

            "person_id":
                record[
                    "person_id"
                ],

            "authorization_status":
                record[
                    "authorization_status"
                ],

            "camera_id":
                record[
                    "camera_id"
                ],

            "zone_id":
                record[
                    "zone_id"
                ],

            "access_point_id":
                record[
                    "access_point_id"
                ],
        }

# ============================================================
# Ingest mapped PPE Compliance event
# ============================================================

def ingest_ppe_event(
    event,
    driver,
):
    """
    Persist one mapped PPE Compliance event.

    Graph structure:

        Event -[:OBSERVED_BY]-> Camera

    Existing Camera -> Zone / AccessPoint topology is reused.

    IMPORTANT:
        - person_index remains frame-local evidence
        - no Person node is created
        - no IDENTIFIES relationship is created
        - authorization is not evaluated
        - PPE state/evidence is preserved
    """

    # ========================================================
    # Common Event Schema
    # ========================================================

    validate_event(
        event
    )


    if (
        event[
            "domain"
        ]
        != "SAFETY"
    ):

        raise ValueError(
            "ingest_ppe_event expected "
            "SAFETY domain."
        )


    if (
        event[
            "event_type"
        ]
        != "PPE_COMPLIANCE_ASSESSMENT"
    ):

        raise ValueError(
            "ingest_ppe_event expected "
            "PPE_COMPLIANCE_ASSESSMENT."
        )


    # ========================================================
    # Mapping contract
    #
    # Do not use validate_mapped_event():
    # camera-observed PPE events do not require server_id.
    # ========================================================

    provenance = event[
        "provenance"
    ]


    if (
        provenance[
            "synthetic_mapping"
        ]
        is not True
    ):

        raise ValueError(
            "PPE event must be topology/scenario "
            "mapped before graph ingestion."
        )


    if (
        provenance[
            "mapping_type"
        ]
        != "SYNTHETIC_SCENARIO"
    ):

        raise ValueError(
            "Expected mapping_type "
            "SYNTHETIC_SCENARIO."
        )


    if not provenance.get(
        "scenario_id"
    ):

        raise ValueError(
            "Mapped PPE event has no scenario_id."
        )


    # ========================================================
    # Observation context
    # ========================================================

    entities = event[
        "entities"
    ]

    location = event[
        "location"
    ]

    evidence = event.get(
        "evidence",
        {}
    )


    camera_id = entities.get(
        "camera_id"
    )

    zone_id = location.get(
        "zone_id"
    )

    access_point_id = location.get(
        "access_point_id"
    )


    if not camera_id:

        raise ValueError(
            "Mapped PPE event has no camera_id."
        )


    if not zone_id:

        raise ValueError(
            "Mapped PPE event has no zone_id."
        )


    # PPE must never claim employee identity.

    if entities.get(
        "person_id"
    ) is not None:

        raise ValueError(
            "PPE event must not contain "
            "an employee person_id."
        )


    # ========================================================
    # PPE evidence
    # ========================================================

    ppe_status = evidence.get(
        "ppe_status"
    )


    if ppe_status not in {
        "COMPLIANT",
        "NON_COMPLIANT",
        "NO_PERSON",
    }:

        raise ValueError(
            "Unsupported PPE status: "
            f"{ppe_status}"
        )


    state = event[
        "assessment"
    ][
        "state"
    ]


    expected_state = {
        "COMPLIANT":
            "PPE_COMPLIANT",

        "NON_COMPLIANT":
            "PPE_NON_COMPLIANT",

        "NO_PERSON":
            "NO_PERSON_DETECTED",
    }[
        ppe_status
    ]


    if state != expected_state:

        raise ValueError(
            "PPE status/state mismatch: "
            f"{ppe_status} -> {state}"
        )


    person_detected = evidence.get(
        "person_detected"
    )

    person_count = evidence.get(
        "person_count"
    )

    people = evidence.get(
        "people",
        []
    )


    if person_count != len(
        people
    ):

        raise ValueError(
            "PPE person_count does not match "
            "person-level evidence."
        )


    if (
        person_count > 0
        and person_detected
        is not True
    ):

        raise ValueError(
            "PPE event contains people but "
            "person_detected is not true."
        )


    if (
        person_count == 0
        and person_detected
        is not False
    ):

        raise ValueError(
            "PPE event has no people but "
            "person_detected is not false."
        )


    # ========================================================
    # Frozen PPE provenance
    # ========================================================

    detector_configuration = evidence.get(
        "detector_configuration"
    )

    detector_configuration_frozen = (
        evidence.get(
            "detector_configuration_frozen"
        )
    )

    policy_version = evidence.get(
        "policy_version"
    )

    policy_name = evidence.get(
        "policy_name"
    )

    policy_frozen = evidence.get(
        "policy_frozen"
    )

    confidence_threshold = evidence.get(
        "confidence_threshold"
    )

    iou_threshold = evidence.get(
        "iou_threshold"
    )

    association_method = evidence.get(
        "association_method"
    )

    association_minimum_containment = (
        evidence.get(
            "association_minimum_containment"
        )
    )

    latency_ms = evidence.get(
        "latency_ms"
    )


    if (
        detector_configuration_frozen
        is not True
    ):

        raise ValueError(
            "PPE detector configuration "
            "must remain frozen."
        )


    if policy_frozen is not True:

        raise ValueError(
            "PPE policy must remain frozen."
        )


    # ========================================================
    # Preserve person-level evidence as JSON
    #
    # Neo4j node properties cannot directly store arbitrary
    # nested dictionaries/lists-of-dictionaries.
    #
    # Therefore preserve the complete person-level evidence
    # as deterministic JSON on the Event node.
    # ========================================================

    people_json = json.dumps(
        people,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
    )


    required_ppe_json = json.dumps(
        evidence.get(
            "required_ppe",
            [],
        ),
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
    )


    properties = build_event_properties(
        event
    )


    # ========================================================
    # Neo4j persistence
    # ========================================================

    with driver.session(
        database=NEO4J_DATABASE
    ) as session:


        # ====================================================
        # Camera must already exist.
        # ====================================================

        camera_record = session.run(
            """
            MATCH (camera:Camera {
                camera_id: $camera_id
            })

            RETURN
                camera.camera_id
                    AS camera_id
            """,

            camera_id=
                camera_id,
        ).single()


        if camera_record is None:

            raise ValueError(
                "PPE observation camera does not "
                "exist in Neo4j: "
                f"{camera_id}"
            )


        # ====================================================
        # Zone must already exist.
        # ====================================================

        zone_record = session.run(
            """
            MATCH (zone:Zone {
                zone_id: $zone_id
            })

            RETURN
                zone.zone_id
                    AS zone_id
            """,

            zone_id=
                zone_id,
        ).single()


        if zone_record is None:

            raise ValueError(
                "PPE observation zone does not "
                "exist in Neo4j: "
                f"{zone_id}"
            )


        # ====================================================
        # Camera must monitor mapped Zone.
        # ====================================================

        camera_zone = session.run(
            """
            MATCH
                (camera:Camera {
                    camera_id: $camera_id
                })
                -[:MONITORS]->
                (zone:Zone {
                    zone_id: $zone_id
                })

            RETURN
                camera.camera_id
                    AS camera_id,

                zone.zone_id
                    AS zone_id
            """,

            camera_id=
                camera_id,

            zone_id=
                zone_id,
        ).single()


        if camera_zone is None:

            raise ValueError(
                "Mapped PPE camera does not monitor "
                f"mapped zone: "
                f"{camera_id} -> {zone_id}"
            )


        # ====================================================
        # Optional AccessPoint verification
        # ====================================================

        if access_point_id:

            camera_access = session.run(
                """
                MATCH
                    (camera:Camera {
                        camera_id: $camera_id
                    })
                    -[:MONITORS]->
                    (access:AccessPoint {
                        access_point_id:
                            $access_point_id
                    })

                RETURN
                    access.access_point_id
                        AS access_point_id
                """,

                camera_id=
                    camera_id,

                access_point_id=
                    access_point_id,
            ).single()


            if camera_access is None:

                raise ValueError(
                    "Mapped PPE camera does not "
                    "monitor mapped access point: "
                    f"{camera_id} -> "
                    f"{access_point_id}"
                )


        # ====================================================
        # Persist Event
        # ====================================================

        event_query = """
        MERGE (event:Event {
            event_id: $event_id
        })

        SET
            event.schema_version =
                $schema_version,

            event.timestamp =
                datetime($timestamp),

            event.window_start =
                datetime($window_start),

            event.window_end =
                datetime($window_end),

            event.domain =
                $domain,

            event.event_type =
                $event_type,

            event.component =
                $component,

            event.component_version =
                $component_version,

            event.model_name =
                $model_name,

            event.state =
                $state,

            event.confidence =
                $confidence,

            event.score =
                $score,

            event.anomaly_detected =
                $anomaly_detected,

            event.ppe_status =
                $ppe_status,

            event.person_detected =
                $person_detected,

            event.person_count =
                $person_count,

            event.people_json =
                $people_json,

            event.required_ppe_json =
                $required_ppe_json,

            event.detector_configuration =
                $detector_configuration,

            event.detector_configuration_frozen =
                $detector_configuration_frozen,

            event.policy_version =
                $policy_version,

            event.policy_name =
                $policy_name,

            event.policy_frozen =
                $policy_frozen,

            event.confidence_threshold =
                $confidence_threshold,

            event.iou_threshold =
                $iou_threshold,

            event.association_method =
                $association_method,

            event.association_minimum_containment =
                $association_minimum_containment,

            event.camera_id =
                $camera_id,

            event.zone_id =
                $zone_id,

            event.access_point_id =
                $access_point_id,

            event.latency_ms =
                $latency_ms,

            event.employee_identity_evaluated =
                false,

            event.authorization_evaluated =
                false,

            event.source_type =
                $source_type,

            event.dataset_name =
                $dataset_name,

            event.synthetic_mapping =
                $synthetic_mapping,

            event.mapping_type =
                $mapping_type,

            event.scenario_id =
                $scenario_id,

            event.original_event_id =
                $original_event_id,

            event.original_timestamp =
                datetime($original_timestamp)
        """


        parameters = {
            **properties,

            "ppe_status":
                ppe_status,

            "person_detected":
                person_detected,

            "person_count":
                person_count,

            "people_json":
                people_json,

            "required_ppe_json":
                required_ppe_json,

            "detector_configuration":
                detector_configuration,

            "detector_configuration_frozen":
                detector_configuration_frozen,

            "policy_version":
                policy_version,

            "policy_name":
                policy_name,

            "policy_frozen":
                policy_frozen,

            "confidence_threshold":
                confidence_threshold,

            "iou_threshold":
                iou_threshold,

            "association_method":
                association_method,

            "association_minimum_containment":
                association_minimum_containment,

            "camera_id":
                camera_id,

            "zone_id":
                zone_id,

            "access_point_id":
                access_point_id,

            "latency_ms":
                latency_ms,
        }


        session.run(
            event_query,
            **parameters
        ).consume()


        # ====================================================
        # Event -> Camera
        # ====================================================

        session.run(
            """
            MATCH (event:Event {
                event_id: $event_id
            })

            MATCH (camera:Camera {
                camera_id: $camera_id
            })

            MERGE
                (event)-[:OBSERVED_BY]->(camera)
            """,

            event_id=
                event[
                    "event_id"
                ],

            camera_id=
                camera_id,
        ).consume()


        # ====================================================
        # IMPORTANT:
        #
        # Do NOT create:
        #   Person nodes
        #   IDENTIFIES relationships
        #   authorization relationships
        #
        # person_index remains event evidence only.
        # ====================================================


        # ====================================================
        # Return persisted context
        # ====================================================

        record = session.run(
            """
            MATCH
                (event:Event {
                    event_id: $event_id
                })
                -[:OBSERVED_BY]->
                (camera:Camera)

            RETURN
                event.event_id
                    AS event_id,

                event.state
                    AS state,

                event.ppe_status
                    AS ppe_status,

                event.anomaly_detected
                    AS anomaly_detected,

                event.person_detected
                    AS person_detected,

                event.person_count
                    AS person_count,

                event.people_json
                    AS people_json,

                event.policy_version
                    AS policy_version,

                event.camera_id
                    AS camera_id,

                event.zone_id
                    AS zone_id,

                event.access_point_id
                    AS access_point_id,

                event.employee_identity_evaluated
                    AS employee_identity_evaluated,

                event.authorization_evaluated
                    AS authorization_evaluated
            """,

            event_id=
                event[
                    "event_id"
                ],
        ).single()


        if record is None:

            raise RuntimeError(
                "PPE event ingestion returned "
                "no event/camera context."
            )


        return {
            "event_id":
                record[
                    "event_id"
                ],

            "state":
                record[
                    "state"
                ],

            "ppe_status":
                record[
                    "ppe_status"
                ],

            "anomaly_detected":
                record[
                    "anomaly_detected"
                ],

            "person_detected":
                record[
                    "person_detected"
                ],

            "person_count":
                record[
                    "person_count"
                ],

            "people":
                json.loads(
                    record[
                        "people_json"
                    ]
                ),

            "policy_version":
                record[
                    "policy_version"
                ],

            "camera_id":
                record[
                    "camera_id"
                ],

            "zone_id":
                record[
                    "zone_id"
                ],

            "access_point_id":
                record[
                    "access_point_id"
                ],

            "employee_identity_evaluated":
                record[
                    "employee_identity_evaluated"
                ],

            "authorization_evaluated":
                record[
                    "authorization_evaluated"
                ],
        }

# ============================================================
# Create driver helper
# ============================================================

def create_driver():

    if not NEO4J_PASSWORD:

        raise ValueError(
            "NEO4J_PASSWORD is missing."
        )


    driver = GraphDatabase.driver(
        NEO4J_URI,
        auth=(
            NEO4J_USER,
            NEO4J_PASSWORD
        )
    )


    driver.verify_connectivity()

    return driver