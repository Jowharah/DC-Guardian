"""
DC-Guardian Phase 2
Cross-Domain Graph Correlation Engine

Provides:

1. Pairwise cross-domain correlation
2. Multi-domain infrastructure correlation

Supported evidence domains:
    CYBERSECURITY
    MAINTENANCE
    ENVIRONMENTAL
    PHYSICAL_SECURITY

Correlation is deterministic and topology-based.
No ML or LLM reasoning is performed here.
"""

from reasoning.correlation.correlation_rules import (
    ABNORMAL_STATES,
    CORRELATION_SCOPE_RACK,
    CORRELATION_SCOPE_SERVER,
    CORRELATION_SCOPE_ZONE,
    CORRELATION_TYPE,
    DEFAULT_CORRELATION_WINDOW_MINUTES,
    PHYSICAL_SECURITY_ABNORMAL_AUTHORIZATION,
    PHYSICAL_SECURITY_ABNORMAL_STATES,
    SUPPORTED_DOMAINS,
)

from reasoning.graph.ingest_event import (
    NEO4J_DATABASE,
)


# ============================================================
# Validation
# ============================================================

def _validate_request(
    scenario_id,
    window_minutes,
):

    if (
        not isinstance(
            scenario_id,
            str,
        )
        or
        not scenario_id.strip()
    ):

        raise ValueError(
            "scenario_id must be a non-empty string."
        )


    if (
        not isinstance(
            window_minutes,
            int,
        )
        or
        window_minutes <= 0
    ):

        raise ValueError(
            "window_minutes must be a positive integer."
        )


# ============================================================
# Evidence independence
# ============================================================

def _classify_evidence_independence(
    domain,
    source_class,
):
    """
    Environmental sensors are independent infrastructure
    observations.

    Hardware-derived environmental telemetry is marked as
    RELATED_SOURCE.

    Other domains are PRIMARY.
    """

    if domain != "ENVIRONMENTAL":

        return "PRIMARY"


    if (
        source_class
        == "ENVIRONMENTAL_SENSOR"
    ):

        return "INDEPENDENT"


    if (
        source_class
        == "HARDWARE_TELEMETRY"
    ):

        return "RELATED_SOURCE"


    return "UNKNOWN"


# ============================================================
# Shared Cypher parameters
# ============================================================

def _correlation_parameters():

    return {
        "supported_domains":
            sorted(
                SUPPORTED_DOMAINS
            ),

        "abnormal_states":
            sorted(
                ABNORMAL_STATES
            ),

        "physical_security_abnormal_states":
            sorted(
                PHYSICAL_SECURITY_ABNORMAL_STATES
            ),

        "physical_security_abnormal_authorization":
            sorted(
                PHYSICAL_SECURITY_ABNORMAL_AUTHORIZATION
            ),
    }


# ============================================================
# Generic event topology contexts
# ============================================================

