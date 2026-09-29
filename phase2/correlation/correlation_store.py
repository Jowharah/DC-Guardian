"""
DC-Guardian Phase 2
Correlation Persistence

Persists deterministic cross-domain correlations into Neo4j.

A Correlation is derived Phase 2 evidence and is deliberately
stored separately from Event nodes.
"""

from datetime import datetime, timezone

from ingest_event import (
    NEO4J_DATABASE,
)



# ============================================================
# Allowed infrastructure identifiers for dynamic Cypher
# ============================================================
#
# Cypher parameters cannot represent labels/property names.
# Keep the only dynamic identifiers behind this closed mapping
# so arbitrary input can never become query syntax.
# ============================================================

INFRASTRUCTURE_BY_SCOPE = {
    "SERVER": (
        "Server",
        "server_id",
    ),
    "RACK": (
        "Rack",
        "rack_id",
    ),
    "ZONE": (
        "Zone",
        "zone_id",
    ),
}


# ============================================================
# Correlation ID
# ============================================================

def build_correlation_id(
    correlation,
):
    """
    Build a deterministic ID from the correlation contents.

    This makes repeated persistence idempotent.
    """

    scenario_id = correlation[
        "scenario_id"
    ]

    scope = correlation[
        "scope"
    ]

    shared_entity_id = correlation[
        "shared_entity_id"
    ]

    event_ids = sorted(
        event[
            "event_id"
        ]
        for event
        in correlation[
            "events"
        ]
    )

    event_component = "__".join(
        event_ids
    )

    return (
        f"CORR-{scenario_id}-"
        f"{scope}-"
        f"{shared_entity_id}-"
        f"{event_component}"
    )


# ============================================================
# Validation
# ============================================================

def validate_correlation(
    correlation,
):

    if not isinstance(
        correlation,
        dict,
    ):

        raise TypeError(
            "correlation must be a dictionary."
        )


    required = [
        "correlation_type",
        "scenario_id",
        "scope",
        "shared_entity_id",
        "events",
    ]


    missing = [
        field
        for field in required
        if field not in correlation
    ]


    if missing:

        raise ValueError(
            "Correlation is missing required fields: "
            + ", ".join(
                missing
            )
        )


    scenario_id = correlation[
        "scenario_id"
    ]

    shared_entity_id = correlation[
        "shared_entity_id"
    ]

    scope = correlation[
        "scope"
    ]


    if (
        not isinstance(
            scenario_id,
            str,
        )
        or not scenario_id.strip()
    ):

        raise ValueError(
            "scenario_id must be a non-empty string."
        )


    if (
        not isinstance(
            shared_entity_id,
            str,
        )
        or not shared_entity_id.strip()
    ):

        raise ValueError(
            "shared_entity_id must be a non-empty string."
        )


    if scope not in INFRASTRUCTURE_BY_SCOPE:

        raise ValueError(
            f"Unsupported correlation scope: {scope}"
        )


    events = correlation[
        "events"
    ]


    if (
        not isinstance(
            events,
            list,
        )
        or len(events) < 2
    ):

        raise ValueError(
            "Correlation must contain "
            "at least two events."
        )


    event_ids = [
        event.get(
            "event_id"
        )
        for event
        in events
    ]


    if any(
        not event_id
        for event_id
        in event_ids
    ):

        raise ValueError(
            "Every correlated event "
            "must contain event_id."
        )


    if len(
        set(
            event_ids
        )
    ) != len(
        event_ids
    ):

        raise ValueError(
            "Correlation contains "
            "duplicate events."
        )


    domains = {
        event.get(
            "domain"
        )
        for event
        in events
    }


    if len(
        domains
    ) < 2:

        raise ValueError(
            "Correlation must contain "
            "multiple domains."
        )


# ============================================================
# Persist correlation
# ============================================================

