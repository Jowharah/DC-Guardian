"""Reusable application service for DC-GUARDIAN integrated scenarios."""

from __future__ import annotations

from integration.scenario_registry import get_scenario
from integration.schemas.pipeline_result import PipelineResult


def run_integrated_scenario(
    scenario_name: str,
    *,
    scenario_id: str | None = None,
) -> PipelineResult:
    config = get_scenario(scenario_name)
    resolved_id = scenario_id or f"DCG-{scenario_name.upper()}-001"

    reasoning = config["reasoning_runner"](scenario_id=resolved_id)
    response = config["response_runner"](reasoning)

    return PipelineResult(
        scenario_id=resolved_id,
        evidence={
            "layer": "EVIDENCE",
            "events": reasoning.get("evidence_events", []),
        },
        reasoning={
            "layer": "REASONING",
            "domains": reasoning["domains"],
            "correlation": reasoning["correlation"],
            "shared_scope": reasoning["shared_scope"],
            "shared_entity": reasoning["shared_entity"],
            "authorization_status": reasoning.get("authorization_status"),
            "identity_link_established": reasoning.get(
                "identity_link_established", False
            ),
        },
        response={
            "layer": "RESPONSE",
            **response,
        },
        decision={
            "status": "PENDING_DETERMINISTIC_DECISION_RULES",
        },
        provenance={
            "scenario_name": scenario_name,
            "scenario_type": "CONTROLLED_SYNTHETIC_SCENARIO",
            "pipeline": "INTEGRATED_APPLICATION_SERVICE",
        },
    )
