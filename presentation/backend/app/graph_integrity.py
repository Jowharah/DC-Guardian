"""Read-only graph integrity checks for controlled incident evidence."""
from reasoning.graph.ingest_event import NEO4J_DATABASE, create_driver

def check_graph_integrity(scenario_id: str, expected_event_ids: list[str]) -> dict:
    query = """
    MATCH (e:Event {scenario_id: $scenario_id})
    OPTIONAL MATCH (e)-[r]-(neighbor)
    RETURN e.event_id AS event_id, e.domain AS domain,
           type(r) AS relationship, labels(neighbor) AS neighbor_labels
    """
    driver = create_driver()
    try:
        with driver.session(database=NEO4J_DATABASE, default_access_mode="READ") as session:
            rows = session.run(query, scenario_id=scenario_id).data()
    finally:
        driver.close()
    observed = {row["event_id"] for row in rows if row["event_id"]}
    missing_events = sorted(set(expected_event_ids) - observed)
    ssh_events = {row["event_id"] for row in rows if row["domain"] == "CYBERSECURITY"}
    missing_source_links = sorted(
        event_id for event_id in ssh_events
        if not any(row["event_id"] == event_id
                   and row["relationship"] == "ORIGINATED_FROM"
                   and "SourceIP" in (row["neighbor_labels"] or [])
                   for row in rows)
    )
    return {
        "scenario_id": scenario_id,
        "status": "PASS" if not missing_events and not missing_source_links else "INCOMPLETE",
        "expected_event_count": len(set(expected_event_ids)),
        "observed_event_count": len(observed),
        "missing_event_ids": missing_events,
        "missing_ssh_source_relationships": missing_source_links,
    }
