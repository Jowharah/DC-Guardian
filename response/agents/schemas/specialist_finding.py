"""Structured specialist findings for safe cross-domain synthesis."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

GroundingStatus = Literal["SUPPORTED", "PARTIALLY_SUPPORTED", "INSUFFICIENT"]


@dataclass(frozen=True)
class EvidenceBoundaryClaims:
    identity_link_established: bool = False
    confirmed_compromise: bool = False
    causal_relationship_established: bool = False
    root_cause_established: bool = False


@dataclass(frozen=True)
class SpecialistFinding:
    specialist_id: str
    domains: tuple[str, ...]
    assessment: str
    supported_findings: tuple[str, ...]
    recommended_considerations: tuple[str, ...]
    grounding_status: GroundingStatus
    citations: tuple[tuple[str, str], ...]
    limitations: tuple[str, ...]
    boundary_claims: EvidenceBoundaryClaims = field(
        default_factory=EvidenceBoundaryClaims
    )


def to_specialist_finding(
    *,
    specialist_id: str,
    domains: tuple[str, ...],
    assessment: dict,
    boundary_claims: EvidenceBoundaryClaims | None = None,
) -> SpecialistFinding:
    return SpecialistFinding(
        specialist_id=specialist_id,
        domains=domains,
        assessment=assessment["assessment"],
        supported_findings=tuple(assessment["supported_findings"]),
        recommended_considerations=tuple(
            assessment["recommended_considerations"]
        ),
        grounding_status=assessment["grounding_status"],
        citations=tuple(
            (item["chunk_id"], item["document_id"])
            for item in assessment["citations"]
        ),
        limitations=tuple(assessment["limitations"]),
        boundary_claims=boundary_claims or EvidenceBoundaryClaims(),
    )
