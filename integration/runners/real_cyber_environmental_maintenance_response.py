"""Multi-specialist Response runner for Cyber + Environmental + Maintenance."""

from __future__ import annotations

from response.agents.providers.openai_provider import OpenAIResponsesProvider
from response.agents.providers.openai_synthesis_provider import OpenAICrossDomainSynthesisProvider
from response.agents.schemas.specialist_finding import (
    EvidenceBoundaryClaims,
    to_specialist_finding,
)
from response.agents.specialists.base import SpecialistRequest
from response.agents.specialists.cybersecurity import CybersecuritySpecialist
from response.agents.specialists.operations import OperationsSpecialist
from response.agents.routing.specialist_router import route_specialists
from response.agents.synthesis.cross_domain import cross_domain_synthesize
from response.rag.knowledge_eligibility import evaluate_knowledge_eligibility
from response.rag.retrieve import retrieve_knowledge


def _retrieve(query, domains):
    for domain in domains:
        if not evaluate_knowledge_eligibility(domains=[domain])["eligible"]:
            raise RuntimeError(f"No approved active knowledge for {domain}")
    return retrieve_knowledge(
        query, domains=domains, top_k=3, ranking="controlled", abstain=False
    )


def run_real_cyber_environmental_maintenance_response(reasoning_result: dict) -> dict:
    routed=route_specialists(reasoning_result["domains"])
    if routed != ["cybersecurity","operations"]:
        raise RuntimeError(f"Unexpected specialist routing: {routed}")

    cyber_evidence=_retrieve(
        "What approved incident-response guidance is relevant to a high-confidence "
        "SSH anomaly with repeated failed authentication behavior?",
        ["CYBERSECURITY"],
    )
    ops_evidence=_retrieve(
        "What approved operations guidance is relevant to drive failure risk and "
        "high temperature in related data-center infrastructure?",
        ["MAINTENANCE","ENVIRONMENTAL"],
    )

    common={
        "scenario_id":reasoning_result["scenario_id"],
        "correlation":reasoning_result["correlation"],
        "shared_scope":reasoning_result["shared_scope"],
        "shared_entity":reasoning_result["shared_entity"],
        "evidence_events":reasoning_result["evidence_events"],
    }

    cyber=CybersecuritySpecialist(OpenAIResponsesProvider()).assess(
        SpecialistRequest(
            incident_evidence={**common,"confirmed_compromise":False},
            retrieved_evidence=cyber_evidence,
            task="Assess the validated cybersecurity evidence without promoting anomaly to compromise.",
            domains=("CYBERSECURITY",),
        )
    )
    ops=OperationsSpecialist(OpenAIResponsesProvider()).assess(
        SpecialistRequest(
            incident_evidence={**common,"causal_relationship_established":False,
                               "root_cause_established":False},
            retrieved_evidence=ops_evidence,
            task="Assess the validated operational evidence without inferring causation or root cause.",
            domains=("MAINTENANCE","ENVIRONMENTAL"),
        )
    )

    findings=[
        to_specialist_finding(
            specialist_id="cybersecurity",domains=("CYBERSECURITY",),
            assessment=cyber,
            boundary_claims=EvidenceBoundaryClaims(confirmed_compromise=False),
        ),
        to_specialist_finding(
            specialist_id="operations",domains=("MAINTENANCE","ENVIRONMENTAL"),
            assessment=ops,
            boundary_claims=EvidenceBoundaryClaims(
                causal_relationship_established=False,root_cause_established=False),
        ),
    ]
    synthesis=cross_domain_synthesize(
        provider=OpenAICrossDomainSynthesisProvider(),
        findings=findings,
        task=(
            "Synthesize the validated Cybersecurity and Operations findings for "
            "the Phase-2-established shared incident context. Preserve all evidence "
            "boundaries and do not assign final severity or escalation."
        ),
    )
    return {
        "specialists":routed,
        "specialist_assessments":{"cybersecurity":cyber,"operations":ops},
        "retrieved_evidence":{"cybersecurity":cyber_evidence,"operations":ops_evidence},
        "synthesis":synthesis,
        "assessment":synthesis,
        "boundary_claims":synthesis["boundary_claims"],
    }