def resolve_event_contexts(
    driver,
    *,
    scenario_id,
):
    """
    Resolve abnormal events to the deepest truthful
    infrastructure context available.

    Supported paths:

        Event -> Server -> Rack -> Zone

        Event -> Asset -> HOSTED_BY
              -> Server -> Rack -> Zone

        Event -> Sensor -> MONITORS -> Zone

        Event -> Equipment -> LOCATED_IN -> Zone

        Event -> Camera -> MONITORS -> Zone

    Physical-security eligibility:

        UNKNOWN_PERSON

        OR

        authorization_status = UNAUTHORIZED

    AUTHORIZED and AUTHORIZATION_UNKNOWN observations are not
    treated as abnormal correlation evidence.
    """

    if (
        not isinstance(
            scenario_id,
            str,
        )
        or
        not scenario_id.strip()
    ):

        raise ValueError(
            "scenario_id must be a non-empty string."
        )


    query = """
    MATCH (e:Event)

    WHERE
        e.scenario_id = $scenario_id

        AND e.domain
            IN $supported_domains

        AND (
            e.state
                IN $abnormal_states

            OR (
                e.domain =
                    "PHYSICAL_SECURITY"

                AND e.state
                    IN
                    $physical_security_abnormal_states
            )

            OR (
                e.domain =
                    "PHYSICAL_SECURITY"

                AND e.authorization_status
                    IN
                    $physical_security_abnormal_authorization
            )
        )


    // =======================================================
    // Direct server target
    // =======================================================

    OPTIONAL MATCH
        (e)-[:TARGETS]->
        (direct_server:Server)

    OPTIONAL MATCH
        (direct_server)-[:LOCATED_IN]->
        (direct_rack:Rack)
        -[:LOCATED_IN]->
        (direct_zone:Zone)


    // =======================================================
    // Asset target -> host server
    // =======================================================

    OPTIONAL MATCH
        (e)-[:TARGETS]->
        (asset:Asset)
        -[:HOSTED_BY]->
        (asset_server:Server)

    OPTIONAL MATCH
        (asset_server)-[:LOCATED_IN]->
        (asset_rack:Rack)
        -[:LOCATED_IN]->
        (asset_zone:Zone)


    // =======================================================
    // Environmental sensor
    // =======================================================

    OPTIONAL MATCH
        (e)-[:TARGETS]->
        (sensor:Sensor)
        -[:MONITORS]->
        (sensor_zone:Zone)


    // =======================================================
    // Equipment
    // =======================================================

    OPTIONAL MATCH
        (e)-[:TARGETS]->
        (equipment:Equipment)
        -[:LOCATED_IN]->
        (equipment_zone:Zone)


    // =======================================================
    // Physical-security camera
    // =======================================================

    OPTIONAL MATCH
        (e)-[:OBSERVED_BY]->
        (camera:Camera)
        -[:MONITORS]->
        (camera_zone:Zone)


    WITH
        e,

        coalesce(
            direct_server.server_id,
            asset_server.server_id
        ) AS server_id,

        coalesce(
            direct_rack.rack_id,
            asset_rack.rack_id
        ) AS rack_id,

        coalesce(
            direct_zone.zone_id,
            asset_zone.zone_id,
            sensor_zone.zone_id,
            equipment_zone.zone_id,
            camera_zone.zone_id
        ) AS zone_id,

        CASE
            WHEN direct_server IS NOT NULL
            THEN "SERVER"

            WHEN asset IS NOT NULL
            THEN "ASSET"

            WHEN sensor IS NOT NULL
            THEN "SENSOR"

            WHEN equipment IS NOT NULL
            THEN "EQUIPMENT"

            WHEN camera IS NOT NULL
            THEN "CAMERA"

            ELSE "UNKNOWN"
        END AS topology_origin


    WHERE
        server_id IS NOT NULL
        OR rack_id IS NOT NULL
        OR zone_id IS NOT NULL


    RETURN DISTINCT
        e.event_id
            AS event_id,

        e.domain
            AS domain,

        e.state
            AS state,

        e.timestamp
            AS timestamp,

        e.authorization_status
            AS authorization_status,

        e.environmental_source_class
            AS environmental_source_class,

        e.environmental_asset_type
            AS environmental_asset_type,

        server_id,
        rack_id,
        zone_id,
        topology_origin

    ORDER BY
        timestamp,
        event_id
    """


    parameters = {
        **_correlation_parameters(),

        "scenario_id":
            scenario_id,
    }


    with driver.session(
        database=NEO4J_DATABASE
    ) as session:

        result = session.run(
            query,
            **parameters,
        )


        contexts = []


        for record in result:

            domain = record[
                "domain"
            ]

            source_class = record[
                "environmental_source_class"
            ]


            contexts.append(
                {
                    "event_id":
                        record[
                            "event_id"
                        ],

                    "domain":
                        domain,

                    "state":
                        record[
                            "state"
                        ],

                    "authorization_status":
                        record[
                            "authorization_status"
                        ],

                    "timestamp":
                        record[
                            "timestamp"
                        ],

                    "server_id":
                        record[
                            "server_id"
                        ],

                    "rack_id":
                        record[
                            "rack_id"
                        ],

                    "zone_id":
                        record[
                            "zone_id"
                        ],

                    "topology_origin":
                        record[
                            "topology_origin"
                        ],

                    "environmental_source_class":
                        source_class,

                    "environmental_asset_type":
                        record[
                            "environmental_asset_type"
                        ],

                    "evidence_independence":
                        _classify_evidence_independence(
                            domain,
                            source_class,
                        ),
                }
            )


    return contexts


# ============================================================
# Temporal helper
# ============================================================

def _seconds_between(
    left_timestamp,
    right_timestamp,
):

    raise RuntimeError(
        "_seconds_between should not be called."
    )


# ============================================================
# Pairwise correlation
# ============================================================

