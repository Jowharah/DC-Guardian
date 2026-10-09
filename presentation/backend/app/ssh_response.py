"""Grounded standalone SSH specialist Response using published detector evidence.

This is not a Decision result and does not infer compromise or correlation.
"""
from response.agents.providers.openai_provider import OpenAIResponsesProvider
from response.agents.specialists.cybersecurity import CybersecuritySpecialist
from response.agents.specialists.base import SpecialistRequest
from response.rag.knowledge_eligibility import evaluate_knowledge_eligibility
from response.rag.retrieve import retrieve_knowledge

def assess_standalone_ssh(event_id: str, assessment: dict, zone: str, server: str) -> dict:
    eligibility=evaluate_knowledge_eligibility(domains=["CYBERSECURITY"])
    if not eligibility["eligible"]:
        raise RuntimeError("No approved cybersecurity knowledge available")
    knowledge=retrieve_knowledge(
        "Approved SSH authentication anomaly investigation and access monitoring guidance",
        domains=["CYBERSECURITY"],top_k=3,ranking="controlled",abstain=False)
    if not knowledge:
        raise RuntimeError("No approved cybersecurity retrieval results")
    # Keep actual detector evidence; the operator's topology assignment is labeled.
    evidence={
        "event_id":event_id,"domains":["CYBERSECURITY"],
        "correlation_status":"NO_CORRELATION",
        "shared_scope":"OPERATOR_ASSIGNED_SERVER",
        "shared_entity":server,"zone_id":zone,
        "ssh_assessment":{
            "source_ip":assessment.get("source_ip"),
            "window_start":assessment.get("window_start"),
            "window_end":assessment.get("window_end"),
            "evidence_state":assessment.get("evidence_state"),
            "detector_votes":assessment.get("detector_votes"),
            "explicit_security_signal":assessment.get("explicit_security_signal"),
            "behavior":assessment.get("evidence",{}),
        },
        "confirmed_compromise":False,
        "identity_link_established":False,
        "causal_relationship_established":False,
        "root_cause_established":False,
    }
    response=CybersecuritySpecialist(OpenAIResponsesProvider()).assess(
        SpecialistRequest(
            incident_evidence=evidence,retrieved_evidence=knowledge,
            task="Assess this standalone SSH Evidence event only. Correlation is not established. "
                 "Do not infer attacker identity, confirmed compromise, Decision severity, or autonomous action.",
            domains=("CYBERSECURITY",),
        ))
    allowed=("assessment","grounding_status","supported_findings",
             "recommended_considerations","limitations","citations")
    return {"specialist_id":"cybersecurity",
            **{key:response[key] for key in allowed},
            "source":"GROUNDED_RESPONSE","decision_severity":None,
            "confirmed_compromise":False}
