"""Real Response runner for Environmental + Maintenance."""

from __future__ import annotations

from phase3.agents.providers.openai_provider import OpenAIResponsesProvider
from phase3.agents.routing.specialist_router import route_specialists
from phase3.agents.specialists.base import SpecialistRequest
from phase3.agents.specialists.operations import OperationsSpecialist
from phase3.rag.knowledge_eligibility import evaluate_knowledge_eligibility
from phase3.rag.retrieve import retrieve_knowledge


QUERY = (
    "What approved data-center operations and maintenance guidance is relevant "
    "when a drive has elevated seven-day failure risk and a zone-level "
    "environmental sensor reports high temperature in related infrastructure?"
)


def run_real_environmental_maintenance_response(reasoning_result: dict) -> dict:
    domains = reasoning_result["domains"]
    routed = route_specialists(domains)
    if routed != ["operations"]:
        raise RuntimeError(f"Unexpected specialist routing: {routed}")

    for domain in domains:
        eligibility = evaluate_knowledge_eligibility(domains=[domain])
        if not eligibility["eligible"]:
            raise RuntimeError(f"No approved active knowledge for {domain}")

    evidence = retrieve_knowledge(
        QUERY, domains=domains, top_k=3, ranking="controlled", abstain=False
    )
    if not evidence:
        raise RuntimeError("No approved Operations evidence retrieved.")

    specialist = OperationsSpecialist(OpenAIResponsesProvider())
    assessment = specialist.assess(
        SpecialistRequest(
            incident_evidence={
                "scenario_id": reasoning_result["scenario_id"],
                "domains": domains,
                "correlation": reasoning_result["correlation"],
                "shared_scope": reasoning_result["shared_scope"],
                "shared_entity": reasoning_result["shared_entity"],
                "causal_relationship_established": False,
                "root_cause_established": False,
                "evidence_events": reasoning_result["evidence_events"],
            },
            retrieved_evidence=evidence,
            task=(
                "Assess the validated Environmental and Maintenance correlation. "
                "Preserve the Reasoning layer's strongest truthful scope and do "
                "not infer causation or root cause."
            ),
            domains=tuple(domains),
        )
    )
    return {
        "specialists": routed,
        "retrieved_evidence": evidence,
        "assessment": assessment,
        "boundary_claims": {
            "causal_relationship_established": False,
            "root_cause_established": False,
        },
    }
