"""Deterministic pre-validation for cross-domain synthesis inputs."""

from __future__ import annotations

from response.agents.schemas.specialist_finding import SpecialistFinding


def validate_synthesis_inputs(findings: list[SpecialistFinding]) -> None:
    if len(findings) < 2:
        raise ValueError("Cross-domain synthesis requires at least two specialists.")

    ids = [item.specialist_id for item in findings]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate specialist findings are not allowed.")

    domains = set()
    for item in findings:
        domains.update(item.domains)
        if item.grounding_status not in {
            "SUPPORTED",
            "PARTIALLY_SUPPORTED",
            "INSUFFICIENT",
        }:
            raise ValueError("Invalid specialist grounding status.")

    if len(domains) < 2:
        raise ValueError("Cross-domain synthesis requires multiple domains.")


def synthesis_boundary_summary(
    findings: list[SpecialistFinding],
) -> dict:
    validate_synthesis_inputs(findings)
    return {
        "specialists": [item.specialist_id for item in findings],
        "domains": sorted({d for item in findings for d in item.domains}),
        "established_claims": {
            "identity_link_established": any(
                x.boundary_claims.identity_link_established for x in findings
            ),
            "confirmed_compromise": any(
                x.boundary_claims.confirmed_compromise for x in findings
            ),
            "causal_relationship_established": any(
                x.boundary_claims.causal_relationship_established
                for x in findings
            ),
            "root_cause_established": any(
                x.boundary_claims.root_cause_established for x in findings
            ),
        },
        "rule": (
            "Synthesis may preserve established claims but must not promote any "
            "false boundary claim to true without explicit upstream evidence."
        ),
    }

