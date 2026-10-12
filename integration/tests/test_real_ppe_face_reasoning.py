"""Integration test using the real PPE/Face Reasoning implementation."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from integration.runners.real_ppe_face_reasoning import (  # noqa: E402
    run_real_ppe_face_reasoning,
)


import pytest  # noqa: E402

# Needs Neo4j (real ingestion and graph authorization), like the Reasoning contracts.
pytestmark = pytest.mark.neo4j


@pytest.fixture(scope="module")
def result():
    from reasoning.graph.ingest_event import create_driver
    try:
        create_driver().close()
    except Exception as exc:  # noqa: BLE001 - any connection failure means "not available"
        pytest.skip(f"Neo4j not reachable: {type(exc).__name__}")
    return run_real_ppe_face_reasoning(scenario_id="INTEGRATION-REAL-PPE-FACE-001")


def test_scope_is_the_truthful_shared_zone(result):
    assert result["shared_scope"] == "ZONE"
    assert result["shared_entity"] == "ZONE-B"


def test_authorization_comes_from_the_graph(result):
    assert result["authorization_status"] == "UNAUTHORIZED"


def test_identity_link_stays_unestablished(result):
    assert not result["identity_link_established"]


def main():
    data = run_real_ppe_face_reasoning(scenario_id="INTEGRATION-REAL-PPE-FACE-001")
    test_scope_is_the_truthful_shared_zone(data)
    test_authorization_comes_from_the_graph(data)
    test_identity_link_stays_unestablished(data)
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
