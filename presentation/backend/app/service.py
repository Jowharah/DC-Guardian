"""Allowlisted scenario execution and browser-safe projection."""
from integration.scenario_registry import SCENARIOS
from integration.service import run_integrated_scenario
from presentation.backend.app.schemas import IncidentView, ScenarioInfo

def list_scenarios() -> list[ScenarioInfo]:
    return [ScenarioInfo(name=name, description=SCENARIOS[name]["description"]) for name in sorted(SCENARIOS)]

def execute_scenario(name: str) -> IncidentView:
    if name not in SCENARIOS:
        raise ValueError("Unknown controlled scenario")
    result = run_integrated_scenario(name)
    if result.decision.get("autonomous_action_allowed") is not False:
        raise ValueError("Unsafe decision contract: autonomous action not explicitly disabled")
    events = result.evidence.get("events", [])
    event_ids = [e["event_id"] for e in events if isinstance(e, dict) and isinstance(e.get("event_id"), str)]
    return IncidentView(
        scenario_id=result.scenario_id,
        scenario_name=name,
        domains=result.reasoning.get("domains", []),
        shared_scope=result.reasoning.get("shared_scope"),
        shared_entity=result.reasoning.get("shared_entity"),
        evidence_event_ids=event_ids,
        decision=result.decision,
    )
