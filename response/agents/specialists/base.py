"""Shared contract for DC-GUARDIAN Specialist Agents specialist agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class SpecialistRequest:
    incident_evidence: dict
    retrieved_evidence: list[dict]
    task: str
    domains: tuple[str, ...]


class SpecialistAgent(ABC):
    specialist_id: str
    supported_domains: frozenset[str]

    def validate_request(self, request: SpecialistRequest) -> None:
        requested = set(request.domains)
        if not requested:
            raise ValueError("Specialist request must include at least one domain.")
        unsupported = requested - self.supported_domains
        if unsupported:
            raise ValueError(
                f"{self.specialist_id} does not support domains: "
                f"{sorted(unsupported)}"
            )

    @abstractmethod
    def assess(self, request: SpecialistRequest) -> dict:
        """Return the shared grounded-assessment contract."""
        raise NotImplementedError
