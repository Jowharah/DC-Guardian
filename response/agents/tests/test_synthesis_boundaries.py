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


import pytest  # noqa: E402

PHYSICAL = finding("physical_safety", ["PHYSICAL_SECURITY", "SAFETY"], identity_link_established=False)
CYBER = finding("cybersecurity", ["CYBERSECURITY"], confirmed_compromise=False)
OPERATIONS = finding("operations", ["MAINTENANCE", "ENVIRONMENTAL"],
                     causal_relationship_established=False, root_cause_established=False)


def test_unestablished_claims_stay_false():
    summary = synthesis_boundary_summary([PHYSICAL, CYBER, OPERATIONS])
    assert not any(summary["established_claims"].values()), "Synthesis promoted an unestablished boundary claim."


def test_explicit_upstream_claim_is_preserved():
    explicit = finding("cybersecurity", ["CYBERSECURITY"], confirmed_compromise=True)
    assert synthesis_boundary_summary([PHYSICAL, explicit])["established_claims"]["confirmed_compromise"]


def test_single_specialist_synthesis_is_rejected():
    with pytest.raises(ValueError):
        validate_synthesis_inputs([PHYSICAL])


def main():
    test_unestablished_claims_stay_false()
    print("PASS: Unestablished specialist claims remain false for synthesis.")
    test_explicit_upstream_claim_is_preserved()
    print("PASS: Explicit upstream established claim is preserved.")
    test_single_specialist_synthesis_is_rejected()
    print("PASS: Single-specialist synthesis rejected.")
    print("=" * 60)
    print("DC-GUARDIAN CROSS-DOMAIN SYNTHESIS INPUT CONTRACT PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
