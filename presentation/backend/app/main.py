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
from presentation.backend.app.graph_integrity import check_graph_integrity
from presentation.backend.app.graph_audit import audit_graph_access
from presentation.backend.app.authentication import current_principal, authorize
from presentation.backend.app.authorization import Principal, Permission
from presentation.backend.app.evidence_details import read_evidence, DOMAIN_PERMISSIONS
from presentation.backend.app.ppe_image_validation import router as ppe_image_router
from presentation.backend.app.face_image_validation import router as face_image_router
from presentation.backend.app.employee_access import router as employee_access_router
from presentation.backend.app.standalone_events import router as standalone_events_router
from presentation.backend.app.ssh_log_validation import router as ssh_log_router
from presentation.backend.app.ssh_publication import router as ssh_publication_router
from presentation.backend.app.maintenance_workflow import router as maintenance_router
from presentation.backend.app.environment_workflow import router as environment_router
from presentation.backend.app.operational_correlations import router as operational_correlation_router
from presentation.backend.app.operational_decision import router as operational_decision_router
from presentation.backend.app.standalone_graph import router as standalone_graph_router
from presentation.backend.app.image_metadata_api import router as image_metadata_router
from presentation.backend.app.physical_image_correlations import router as physical_image_router

app = FastAPI(
    title="DC-GUARDIAN Presentation API", version="0.1.0",
    docs_url=None, redoc_url=None,
)

app.include_router(ppe_image_router)
app.include_router(face_image_router)
app.include_router(employee_access_router)
app.include_router(standalone_events_router)
app.include_router(ssh_log_router)
app.include_router(ssh_publication_router)
app.include_router(maintenance_router)
app.include_router(environment_router)
app.include_router(operational_correlation_router)
app.include_router(operational_decision_router)
app.include_router(standalone_graph_router)
app.include_router(image_metadata_router)
app.include_router(physical_image_router)

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

@app.get("/api/v1/incidents/{scenario_id}/graph-integrity")
def incident_graph_integrity(scenario_id: str, principal: Principal = Depends(current_principal)) -> dict:
    incident = get_incident(scenario_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    authorize(principal, Permission.GRAPH_READ, incident.shared_entity)
    try:
        return check_graph_integrity(scenario_id, incident.evidence_event_ids)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Graph integrity service unavailable") from exc

@app.get("/api/v1/incidents/{scenario_id}/evidence/{event_id}")
def incident_evidence_detail(scenario_id: str, event_id: str, principal: Principal = Depends(current_principal)) -> dict:
    incident = get_incident(scenario_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    authorize(principal, Permission.INCIDENT_READ, incident.shared_entity)
    matched = next((event for event in incident.evidence_events if event.event_id == event_id), None)
    if matched is None:
        raise HTTPException(status_code=404, detail="Evidence event not found in incident")
    permission = DOMAIN_PERMISSIONS.get(matched.domain)
    if permission is None:
        raise HTTPException(status_code=403, detail="Unsupported Evidence domain")
    authorize(principal, permission, incident.shared_entity)
    detail = read_evidence(scenario_id, event_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Detailed Evidence unavailable for this snapshot; regenerate controlled scenario")
    return detail