def persist_correlation(
    correlation,
    driver,
):
    """
    Persist one deterministic correlation.

    Creates:

        (:Correlation)
              ^
              |
        [:CONTRIBUTES_TO]
              |
           (:Event)

    and:

        (:Correlation)-[:CONCERNS]->(infrastructure)

    depending on SERVER / RACK / ZONE scope.
    """

    validate_correlation(
        correlation
    )


    correlation_id = (
        build_correlation_id(
            correlation
        )
    )


    correlation_type = (
        correlation[
            "correlation_type"
        ]
    )

    scenario_id = (
        correlation[
            "scenario_id"
        ]
    )

    scope = (
        correlation[
            "scope"
        ]
    )

    shared_entity_id = (
        correlation[
            "shared_entity_id"
        ]
    )


    if scope not in INFRASTRUCTURE_BY_SCOPE:

        raise ValueError(
            f"Unsupported correlation scope: "
            f"{scope}"
        )


    event_ids = [
        event[
            "event_id"
        ]
        for event
        in correlation[
            "events"
        ]
    ]


    domains = sorted(
        {
            event[
                "domain"
            ]
            for event
            in correlation[
                "events"
            ]
        }
    )


    created_at = (
        datetime.now(
            timezone.utc
        )
        .isoformat()
        .replace(
            "+00:00",
            "Z",
        )
    )


    with driver.session(
        database=NEO4J_DATABASE
    ) as session:

        # ====================================================
        # Verify all contributing events exist first
        # ====================================================

        record = session.run(
            """
            MATCH (e:Event)
            WHERE e.event_id IN $event_ids

            RETURN
                count(DISTINCT e)
                    AS event_count
            """,
            event_ids=
                event_ids,
        ).single()


        if (
            record is None
            or
            record[
                "event_count"
            ] != len(
                event_ids
            )
        ):

            raise ValueError(
                "One or more contributing events "
                "do not exist in Neo4j."
            )


        # ====================================================
        # Verify shared infrastructure exists
        # ====================================================

        (
            infrastructure_label,
            id_property,
        ) = INFRASTRUCTURE_BY_SCOPE[
            scope
        ]


        infrastructure_query = f"""
        MATCH (n:{infrastructure_label} {{
            {id_property}: $shared_entity_id
        }})

        RETURN count(n) AS count
        """


        record = session.run(
            infrastructure_query,
            shared_entity_id=
                shared_entity_id,
        ).single()


        if (
            record is None
            or
            record[
                "count"
            ] != 1
        ):

            raise ValueError(
                "Shared correlation infrastructure "
                "does not exist uniquely in Neo4j."
            )


        # ====================================================
        # Correlation + event relationships
        # ====================================================

        query = """
        MERGE (c:Correlation {
            correlation_id: $correlation_id
        })

        ON CREATE SET
            c.created_at =
                datetime($created_at)

        SET
            c.correlation_type =
                $correlation_type,

            c.scenario_id =
                $scenario_id,

            c.scope =
                $scope,

            c.shared_entity_id =
                $shared_entity_id,

            c.domains =
                $domains,

            c.event_count =
                size($event_ids)

        WITH
            c,
            $event_ids AS event_ids

        UNWIND event_ids AS event_id

        MATCH (e:Event {
            event_id: event_id
        })

        MERGE
            (e)-[:CONTRIBUTES_TO]->(c)

        WITH
            c,
            count(DISTINCT e) AS linked_event_count

        RETURN
            c.correlation_id AS correlation_id,
            c.event_count AS event_count,
            linked_event_count
        """


        result = session.run(
            query,

            correlation_id=
                correlation_id,

            created_at=
                created_at,

            correlation_type=
                correlation_type,

            scenario_id=
                scenario_id,

            scope=
                scope,

            shared_entity_id=
                shared_entity_id,

            domains=
                domains,

            event_ids=
                event_ids,
        ).single()


        if (
            result[
                "linked_event_count"
            ]
            != len(
                event_ids
            )
        ):

            raise RuntimeError(
                "Not all contributing events "
                "were linked to the correlation."
            )


        # ====================================================
        # Correlation -> infrastructure relationship
        # ====================================================

        concern_query = f"""
        MATCH (c:Correlation {{
            correlation_id: $correlation_id
        }})

        MATCH (n:{infrastructure_label} {{
            {id_property}: $shared_entity_id
        }})

        MERGE
            (c)-[:CONCERNS]->(n)

        RETURN
            c.correlation_id
                AS correlation_id
        """


        concern_result = session.run(
            concern_query,

            correlation_id=
                correlation_id,

            shared_entity_id=
                shared_entity_id,
        ).single()


        if concern_result is None:

            raise RuntimeError(
                "Correlation infrastructure "
                "relationship was not created."
            )


    return {
        "correlation_id":
            correlation_id,

        "correlation_type":
            correlation_type,

        "scenario_id":
            scenario_id,

        "scope":
            scope,

        "shared_entity_id":
            shared_entity_id,

        "event_count":
            len(
                event_ids
            ),

        "domains":
            domains,
    }