"""Read-only authorization assessment for retained face observations.

A missing graph person or zone is UNKNOWN, never UNAUTHORIZED.
"""
from reasoning.graph.ingest_event import create_driver, NEO4J_DATABASE

QUERY = """
OPTIONAL MATCH (p:Person {person_id: $person_id})
OPTIONAL MATCH (z:Zone {zone_id: $zone_id})
RETURN p IS NOT NULL AS person_exists,
       z IS NOT NULL AS zone_exists,
       EXISTS { MATCH (p)-[:AUTHORIZED_FOR]->(z) } AS authorized
"""

_driver = None

def _shared_driver():
    """One long-lived driver: opening a connection costs seconds, a query ms."""
    global _driver
    if _driver is None:
        _driver = create_driver()
    return _driver

def _reset_driver():
    global _driver
    try:
        if _driver is not None:
            _driver.close()
    finally:
        _driver = None

def assess(person_id: str, zone_id: str) -> dict:
    base = {"status": "UNKNOWN", "source": "NEO4J_READ_ONLY",
            "reason": "GRAPH_UNAVAILABLE"}
    if not person_id or person_id == "UNKNOWN":
        return {**base, "reason": "IDENTITY_NOT_RECOGNIZED"}
    try:
        with _shared_driver().session(database=NEO4J_DATABASE, default_access_mode="READ") as session:
            record = session.run(QUERY, person_id=person_id, zone_id=zone_id).single()
    except Exception:
        # Drop a broken connection so the next call reconnects.
        _reset_driver()
        return base
    if record is None or not record["person_exists"]:
        return {**base, "reason": "PERSON_NOT_IN_TOPOLOGY"}
    if not record["zone_exists"]:
        return {**base, "reason": "ZONE_NOT_IN_TOPOLOGY"}
    return {"status": "AUTHORIZED" if record["authorized"] else "UNAUTHORIZED",
            "source": "NEO4J_READ_ONLY", "reason": "GRAPH_RELATIONSHIP_CHECK"}
