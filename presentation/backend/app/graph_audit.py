"""Minimal local audit of sensitive graph disclosure (no sensitive values)."""
import sqlite3
from datetime import datetime, timezone
from presentation.backend.app.incident_store import _db_path

def audit_graph_access(subject: str, scenario_id: str, zone: str, graph: dict) -> None:
    nodes = graph.get("nodes", [])
    source_count = sum(1 for n in nodes if n.get("type") == "SourceIP" and not n.get("restricted"))
    person_count = sum(1 for n in nodes if n.get("type") == "Person" and not n.get("restricted"))
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path, timeout=10) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS graph_access_audit "
            "(recorded_at TEXT, subject TEXT, scenario_id TEXT, zone TEXT, "
            "source_ip_nodes INTEGER, person_nodes INTEGER)"
        )
        conn.execute(
            "INSERT INTO graph_access_audit VALUES (?,?,?,?,?,?)",
            (datetime.now(timezone.utc).isoformat(), subject, scenario_id, zone, source_count, person_count),
        )
