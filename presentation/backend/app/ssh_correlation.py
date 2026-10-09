"""Read-only cross-domain correlation for one ingested SSH event.

The existing correlation engine is scenario-scoped; unrelated scenarios are
never combined, and an empty result is not represented as an error.
"""
from reasoning.graph.ingest_event import create_driver
from reasoning.correlation.correlation_engine import find_cross_domain_correlations

def check_ssh_correlations(scenario_id: str, graph_event_id: str) -> dict:
    driver = create_driver()
    try:
        candidates = find_cross_domain_correlations(
            driver, scenario_id=scenario_id, window_minutes=15)
    finally:
        driver.close()
    matches = [c for c in candidates if graph_event_id in c.get("event_ids", [])
               or graph_event_id in c.get("evidence_event_ids", [])]
    # Correlation engine outputs may differ by rule; never return an unrelated pair.
    return {"status": "CORRELATED" if matches else "NO_CORRELATION",
            "correlation_count": len(matches), "scenario_id": scenario_id,
            "graph_event_id": graph_event_id,
            "scope": "SCENARIO_ONLY",
            "note": "Only same-scenario evidence is eligible; no companion events generated."}
