"""Read-only, bounded Neo4j neighborhood for stored controlled incidents."""
from reasoning.graph.ingest_event import create_driver, NEO4J_DATABASE
from presentation.backend.app.authorization import Principal, Permission, allowed

NODE_KEYS = ("event_id", "zone_id", "rack_id", "server_id", "camera_id", "sensor_id", "asset_id", "equipment_id", "name")
EVENT_KEYS = ("domain", "state", "timestamp", "event_type")

def project_node(node, principal: Principal, zone: str) -> dict:
    node_id = str(node.element_id)
    labels = sorted(node.labels)
    node_type = labels[0] if labels else "Node"
    keys = EVENT_KEYS + NODE_KEYS if "Event" in labels else NODE_KEYS
    sensitive = None
    if "Person" in labels:
        sensitive = Permission.PERSON_DETAIL
        keys = ("person_id",)
    elif "SourceIP" in labels:
        sensitive = Permission.SSH_DETAIL
        keys = ("address",)
    if sensitive and not allowed(principal, sensitive, zone):
        return {"id": node_id, "label": node_type + " (restricted)",
                "type": node_type, "properties": {}, "restricted": True}
    properties = {key: node[key] for key in keys
                  if key in node and isinstance(node[key], (str, int, float, bool))}
    label = next((str(properties[k]) for k in ("person_id", "address") + NODE_KEYS
                  if k in properties), node_type)
    return {"id": node_id, "label": label, "type": node_type,
            "properties": properties, "restricted": False}

def graph_for_scenario(scenario_id: str, *, principal: Principal, zone: str) -> dict:
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
                    projected = project_node(node, principal, zone)
                    nodes[projected["id"]] = projected
                relation = row["r"]
                if relation is not None:
                    rel_id = str(relation.element_id)
                    edges[rel_id] = {"id": rel_id, "source": str(relation.start_node.element_id),
                                     "target": str(relation.end_node.element_id), "type": relation.type}
    finally:
        driver.close()
    return {"scenario_id": scenario_id, "source": "NEO4J_READ_ONLY",
            "nodes": list(nodes.values()), "edges": list(edges.values())}
