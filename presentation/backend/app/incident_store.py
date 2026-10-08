"""In-memory, process-local snapshots of validated pipeline runs.

Controlled test data only. Restart clears this store; it is not a production
incident repository. No synthetic event feed is represented as live telemetry.
"""
from threading import RLock
from presentation.backend.app.schemas import IncidentView

_lock = RLock()
_incidents: dict[str, IncidentView] = {}

def remember(incident: IncidentView) -> IncidentView:
    with _lock:
        _incidents[incident.scenario_id] = incident
    return incident

def list_incidents() -> list[IncidentView]:
    with _lock:
        return list(_incidents.values())

def get_incident(scenario_id: str) -> IncidentView | None:
    with _lock:
        return _incidents.get(scenario_id)
