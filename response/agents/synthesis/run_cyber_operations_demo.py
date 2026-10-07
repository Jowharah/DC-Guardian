"""Live Cybersecurity + Operations cross-domain synthesis demo."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from response.agents.providers.openai_synthesis_provider import (  # noqa: E402
    OpenAICrossDomainSynthesisProvider,
)
from response.agents.schemas.specialist_finding import (  # noqa: E402
    EvidenceBoundaryClaims,
    SpecialistFinding,
)
from response.agents.synthesis.cross_domain import cross_domain_synthesize  # noqa: E402


CYBER = SpecialistFinding(
    specialist_id="cybersecurity",
    domains=("CYBERSECURITY",),
    assessment=(
        "SSH evidence is a HIGH_CONFIDENCE_ANOMALY requiring investigation, "
        "not proof of confirmed attack or host compromise."
    ),
    supported_findings=(
        "Two frozen SSH detector components voted anomalous.",
        "Repeated authentication failures and invalid-user activity were observed.",
    ),
    recommended_considerations=(
        "Review authentication evidence and determine whether successful access occurred.",
    ),
    grounding_status="SUPPORTED",
    citations=(
        ("NIST-SP-800-61R3:chunk:00013:6f4012185dd40c56", "NIST-SP-800-61R3"),
    ),
    limitations=(
        "Successful authentication, compromise, attacker identity, persistence, and impact are not established.",
    ),
    boundary_claims=EvidenceBoundaryClaims(
        confirmed_compromise=False,
    ),
)

OPERATIONS = SpecialistFinding(
    specialist_id="operations",
    domains=("MAINTENANCE", "ENVIRONMENTAL"),
    assessment=(
        "Drive AT_RISK evidence and a zone-level HIGH_TEMPERATURE observation "
        "are operationally relevant in shared ZONE-B context without establishing causation."
    ),
    supported_findings=(
        "The maintenance model reports elevated seven-day failure risk.",
        "A dedicated ZONE-B sensor reports HIGH_TEMPERATURE.",
        "Phase 2 establishes shared ZONE-B context only.",
    ),
    recommended_considerations=(
        "Review drive-health and environmental evidence together while preserving separate provenance.",
    ),
    grounding_status="PARTIALLY_SUPPORTED",
    citations=(
        ("DOE-FEMP-DC-DESIGN-2024:chunk:00016:48228438e6e90d82", "DOE-FEMP-DC-DESIGN-2024"),
        ("DOE-FEMP-OM-BEST-PRACTICES:chunk:00090:27d834eac93118c4", "DOE-FEMP-OM-BEST-PRACTICES"),
    ),
    limitations=(
        "Temperature is not established as the cause of drive risk or hardware damage.",
        "The zone sensor does not directly measure the server or drive.",
    ),
    boundary_claims=EvidenceBoundaryClaims(
        causal_relationship_established=False,
        root_cause_established=False,
    ),
)


def main() -> None:
    load_dotenv(ROOT / ".env")
    result = cross_domain_synthesize(
        provider=OpenAICrossDomainSynthesisProvider(),
        findings=[CYBER, OPERATIONS],
        task=(
            "Produce a unified cross-domain assessment for validated Cybersecurity "
            "and Operations findings that Phase 2 has already related within the "
            "controlled incident context. Identify supported coordinated-review "
            "considerations without inventing compromise, causation, or root cause."
        ),
    )

    print("=" * 60)
    print("DC-GUARDIAN CROSS-DOMAIN SYNTHESIS DEMO")
    print("=" * 60)
    print("Specialists: cybersecurity + operations")
    print()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print()
    print("PASS: Structured synthesis boundary validation passed.")


if __name__ == "__main__":
    main()

