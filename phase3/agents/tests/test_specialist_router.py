"""Contracts for deterministic Phase 3.3 specialist routing."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from phase3.agents.routing.specialist_router import route_specialists  # noqa: E402


def expect(domains, expected):
    actual = route_specialists(domains)
    if actual != expected:
        raise AssertionError(
            f"Routing failed for {domains}: expected {expected}, got {actual}"
        )
    print(f"PASS: {domains} -> {actual}")


def main():
    expect(["PHYSICAL_SECURITY"], ["physical_safety"])
    expect(["SAFETY"], ["physical_safety"])
    expect(
        ["PHYSICAL_SECURITY", "SAFETY"],
        ["physical_safety"],
    )
    expect(["CYBERSECURITY"], ["cybersecurity"])
    expect(["MAINTENANCE"], ["operations"])
    expect(["ENVIRONMENTAL"], ["operations"])
    expect(
        ["MAINTENANCE", "ENVIRONMENTAL"],
        ["operations"],
    )
    expect(
        ["CYBERSECURITY", "MAINTENANCE", "ENVIRONMENTAL"],
        ["cybersecurity", "operations"],
    )
    expect(
        ["SAFETY", "CYBERSECURITY", "PHYSICAL_SECURITY"],
        ["physical_safety", "cybersecurity"],
    )

    try:
        route_specialists(["SHARED_POLICY"])
    except ValueError:
        print("PASS: SHARED_POLICY is not routed as a specialist domain.")
    else:
        raise AssertionError("Unsupported SHARED_POLICY routing was accepted.")

    print("=" * 60)
    print("DC-GUARDIAN PHASE 3.3 SPECIALIST ROUTER CONTRACT PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
