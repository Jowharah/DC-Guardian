"""Cross-domain synthesis orchestration and deterministic validation."""

from __future__ import annotations

from response.agents.schemas.cross_domain_synthesis import (
    SYNTHESIS_REQUIRED_KEYS,
)
from response.agents.schemas.specialist_finding import SpecialistFinding
from response.agents.synthesis.boundaries import synthesis_boundary_summary


def _allowed_citations(findings: list[SpecialistFinding]) -> set[tuple[str, str]]:
    return {
        citation
        for finding in findings
        for citation in finding.citations
    }


def validate_cross_domain_synthesis(
    result: dict,
    findings: list[SpecialistFinding],
) -> None:
    missing = SYNTHESIS_REQUIRED_KEYS - result.keys()
    extra = result.keys() - SYNTHESIS_REQUIRED_KEYS
    if missing:
        raise ValueError(f"Missing synthesis keys: {sorted(missing)}")
    if extra:
        raise ValueError(f"Unexpected synthesis keys: {sorted(extra)}")

    summary = synthesis_boundary_summary(findings)
    expected_specialists = set(summary["specialists"])
    actual_specialists = set(result["contributing_specialists"])
    if actual_specialists != expected_specialists:
        raise ValueError(
            "Synthesis contributing_specialists must exactly match inputs."
        )

    if result["grounding_status"] not in {
        "SUPPORTED",
        "PARTIALLY_SUPPORTED",
        "INSUFFICIENT",
    }:
        raise ValueError("Invalid synthesis grounding_status.")

    allowed = _allowed_citations(findings)
    for citation in result["citations"]:
        pair = (citation["chunk_id"], citation["document_id"])
        if pair not in allowed:
            raise ValueError(
                f"Synthesis cited evidence not supplied by specialists: {pair}"
            )

    upstream = summary["established_claims"]
    output = result["boundary_claims"]
    for key, value in output.items():
        if value and not upstream[key]:
            raise ValueError(
                f"Synthesis promoted unestablished boundary claim: {key}"
            )

    if result["grounding_status"] in {
        "SUPPORTED",
        "PARTIALLY_SUPPORTED",
    } and not result["citations"]:
        raise ValueError(
            "Supported synthesis must preserve at least one specialist citation."
        )


def cross_domain_synthesize(*, provider, findings: list[SpecialistFinding], task: str) -> dict:
    boundary_summary = synthesis_boundary_summary(findings)
    payload = {
        "task": task,
        "specialist_findings": [
            {
                "specialist_id": x.specialist_id,
                "domains": list(x.domains),
                "assessment": x.assessment,
                "supported_findings": list(x.supported_findings),
                "recommended_considerations": list(x.recommended_considerations),
                "grounding_status": x.grounding_status,
                "citations": [
                    {"chunk_id": c[0], "document_id": c[1]}
                    for c in x.citations
                ],
                "limitations": list(x.limitations),
                "boundary_claims": vars(x.boundary_claims),
            }
            for x in findings
        ],
        "boundary_summary": boundary_summary,
    }
    result = provider.synthesize(payload)
    validate_cross_domain_synthesis(result, findings)
    return result

