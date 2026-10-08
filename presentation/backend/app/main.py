"""DC-GUARDIAN Presentation API — controlled prototype, no public deployment."""
from fastapi import FastAPI, HTTPException
from presentation.backend.app.custom_scenarios import CustomScenarioInput, CustomScenarioResult, topology_options, assess_custom_environment
from presentation.backend.app.schemas import IncidentView, ScenarioInfo
from presentation.backend.app.service import execute_scenario, list_scenarios

app = FastAPI(title="DC-GUARDIAN Presentation API", version="0.1.0", docs_url=None, redoc_url=None)

@app.get("/api/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok", "mode": "CONTROLLED_PROTOTYPE"}

@app.get("/api/v1/scenarios", response_model=list[ScenarioInfo])
def scenarios() -> list[ScenarioInfo]:
    return list_scenarios()

@app.post("/api/v1/scenarios/{name}/run", response_model=IncidentView)
def run_scenario(name: str) -> IncidentView:
    # Prototype only: no production deployment until authentication/RBAC and audit are implemented.
    try:
        return execute_scenario(name)
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
