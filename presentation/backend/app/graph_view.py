"""Read-only, bounded Neo4j neighborhood for stored controlled incidents."""
from reasoning.graph.ingest_event import create_driver, NEO4J_DATABASE

NODE_KEYS = ("event_id", "zone_id", "rack_id", "server_id", "camera_id", "sensor_id", "asset_id", "equipment_id", "name")
EVENT_KEYS = ("domain", "state", "timestamp", "event_type")

def graph_for_scenario(scenario_id: str) -> dict:
    query = """
    MATCH (e:Event {scenario_id: $scenario_id})
    WITH e ORDER BY e.event_id LIMIT 30
    OPTIONAL MATCH (e)-[r]-(n)
    RETURN e, r, n LIMIT 150
    """
    nodes: dict[str, dict] = {}
    edges: dict[str, dict] = {}
    driver = create_driver()
    try:
        with driver.session(database=NEO4J_DATABASE, default_access_mode="READ") as session:
            for row in session.run(query, scenario_id=scenario_id):
                for node in (row["e"], row["n"]):
                    if node is None:
                        continue
                    node_id = str(node.element_id)
                    labels = sorted(node.labels)
                    # Never expose person IDs, source IPs, arbitrary model evidence or biometric fields.
                    keys = EVENT_KEYS + NODE_KEYS if "Event" in labels else NODE_KEYS
                    if "Person" in labels or "SourceIP" in labels:
                        properties = {}
                        label = labels[0]
                    else:
                        properties = {key: node[key] for key in keys
                                      if key in node and isinstance(node[key], (str, int, float, bool))}
                        label = next((str(properties[k]) for k in NODE_KEYS if k in properties),
                                     labels[0] if labels else "Node")
                    nodes[node_id] = {"id": node_id, "label": label,
                                      "type": labels[0] if labels else "Node", "properties": properties}
                relation = row["r"]
                if relation is not None:
                    rel_id = str(relation.element_id)
                    edges[rel_id] = {"id": rel_id, "source": str(relation.start_node.element_id),
                                     "target": str(relation.end_node.element_id), "type": relation.type}
    finally:
        driver.close()
    return {"scenario_id": scenario_id, "source": "NEO4J_READ_ONLY",
            "nodes": list(nodes.values()), "edges": list(edges.values())}
