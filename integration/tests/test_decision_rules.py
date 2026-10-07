"""Contract tests for deterministic DC-GUARDIAN Decision Rules v1."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from decision.rules import decide  # noqa: E402


def case(domains, *, auth=None, grounding="SUPPORTED", boundaries=None):
    return {
        "reasoning": {"domains": domains, "authorization_status": auth},
        "response": {
            "assessment": {"grounding_status": grounding},
            "boundary_claims": boundaries or {},
        },
    }


def main():
    physical = decide(case(
        ["PHYSICAL_SECURITY", "SAFETY"], auth="UNAUTHORIZED",
        boundaries={"identity_link_established": False},
    ))
    assert physical["severity"] == "MEDIUM"
    assert not physical["autonomous_action_allowed"]
    print("PASS: Unauthorized Physical/Safety evidence -> MEDIUM human review.")

    operations = decide(case(
        ["ENVIRONMENTAL", "MAINTENANCE"],
        boundaries={
            "causal_relationship_established": False,
            "root_cause_established": False,
        },
    ))
    assert operations["severity"] == "MEDIUM"
    print("PASS: Correlated operational risk -> MEDIUM human review.")

    multi = decide(case(
        ["CYBERSECURITY", "ENVIRONMENTAL", "MAINTENANCE"],
        boundaries={
            "confirmed_compromise": False,
            "causal_relationship_established": False,
            "root_cause_established": False,
        },
    ))
    assert multi["severity"] == "HIGH"
    assert multi["escalation_required"]
    assert not multi["protected_boundaries"]["confirmed_compromise"]
    print("PASS: Three-domain correlated risk -> HIGH review/escalation.")
    print("PASS: HIGH severity does not promote compromise or causation.")

    insufficient = decide(case(
        ["CYBERSECURITY"], grounding="INSUFFICIENT",
        boundaries={"confirmed_compromise": False},
    ))
    assert insufficient["incident_status"] == "EVIDENCE_REVIEW_REQUIRED"
    print("PASS: Insufficient grounding -> evidence review required.")

    print("=" * 60)
    print("DC-GUARDIAN DETERMINISTIC DECISION CONTRACT PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()