def find_cross_domain_correlations(
    driver,
    *,
    scenario_id,
    window_minutes=
        DEFAULT_CORRELATION_WINDOW_MINUTES,
):
    """
    Find abnormal cross-domain event pairs.

    Physical-security camera evidence resolves truthfully to
    Zone scope.
    """

    _validate_request(
        scenario_id,
        window_minutes,
    )


    query = """
    MATCH (left:Event)
    MATCH (right:Event)

    WHERE
        left.scenario_id = $scenario_id
        AND right.scenario_id = $scenario_id

        AND left.event_id < right.event_id

        AND left.domain
            IN $supported_domains

        AND right.domain
            IN $supported_domains


        // ===================================================
        // LEFT abnormal eligibility
        // ===================================================

        AND (
            left.state
                IN $abnormal_states

            OR (
                left.domain =
                    "PHYSICAL_SECURITY"

                AND left.state
                    IN
                    $physical_security_abnormal_states
            )

            OR (
                left.domain =
                    "PHYSICAL_SECURITY"

                AND left.authorization_status
                    IN
                    $physical_security_abnormal_authorization
            )
        )


        // ===================================================
        // RIGHT abnormal eligibility
        // ===================================================

        AND (
            right.state
                IN $abnormal_states

            OR (
                right.domain =
                    "PHYSICAL_SECURITY"

                AND right.state
                    IN
                    $physical_security_abnormal_states
            )

            OR (
                right.domain =
                    "PHYSICAL_SECURITY"

                AND right.authorization_status
                    IN
                    $physical_security_abnormal_authorization
            )
        )


        AND left.domain <> right.domain

        AND abs(
            duration.inSeconds(
                left.timestamp,
                right.timestamp
            ).seconds
        ) <= ($window_minutes * 60)


    // =======================================================
    // LEFT event topology
    // =======================================================

    OPTIONAL MATCH
        (left)-[:TARGETS]->
        (left_direct_server:Server)

    OPTIONAL MATCH
        (left_direct_server)-[:LOCATED_IN]->
        (left_direct_rack:Rack)
        -[:LOCATED_IN]->
        (left_direct_zone:Zone)


    OPTIONAL MATCH
        (left)-[:TARGETS]->
        (:Asset)
        -[:HOSTED_BY]->
        (left_asset_server:Server)

    OPTIONAL MATCH
        (left_asset_server)-[:LOCATED_IN]->
        (left_asset_rack:Rack)
        -[:LOCATED_IN]->
        (left_asset_zone:Zone)


    OPTIONAL MATCH
        (left)-[:TARGETS]->
        (:Sensor)
        -[:MONITORS]->
        (left_sensor_zone:Zone)


    OPTIONAL MATCH
        (left)-[:TARGETS]->
        (:Equipment)
        -[:LOCATED_IN]->
        (left_equipment_zone:Zone)


    OPTIONAL MATCH
        (left)-[:OBSERVED_BY]->
        (left_camera:Camera)
        -[:MONITORS]->
        (left_camera_zone:Zone)


    // =======================================================
    // RIGHT event topology
    // =======================================================

    OPTIONAL MATCH
        (right)-[:TARGETS]->
        (right_direct_server:Server)

    OPTIONAL MATCH
        (right_direct_server)-[:LOCATED_IN]->
        (right_direct_rack:Rack)
        -[:LOCATED_IN]->
        (right_direct_zone:Zone)


    OPTIONAL MATCH
        (right)-[:TARGETS]->
        (:Asset)
        -[:HOSTED_BY]->
        (right_asset_server:Server)

    OPTIONAL MATCH
        (right_asset_server)-[:LOCATED_IN]->
        (right_asset_rack:Rack)
        -[:LOCATED_IN]->
        (right_asset_zone:Zone)


    OPTIONAL MATCH
        (right)-[:TARGETS]->
        (:Sensor)
        -[:MONITORS]->
        (right_sensor_zone:Zone)


    OPTIONAL MATCH
        (right)-[:TARGETS]->
        (:Equipment)
        -[:LOCATED_IN]->
        (right_equipment_zone:Zone)


    OPTIONAL MATCH
        (right)-[:OBSERVED_BY]->
        (right_camera:Camera)
        -[:MONITORS]->
        (right_camera_zone:Zone)


    WITH
        left,
        right,

        coalesce(
            left_direct_server.server_id,
            left_asset_server.server_id
        ) AS left_server_id,

        coalesce(
            left_direct_rack.rack_id,
            left_asset_rack.rack_id
        ) AS left_rack_id,

        coalesce(
            left_direct_zone.zone_id,
            left_asset_zone.zone_id,
            left_sensor_zone.zone_id,
            left_equipment_zone.zone_id,
            left_camera_zone.zone_id
        ) AS left_zone_id,

        coalesce(
            right_direct_server.server_id,
            right_asset_server.server_id
        ) AS right_server_id,

        coalesce(
            right_direct_rack.rack_id,
            right_asset_rack.rack_id
        ) AS right_rack_id,

        coalesce(
            right_direct_zone.zone_id,
            right_asset_zone.zone_id,
            right_sensor_zone.zone_id,
            right_equipment_zone.zone_id,
            right_camera_zone.zone_id
        ) AS right_zone_id


    WITH
        left,
        right,

        CASE
            WHEN
                left_server_id IS NOT NULL
                AND
                left_server_id = right_server_id
            THEN "SERVER"

            WHEN
                left_rack_id IS NOT NULL
                AND
                left_rack_id = right_rack_id
            THEN "RACK"

            WHEN
                left_zone_id IS NOT NULL
                AND
                left_zone_id = right_zone_id
            THEN "ZONE"

            ELSE NULL
        END AS correlation_scope,

        CASE
            WHEN
                left_server_id IS NOT NULL
                AND
                left_server_id = right_server_id
            THEN left_server_id

            WHEN
                left_rack_id IS NOT NULL
                AND
                left_rack_id = right_rack_id
            THEN left_rack_id

            WHEN
                left_zone_id IS NOT NULL
                AND
                left_zone_id = right_zone_id
            THEN left_zone_id

            ELSE NULL
        END AS shared_entity_id


    WHERE correlation_scope IS NOT NULL


    RETURN DISTINCT
        left.event_id
            AS event_a_id,

        left.domain
            AS event_a_domain,

        left.state
            AS event_a_state,

        left.authorization_status
            AS event_a_authorization_status,

        left.timestamp
            AS event_a_timestamp,

        left.environmental_source_class
            AS event_a_source_class,


        right.event_id
            AS event_b_id,

        right.domain
            AS event_b_domain,

        right.state
            AS event_b_state,

        right.authorization_status
            AS event_b_authorization_status,

        right.timestamp
            AS event_b_timestamp,

        right.environmental_source_class
            AS event_b_source_class,


        correlation_scope,
        shared_entity_id

    ORDER BY
        event_a_id,
        event_b_id
    """


    parameters = {
        **_correlation_parameters(),

        "scenario_id":
            scenario_id,

        "window_minutes":
            window_minutes,
    }


    with driver.session(
        database=NEO4J_DATABASE
    ) as session:

        result = session.run(
            query,
            **parameters,
        )


        correlations = []


        for record in result:

            event_a_domain = record[
                "event_a_domain"
            ]

            event_b_domain = record[
                "event_b_domain"
            ]


            correlations.append(
                {
                    "correlation_type":
                        CORRELATION_TYPE,

                    "scenario_id":
                        scenario_id,

                    "scope":
                        record[
                            "correlation_scope"
                        ],

                    "shared_entity_id":
                        record[
                            "shared_entity_id"
                        ],

                    "events": [
                        {
                            "event_id":
                                record[
                                    "event_a_id"
                                ],

                            "domain":
                                event_a_domain,

                            "state":
                                record[
                                    "event_a_state"
                                ],

                            "authorization_status":
                                record[
                                    "event_a_authorization_status"
                                ],

                            "timestamp":
                                str(
                                    record[
                                        "event_a_timestamp"
                                    ]
                                ),

                            "evidence_independence":
                                _classify_evidence_independence(
                                    event_a_domain,
                                    record[
                                        "event_a_source_class"
                                    ],
                                ),
                        },

                        {
                            "event_id":
                                record[
                                    "event_b_id"
                                ],

                            "domain":
                                event_b_domain,

                            "state":
                                record[
                                    "event_b_state"
                                ],

                            "authorization_status":
                                record[
                                    "event_b_authorization_status"
                                ],

                            "timestamp":
                                str(
                                    record[
                                        "event_b_timestamp"
                                    ]
                                ),

                            "evidence_independence":
                                _classify_evidence_independence(
                                    event_b_domain,
                                    record[
                                        "event_b_source_class"
                                    ],
                                ),
                        },
                    ],
                }
            )


    return correlations


