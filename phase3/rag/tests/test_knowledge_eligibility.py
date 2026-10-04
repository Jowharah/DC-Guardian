"""Contract tests for deterministic knowledge eligibility."""

from __future__ import annotations

import sys
from pathlib import Path

RAG_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAG_ROOT))

from knowledge_eligibility import evaluate_knowledge_eligibility  # noqa: E402


def main() -> None:
    physical = evaluate_knowledge_eligibility(
        domains=["PHYSICAL_SECURITY"]
    )
    if not physical["eligible"]:
        raise AssertionError("Physical-security knowledge should be eligible.")
    if "NIST-SP-800-53R5-PE" not in physical["eligible_document_ids"]:
        raise AssertionError("Expected physical-security source missing.")

    project_policy = evaluate_knowledge_eligibility(
        domains=["SHARED_POLICY"],
        required_authority_type="PROJECT_POLICY",
        required_source_type="DC_GUARDIAN_INTERNAL",
    )
    if project_policy["eligible"]:
        raise AssertionError(
            "Planned/inactive DC-GUARDIAN policy must not be eligible."
        )
    if project_policy["status"] != "INSUFFICIENT_APPROVED_KNOWLEDGE":
        raise AssertionError("Incorrect insufficient-knowledge status.")

    safety = evaluate_knowledge_eligibility(
        domains=["SAFETY"],
        required_authority_type="REGULATION",
    )
    if not safety["eligible"]:
        raise AssertionError("Approved safety regulations should be eligible.")

    print("=" * 60)
    print("DC-GUARDIAN KNOWLEDGE ELIGIBILITY CONTRACT PASSED")
    print("=" * 60)
    print("Physical security: ELIGIBLE")
    print("Project policy:    INSUFFICIENT_APPROVED_KNOWLEDGE")
    print("Safety regulation: ELIGIBLE")


if __name__ == "__main__":
    main()
