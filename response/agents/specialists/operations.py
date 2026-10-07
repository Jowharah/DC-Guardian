"""Operations specialist for DC-GUARDIAN Phase 3.3."""

from __future__ import annotations

from response.agents.grounded_reasoning import grounded_reason
from response.agents.specialists.base import SpecialistAgent, SpecialistRequest


class OperationsSpecialist(SpecialistAgent):
    specialist_id = "operations"
    supported_domains = frozenset({"MAINTENANCE", "ENVIRONMENTAL"})

    def __init__(self, provider) -> None:
        self.provider = provider

    def assess(self, request: SpecialistRequest) -> dict:
        self.validate_request(request)

        specialist_task = (
            "You are the DC-GUARDIAN Operations specialist for maintenance and "
            "environmental evidence. Preserve the originating evidence semantics. "
            "A maintenance AT_RISK state is a model-estimated failure risk within "
            "its stated horizon; it is not a guaranteed failure and does not predict "
            "an exact failure date. Environmental abnormality such as HIGH_TEMPERATURE "
            "is an observed/derived operating-condition state; it does not by itself "
            "prove hardware damage or root cause. Shared server/rack/zone context and "
            "Phase 2 correlation establish operational relevance, not causation. "
            "Do not claim that temperature caused a drive failure, that a drive will "
            "certainly fail, or that correlated evidence proves root cause unless "
            "explicit causal evidence is supplied. Do not decide correlation, final "
            "severity, escalation, maintenance scheduling, or autonomous action. "
            + request.task
        )

        return grounded_reason(
            provider=self.provider,
            incident_evidence=request.incident_evidence,
            retrieved_evidence=request.retrieved_evidence,
            task=specialist_task,
        )

