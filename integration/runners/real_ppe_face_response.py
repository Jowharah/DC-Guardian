"""Real Response runner for the PPE + Face vertical slice."""

from __future__ import annotations

from phase3.agents.providers.openai_provider import OpenAIResponsesProvider
from phase3.agents.routing.specialist_router import route_specialists
from phase3.agents.specialists.base import SpecialistRequest
from phase3.agents.specialists.physical_safety import PhysicalSafetySpecialist
from phase3.rag.knowledge_eligibility import evaluate_knowledge_eligibility
from phase3.rag.retrieve import retrieve_knowledge


QUERY = (
    "What approved physical-access and PPE guidance is relevant when "
    "unauthorized recognized Face evidence and PPE non-compliance evidence "
    "are deterministically correlated in the same data-center zone?"
)


def run_real_ppe_face_response(reasoning_result: dict) -> dict:
    domains = reasoning_result["domains"]
    routed = route_specialists(domains)
    if routed != ["physical_safety"]:
        raise RuntimeError(f"Unexpected specialist routing: {routed}")

    for domain in domains:
        eligibility = evaluate_knowledge_eligibility(domains=[domain])
        if not eligibility["eligible"]:
            raise RuntimeError(
                f"No approved active knowledge for required domain: {domain}"
            )

    evidence = retrieve_knowledge(
        QUERY,
        domains=domains,
        top_k=3,
        ranking="controlled",
        abstain=False,
    )
    if not evidence:
        raise RuntimeError("No approved Physical/Safety evidence retrieved.")

    correlation = reasoning_result["correlation"]
    incident = {
        "scenario_id": reasoning_result["scenario_id"],
        "correlation_type": correlation["correlation_type"],
        "domains": domains,
        "shared_scope": reasoning_result["shared_scope"],
        "shared_entity": reasoning_result["shared_entity"],
        "authorization_status": reasoning_result["authorization_status"],
        "identity_link_established": reasoning_result[
            "identity_link_established"
        ],
        "correlated_events": correlation["events"],
        "source": "REAL_REASONING_VERTICAL_SLICE",
    }

    specialist = PhysicalSafetySpecialist(OpenAIResponsesProvider())
    assessment = specialist.assess(
        SpecialistRequest(
            incident_evidence=incident,
            retrieved_evidence=evidence,
            task=(
                "Assess the validated PPE and Face correlation. Preserve the "
                "Reasoning layer's ZONE scope and its explicit absence of a "
                "cross-model identity link."
            ),
            domains=tuple(domains),
        )
    )

    if reasoning_result["identity_link_established"]:
        raise RuntimeError("Unexpected upstream identity link.")
    return {
        "specialists": routed,
        "retrieved_evidence": evidence,
        "assessment": assessment,
        "boundary_claims": {
            "identity_link_established": False,
        },
    }
