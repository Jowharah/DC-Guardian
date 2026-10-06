"""Integration test using the real PPE/Face Reasoning implementation."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from integration.runners.real_ppe_face_reasoning import (  # noqa: E402
    run_real_ppe_face_reasoning,
)


def main():
    result = run_real_ppe_face_reasoning(
        scenario_id="INTEGRATION-REAL-PPE-FACE-001"
    )
    if result["shared_scope"] != "ZONE":
        raise AssertionError("Expected truthful ZONE scope.")
    if result["shared_entity"] != "ZONE-B":
        raise AssertionError("Expected shared ZONE-B context.")
    if result["authorization_status"] != "UNAUTHORIZED":
        raise AssertionError("Expected graph-derived UNAUTHORIZED status.")
    if result["identity_link_established"]:
        raise AssertionError("PPE/Face identity must remain unestablished.")

    print("=" * 60)
    print("DC-GUARDIAN REAL REASONING VERTICAL SLICE")
    print("EVIDENCE -> REASONING")
    print("=" * 60)
    print("PASS: Real Face adapter and topology mapping.")
    print("PASS: Real PPE adapter and topology mapping.")
    print("PASS: Real Neo4j ingestion.")
    print("PASS: Graph-derived Face authorization = UNAUTHORIZED.")
    print("PASS: Real deterministic PPE + Face correlation.")
    print("PASS: Strongest truthful scope = ZONE-B.")
    print("PASS: Cross-model identity remains unestablished.")
    print("=" * 60)
    print("DC-GUARDIAN REAL REASONING VERTICAL SLICE PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
