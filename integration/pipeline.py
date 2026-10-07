"""Integrated DC-GUARDIAN Evidence -> Reasoning -> Response pipeline.

Initial v1 wires the controlled PPE + Face scenario through explicit layer
interfaces. The Evidence and Reasoning hooks are injectable so the contract can
be tested without neural model loading or Neo4j; production adapters can replace
those hooks without changing the pipeline result schema.
"""

from __future__ import annotations

from collections.abc import Callable

from integration.schemas.pipeline_result import PipelineResult
from response.agents.routing.specialist_router import route_specialists


EvidenceRunner = Callable[[dict], list[dict]]
ReasoningRunner = Callable[[list[dict], str], dict]
ResponseRunner = Callable[[dict], dict]


def run_dc_guardian_scenario(
    *,
    scenario: dict,
    evidence_runner: EvidenceRunner,
    reasoning_runner: ReasoningRunner,
    response_runner: ResponseRunner,
) -> PipelineResult:
    scenario_id = scenario["scenario_id"]

    evidence_events = evidence_runner(scenario)
    if not evidence_events:
        raise ValueError("EVIDENCE produced no structured events.")

    reasoning_result = reasoning_runner(evidence_events, scenario_id)
    domains = tuple(reasoning_result.get("domains", ()))
    if not domains:
        raise ValueError("REASONING produced no domains.")

    routed = route_specialists(domains)
    reasoning_result = dict(reasoning_result)
    reasoning_result["routed_specialists"] = routed

    response_input = {
        "scenario_id": scenario_id,
        "evidence_events": evidence_events,
        "reasoning": reasoning_result,
    }
    response_result = response_runner(response_input)

    return PipelineResult(
        scenario_id=scenario_id,
        evidence={
            "layer": "EVIDENCE",
            "events": evidence_events,
        },
        reasoning={
            "layer": "REASONING",
            **reasoning_result,
        },
        response={
            "layer": "RESPONSE",
            **response_result,
        },
        decision={
            "status": "PENDING_DETERMINISTIC_DECISION_RULES",
        },
        provenance={
            "scenario_type": scenario.get("scenario_type"),
            "identity_boundary": scenario.get("identity_boundary"),
        },
    )

