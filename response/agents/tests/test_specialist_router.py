"""Contracts for deterministic Specialist Agents specialist routing."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from response.agents.routing.specialist_router import route_specialists  # noqa: E402


def expect(domains, expected):
    actual = route_specialists(domains)
    if actual != expected:
        raise AssertionError(
            f"Routing failed for {domains}: expected {expected}, got {actual}"
        )
    print(f"PASS: {domains} -> {actual}")


import pytest  # noqa: E402

ROUTES = [
    (["PHYSICAL_SECURITY"], ["physical_safety"]),
    (["SAFETY"], ["physical_safety"]),
    (["PHYSICAL_SECURITY", "SAFETY"], ["physical_safety"]),
    (["CYBERSECURITY"], ["cybersecurity"]),
    (["MAINTENANCE"], ["operations"]),
    (["ENVIRONMENTAL"], ["operations"]),
    (["MAINTENANCE", "ENVIRONMENTAL"], ["operations"]),
    (["CYBERSECURITY", "MAINTENANCE", "ENVIRONMENTAL"], ["cybersecurity", "operations"]),
    (["SAFETY", "CYBERSECURITY", "PHYSICAL_SECURITY"], ["physical_safety", "cybersecurity"]),
]


@pytest.mark.parametrize("domains,expected", ROUTES)
def test_domains_route_to_specialists(domains, expected):
    expect(domains, expected)


def test_shared_policy_is_not_a_specialist_domain():
    with pytest.raises(ValueError):
        route_specialists(["SHARED_POLICY"])


def main():
    for domains, expected in ROUTES:
        test_domains_route_to_specialists(domains, expected)
    test_shared_policy_is_not_a_specialist_domain()
    print("PASS: SHARED_POLICY is not routed as a specialist domain.")
    print("=" * 60)
    print("DC-GUARDIAN SPECIALIST AGENTS SPECIALIST ROUTER CONTRACT PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
