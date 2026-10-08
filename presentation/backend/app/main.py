"""DC-GUARDIAN Presentation API — local controlled prototype only."""
from fastapi import FastAPI, HTTPException, Query
from presentation.backend.app.custom_scenarios import (
    CustomScenarioInput, CustomScenarioResult, topology_options,
    assess_custom_environment,
)
from presentation.backend.app.schemas import IncidentView, ScenarioInfo
from presentation.backend.app.incident_store import remember, list_incidents, get_incident
from presentation.backend.app.service import execute_scenario, list_scenarios
from presentation.backend.app.graph_view import graph_for_scenario

app = FastAPI(
    title="DC-GUARDIAN Presentation API", version="0.1.0",
    docs_url=None, redoc_url=None,
)

@app.get("/api/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok", "mode": "CONTROLLED_PROTOTYPE"}

@app.get("/api/v1/scenarios", response_model=list[ScenarioInfo])
def scenarios() -> list[ScenarioInfo]:
    return list_scenarios()

@app.post("/api/v1/scenarios/{name}/run", response_model=IncidentView)
def run_scenario(
    name: str,
    run_id: str | None = Query(default=None, pattern=r"^DCG-[A-Z0-9_-]{1,90}$", max_length=94),
) -> IncidentView:
    # Local prototype only; authentication and authorization not yet implemented.
    try:
        incident = execute_scenario(name, scenario_id=run_id) if run_id else execute_scenario(name)
        return remember(incident)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

@app.get("/api/v1/topology/options")
def get_topology_options() -> list[dict]:
    return topology_options()

@app.post("/api/v1/custom-scenarios/environment", response_model=CustomScenarioResult)
def custom_environment(payload: CustomScenarioInput) -> CustomScenarioResult:
    try:
        return assess_custom_environment(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

@app.get("/api/v1/incidents", response_model=list[IncidentView])
def incidents() -> list[IncidentView]:
    return list_incidents()

@app.get("/api/v1/incidents/{scenario_id}", response_model=IncidentView)
def incident_detail(scenario_id: str) -> IncidentView:
    incident = get_incident(scenario_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found in current process")
    return incident

@app.get("/api/v1/incidents/{scenario_id}/graph")
def incident_graph(scenario_id: str) -> dict:
    if get_incident(scenario_id) is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    try:
        return graph_for_scenario(scenario_id)
    except Exception as exc:
        # Never expose database errors, credentials or internal connection details.
        raise HTTPException(status_code=503, detail="Graph service unavailable") from exc
