"""Allowlisted scenario execution and browser-safe projection."""
from integration.scenario_registry import SCENARIOS
from integration.service import run_integrated_scenario
from presentation.backend.app.schemas import IncidentView, ScenarioInfo, EvidenceEventView, SpecialistAssessmentView, SynthesisView

def list_scenarios() -> list[ScenarioInfo]:
    return [ScenarioInfo(name=name, description=SCENARIOS[name]["description"]) for name in sorted(SCENARIOS)]

def execute_scenario(name: str, *, scenario_id: str | None = None) -> IncidentView:
    if name not in SCENARIOS:
        raise ValueError("Unknown controlled scenario")
    result = run_integrated_scenario(name, scenario_id=scenario_id)
    if result.decision.get("autonomous_action_allowed") is not False:
        raise ValueError("Unsafe decision contract: autonomous action not explicitly disabled")
    events = result.evidence.get("events", [])
    event_ids = [e["event_id"] for e in events if isinstance(e, dict) and isinstance(e.get("event_id"), str)]
    safe_events = []
    for event in events:
        if not isinstance(event, dict):
            continue
        try:
            safe_events.append(EvidenceEventView(
                event_id=event["event_id"],
                domain=event["domain"],
                event_type=event["event_type"],
                timestamp=event["timestamp"],
                state=event["assessment"]["state"],
                component=event["source"]["component"],
                zone_id=event.get("location", {}).get("zone_id"),
                server_id=event.get("entities", {}).get("server_id"),
                sensor_id=event.get("entities", {}).get("sensor_id"),
                camera_id=event.get("entities", {}).get("camera_id"),
                source_type=event.get("provenance", {}).get("source_type"),
            ))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Invalid pipeline evidence event contract") from exc
    response = result.response
    routed = response.get("specialists", [])
    raw_assessments = response.get("specialist_assessments")
    if raw_assessments is None:
        raw_assessments = {routed[0]: response["assessment"]} if len(routed) == 1 else {}
    specialist_views = [
        SpecialistAssessmentView(specialist_id=key, **{
            field: assessment[field] for field in (
                "assessment", "grounding_status", "supported_findings",
                "recommended_considerations", "limitations", "citations"
            )
        })
        for key, assessment in raw_assessments.items()
    ]
    synthesis = None
    if "synthesis" in response:
        synthesis = SynthesisView(**{
            field: response["synthesis"][field] for field in (
                "assessment", "grounding_status", "contributing_specialists",
                "supported_cross_domain_findings", "recommended_considerations",
                "limitations", "citations"
            )
        })
    return IncidentView(
        scenario_id=result.scenario_id,
        scenario_name=name,
        domains=result.reasoning.get("domains", []),
        shared_scope=result.reasoning.get("shared_scope"),
        shared_entity=result.reasoning.get("shared_entity"),
        evidence_event_ids=event_ids,
        evidence_events=safe_events,
        specialist_assessments=specialist_views,
        synthesis=synthesis,
        event_time=min((item.timestamp for item in safe_events), default=None),
        decision=result.decision,
    )
