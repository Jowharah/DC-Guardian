"""Contracts for structured specialist findings and synthesis boundaries."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from response.agents.schemas.specialist_finding import (  # noqa: E402
    EvidenceBoundaryClaims,
    SpecialistFinding,
)
from response.agents.synthesis.boundaries import (  # noqa: E402
    synthesis_boundary_summary,
    validate_synthesis_inputs,
)


def finding(specialist_id, domains, **claims):
    return SpecialistFinding(
        specialist_id=specialist_id,
        domains=tuple(domains),
        assessment="Validated specialist assessment.",
        supported_findings=("Supported finding.",),
        recommended_considerations=("Review evidence.",),
        grounding_status="SUPPORTED",
        citations=(("chunk-1", "doc-1"),),
        limitations=("Known limitation.",),
        boundary_claims=EvidenceBoundaryClaims(**claims),
    )


def main():
    physical = finding(
        "physical_safety",
        ["PHYSICAL_SECURITY", "SAFETY"],
        identity_link_established=False,
    )
    cyber = finding(
        "cybersecurity",
        ["CYBERSECURITY"],
        confirmed_compromise=False,
    )
    operations = finding(
        "operations",
        ["MAINTENANCE", "ENVIRONMENTAL"],
        causal_relationship_established=False,
        root_cause_established=False,
    )

    summary = synthesis_boundary_summary([physical, cyber, operations])
    if any(summary["established_claims"].values()):
        raise AssertionError(
            "Synthesis incorrectly promoted an unestablished boundary claim."
        )
    print("PASS: Unestablished specialist claims remain false for synthesis.")

    explicit = finding(
        "cybersecurity",
        ["CYBERSECURITY"],
        confirmed_compromise=True,
    )
    summary = synthesis_boundary_summary([physical, explicit])
    if not summary["established_claims"]["confirmed_compromise"]:
        raise AssertionError("Explicit established claim was lost.")
    print("PASS: Explicit upstream established claim is preserved.")

    try:
        validate_synthesis_inputs([physical])
    except ValueError:
        print("PASS: Single-specialist synthesis rejected.")
    else:
        raise AssertionError("Single-specialist synthesis was accepted.")

    print("=" * 60)
    print("DC-GUARDIAN CROSS-DOMAIN SYNTHESIS INPUT CONTRACT PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()

