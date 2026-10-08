"""DC-GUARDIAN Presentation API — local controlled prototype only."""
from fastapi import FastAPI, HTTPException, Query, Depends
from presentation.backend.app.custom_scenarios import (
    CustomScenarioInput, CustomScenarioResult, topology_options,
    assess_custom_environment,
)
from presentation.backend.app.schemas import IncidentView, ScenarioInfo
from presentation.backend.app.incident_store import remember, list_incidents, get_incident
from presentation.backend.app.service import execute_scenario, list_scenarios
from presentation.backend.app.graph_view import graph_for_scenario
from presentation.backend.app.graph_audit import audit_graph_access
from presentation.backend.app.authentication import current_principal, authorize
from presentation.backend.app.authorization import Principal, Permission

app = FastAPI(
    title="DC-GUARDIAN Presentation API", version="0.1.0",
    docs_url=None, redoc_url=None,
)

@app.get("/api/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok", "mode": "CONTROLLED_PROTOTYPE"}

@app.get("/api/v1/scenarios", response_model=list[ScenarioInfo])
def scenarios(principal: Principal = Depends(current_principal)) -> list[ScenarioInfo]:
    return list_scenarios()

@app.post("/api/v1/scenarios/{name}/run", response_model=IncidentView)
def run_scenario(
    name: str,
    run_id: str | None = Query(default=None, pattern=r"^DCG-[A-Z0-9_-]{1,90}$", max_length=94),
    principal: Principal = Depends(current_principal),
) -> IncidentView:
    authorize(principal, Permission.SCENARIO_EXECUTE)
    try:
        incident = execute_scenario(name, scenario_id=run_id) if run_id else execute_scenario(name)
        return remember(incident)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

@app.get("/api/v1/topology/options")
def get_topology_options(principal: Principal = Depends(current_principal)) -> list[dict]:
    return topology_options()

@app.post("/api/v1/custom-scenarios/environment", response_model=CustomScenarioResult)
def custom_environment(payload: CustomScenarioInput, principal: Principal = Depends(current_principal)) -> CustomScenarioResult:
    authorize(principal, Permission.SCENARIO_EXECUTE, payload.zone_id)
    try:
        return assess_custom_environment(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

@app.get("/api/v1/incidents", response_model=list[IncidentView])
def incidents(principal: Principal = Depends(current_principal)) -> list[IncidentView]:
    return [item for item in list_incidents() if item.shared_entity in principal.zones]

@app.get("/api/v1/incidents/{scenario_id}", response_model=IncidentView)
def incident_detail(scenario_id: str, principal: Principal = Depends(current_principal)) -> IncidentView:
    incident = get_incident(scenario_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found in current process")
    authorize(principal, Permission.INCIDENT_READ, incident.shared_entity)
    return incident

@app.get("/api/v1/incidents/{scenario_id}/graph")
def incident_graph(scenario_id: str, principal: Principal = Depends(current_principal)) -> dict:
    incident = get_incident(scenario_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    authorize(principal, Permission.GRAPH_READ, incident.shared_entity)
    try:
        graph = graph_for_scenario(scenario_id, principal=principal, zone=incident.shared_entity)
        audit_graph_access(principal.subject, scenario_id, incident.shared_entity, graph)
        return graph
    except Exception as exc:
        # Never expose database errors, credentials or internal connection details.
        raise HTTPException(status_code=503, detail="Graph service unavailable") from exc

@app.get("/api/v1/auth/me")
def auth_me(principal: Principal = Depends(current_principal)) -> dict:
    return {"username": principal.subject, "roles": sorted(principal.roles), "zones": sorted(principal.zones)}
