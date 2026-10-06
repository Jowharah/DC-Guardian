"""Physical/Safety specialist for Phase 3.3."""

from __future__ import annotations

from phase3.agents.grounded_reasoning import grounded_reason
from phase3.agents.specialists.base import SpecialistAgent, SpecialistRequest


class PhysicalSafetySpecialist(SpecialistAgent):
    specialist_id = "physical_safety"
    supported_domains = frozenset({"PHYSICAL_SECURITY", "SAFETY"})

    def __init__(self, provider) -> None:
        self.provider = provider

    def assess(self, request: SpecialistRequest) -> dict:
        self.validate_request(request)

        specialist_task = (
            "You are the DC-GUARDIAN Physical/Safety specialist. "
            "Interpret only the supplied physical-security and safety evidence "
            "together with retrieved approved knowledge. Preserve the distinction "
            "between face identity evidence, graph-derived authorization, and PPE "
            "detection evidence. PPE person_index evidence is anonymous and must "
            "not be claimed to identify the recognized Face subject unless explicit "
            "cross-model identity evidence is supplied. Do not decide correlation, "
            "final severity, escalation, or autonomous action. "
            + request.task
        )

        return grounded_reason(
            provider=self.provider,
            incident_evidence=request.incident_evidence,
            retrieved_evidence=request.retrieved_evidence,
            task=specialist_task,
        )