# ============================================================
# Multi-domain correlation
# ============================================================

def find_multi_domain_correlations(
    driver,
    *,
    scenario_id,
    window_minutes=
        DEFAULT_CORRELATION_WINDOW_MINUTES,
    minimum_domains=2,
):
    """
    Find infrastructure correlation containing multiple
    abnormal evidence domains.

    Deepest topology scope shared by ALL events:

        SERVER
        RACK
        ZONE

    Physical-security camera evidence contributes truthful
    Zone context only.
    """

    _validate_request(
        scenario_id,
        window_minutes,
    )


    if (
        not isinstance(
            minimum_domains,
            int,
        )
        or
        minimum_domains < 2
    ):

        raise ValueError(
            "minimum_domains must be "
            "an integer >= 2."
        )


    query = """
    MATCH (e:Event)

    WHERE
        e.scenario_id = $scenario_id

        AND e.domain
            IN $supported_domains

        AND (
            e.state
                IN $abnormal_states

            OR (
                e.domain =
                    "PHYSICAL_SECURITY"

                AND e.state
                    IN
                    $physical_security_abnormal_states
            )

            OR (
                e.domain =
                    "PHYSICAL_SECURITY"

                AND e.authorization_status
                    IN
                    $physical_security_abnormal_authorization
            )
        )


    // =======================================================
    // Resolve event -> topology
    // =======================================================

    OPTIONAL MATCH
        (e)-[:TARGETS]->
        (direct_server:Server)

    OPTIONAL MATCH
        (direct_server)-[:LOCATED_IN]->
        (direct_rack:Rack)
        -[:LOCATED_IN]->
        (direct_zone:Zone)


    OPTIONAL MATCH
        (e)-[:TARGETS]->
        (:Asset)
        -[:HOSTED_BY]->
        (asset_server:Server)

    OPTIONAL MATCH
        (asset_server)-[:LOCATED_IN]->
        (asset_rack:Rack)
        -[:LOCATED_IN]->
        (asset_zone:Zone)


    OPTIONAL MATCH
        (e)-[:TARGETS]->
        (:Sensor)
        -[:MONITORS]->
        (sensor_zone:Zone)


    OPTIONAL MATCH
        (e)-[:TARGETS]->
        (:Equipment)
        -[:LOCATED_IN]->
        (equipment_zone:Zone)


    OPTIONAL MATCH
        (e)-[:OBSERVED_BY]->
        (camera:Camera)
        -[:MONITORS]->
        (camera_zone:Zone)


    WITH
        e,

        coalesce(
            direct_server.server_id,
            asset_server.server_id
        ) AS server_id,

        coalesce(
            direct_rack.rack_id,
            asset_rack.rack_id
        ) AS rack_id,

        coalesce(
            direct_zone.zone_id,
            asset_zone.zone_id,
            sensor_zone.zone_id,
            equipment_zone.zone_id,
            camera_zone.zone_id
        ) AS zone_id


    WHERE zone_id IS NOT NULL


    // =======================================================
    // Group by Zone
    // =======================================================

    WITH
        zone_id,

        collect(DISTINCT {
            event_id:
                e.event_id,

            domain:
                e.domain,

            state:
                e.state,

            authorization_status:
                e.authorization_status,

            timestamp:
                e.timestamp,

            source_class:
                e.environmental_source_class,

            server_id:
                server_id,

            rack_id:
                rack_id,

            zone_id:
                zone_id
        }) AS events


    // =======================================================
    // Distinct domains
    // =======================================================

    WITH
        zone_id,
        events,

        reduce(
            domains = [],
            item IN events |
            CASE
                WHEN item.domain IN domains
                THEN domains
                ELSE domains + item.domain
            END
        ) AS domains


    WHERE
        size(domains)
        >= $minimum_domains


    // =======================================================
    // Temporal span
    // =======================================================

    UNWIND events AS event_item

    WITH
        zone_id,
        events,
        domains,

        min(
            event_item.timestamp
        ) AS earliest_timestamp,

        max(
            event_item.timestamp
        ) AS latest_timestamp


    WHERE
        abs(
            duration.inSeconds(
                earliest_timestamp,
                latest_timestamp
            ).seconds
        ) <= ($window_minutes * 60)


    // =======================================================
    // Determine strongest truthful common scope
    // =======================================================

    WITH
        zone_id,
        events,
        domains,
        earliest_timestamp,
        latest_timestamp,

        [
            item IN events
            WHERE item.server_id IS NOT NULL
            | item.server_id
        ] AS server_ids,

        [
            item IN events
            WHERE item.rack_id IS NOT NULL
            | item.rack_id
        ] AS rack_ids


    WITH
        zone_id,
        events,
        domains,
        earliest_timestamp,
        latest_timestamp,
        server_ids,
        rack_ids,

        reduce(
            unique_servers = [],
            server_id IN server_ids |

            CASE
                WHEN server_id
                    IN unique_servers

                THEN unique_servers

                ELSE
                    unique_servers
                    + server_id
            END
        ) AS unique_servers,

        reduce(
            unique_racks = [],
            rack_id IN rack_ids |

            CASE
                WHEN rack_id
                    IN unique_racks

                THEN unique_racks

                ELSE
                    unique_racks
                    + rack_id
            END
        ) AS unique_racks


    WITH
        zone_id,
        events,
        domains,
        earliest_timestamp,
        latest_timestamp,

        CASE
            WHEN
                size(server_ids)
                    = size(events)

                AND
                size(unique_servers)
                    = 1

            THEN "SERVER"

            WHEN
                size(rack_ids)
                    = size(events)

                AND
                size(unique_racks)
                    = 1

            THEN "RACK"

            ELSE "ZONE"
        END AS correlation_scope,

        CASE
            WHEN
                size(server_ids)
                    = size(events)

                AND
                size(unique_servers)
                    = 1

            THEN unique_servers[0]

            WHEN
                size(rack_ids)
                    = size(events)

                AND
                size(unique_racks)
                    = 1

            THEN unique_racks[0]

            ELSE zone_id
        END AS shared_entity_id


    RETURN
        correlation_scope,
        shared_entity_id,
        domains,
        events,
        earliest_timestamp,
        latest_timestamp

    ORDER BY
        shared_entity_id
    """


    parameters = {
        **_correlation_parameters(),

        "scenario_id":
            scenario_id,

        "window_minutes":
            window_minutes,

        "minimum_domains":
            minimum_domains,
    }


    with driver.session(
        database=NEO4J_DATABASE
    ) as session:

        result = session.run(
            query,
            **parameters,
        )


        correlations = []


        for record in result:

            raw_events = record[
                "events"
            ]


            events = []


            for item in raw_events:

                domain = item[
                    "domain"
                ]

                source_class = item.get(
                    "source_class"
                )


                events.append(
                    {
                        "event_id":
                            item[
                                "event_id"
                            ],

                        "domain":
                            domain,

                        "state":
                            item[
                                "state"
                            ],

                        "authorization_status":
                            item.get(
                                "authorization_status"
                            ),

                        "timestamp":
                            str(
                                item[
                                    "timestamp"
                                ]
                            ),

                        "server_id":
                            item.get(
                                "server_id"
                            ),

                        "rack_id":
                            item.get(
                                "rack_id"
                            ),

                        "zone_id":
                            item.get(
                                "zone_id"
                            ),

                        "evidence_independence":
                            _classify_evidence_independence(
                                domain,
                                source_class,
                            ),
                    }
                )


            events.sort(
                key=lambda item: (
                    item[
                        "timestamp"
                    ],

                    item[
                        "event_id"
                    ],
                )
            )


            domains = sorted(
                set(
                    record[
                        "domains"
                    ]
                )
            )


            correlations.append(
                {
                    "correlation_type":
                        CORRELATION_TYPE,

                    "scenario_id":
                        scenario_id,

                    "scope":
                        record[
                            "correlation_scope"
                        ],

                    "shared_entity_id":
                        record[
                            "shared_entity_id"
                        ],

                    "domains":
                        domains,

                    "domain_count":
                        len(
                            domains
                        ),

                    "event_count":
                        len(
                            events
                        ),

                    "window_minutes":
                        window_minutes,

                    "earliest_timestamp":
                        str(
                            record[
                                "earliest_timestamp"
                            ]
                        ),

                    "latest_timestamp":
                        str(
                            record[
                                "latest_timestamp"
                            ]
                        ),

                    "events":
                        events,
                }
            )


    return correlations
