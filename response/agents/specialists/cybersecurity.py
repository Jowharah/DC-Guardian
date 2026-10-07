"""Cybersecurity specialist for DC-GUARDIAN Phase 3.3."""

from __future__ import annotations

from response.agents.grounded_reasoning import grounded_reason
from response.agents.specialists.base import SpecialistAgent, SpecialistRequest


class CybersecuritySpecialist(SpecialistAgent):
    specialist_id = "cybersecurity"
    supported_domains = frozenset({"CYBERSECURITY"})

    def __init__(self, provider) -> None:
        self.provider = provider

    def assess(self, request: SpecialistRequest) -> dict:
        self.validate_request(request)

        specialist_task = (
            "You are the DC-GUARDIAN Cybersecurity specialist. Interpret only "
            "the supplied cybersecurity evidence together with retrieved approved "
            "knowledge. Preserve the originating SSH detector semantics. "
            "HIGH_CONFIDENCE_ANOMALY means two or more frozen detector components "
            "voted anomalous; it is not proof of a confirmed attack. "
            "ANOMALY_CANDIDATE is lower-confidence anomaly evidence and must not "
            "be called malicious activity without additional evidence. "
            "EXPLICIT_SECURITY_EVENT represents an explicit OpenSSH security "
            "signal but does not by itself prove compromise, attacker identity, "
            "successful access, persistence, or impact. Do not invent commands, "
            "accounts, assets, compromise, root cause, severity, escalation, or "
            "autonomous response. Do not decide whether events correlate. "
            + request.task
        )

        return grounded_reason(
            provider=self.provider,
            incident_evidence=request.incident_evidence,
            retrieved_evidence=request.retrieved_evidence,
            task=specialist_task,
        )

