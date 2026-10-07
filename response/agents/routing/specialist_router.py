"""Deterministic Specialist Agents specialist routing.

Routing consumes domains already established by Evidence/Reasoning. It does not ask an
LLM to rediscover domain membership or decide whether source events correlate.
"""

from __future__ import annotations

SPECIALIST_DOMAINS = {
    "physical_safety": frozenset({"PHYSICAL_SECURITY", "SAFETY"}),
    "cybersecurity": frozenset({"CYBERSECURITY"}),
    "operations": frozenset({"MAINTENANCE", "ENVIRONMENTAL"}),
}

DOMAIN_TO_SPECIALIST = {
    domain: specialist
    for specialist, domains in SPECIALIST_DOMAINS.items()
    for domain in domains
}


def route_specialists(domains: list[str] | tuple[str, ...] | set[str]) -> list[str]:
    normalized = {str(domain).upper() for domain in domains}
    if not normalized:
        raise ValueError("At least one domain is required for specialist routing.")

    unsupported = normalized - DOMAIN_TO_SPECIALIST.keys()
    if unsupported:
        raise ValueError(f"Unsupported specialist domains: {sorted(unsupported)}")

    # Stable order makes routing reproducible and testable.
    order = ("physical_safety", "cybersecurity", "operations")
    selected = {DOMAIN_TO_SPECIALIST[domain] for domain in normalized}
    return [specialist for specialist in order if specialist in selected]
