"""Controlled scenarios for integrated Evidence -> Reasoning -> Response tests."""

from __future__ import annotations


def ppe_face_scenario() -> dict:
    return {
        "scenario_id": "INTEGRATION-PPE-FACE-001",
        "scenario_type": "CONTROLLED_SYNTHETIC_SCENARIO",
        "evidence_inputs": {
            "face": {
                "person_id": "TEST-P003",
                "recognition_status": "RECOGNIZED",
                "camera_id": "CAM-B-01",
                "timestamp": "2026-10-06T12:00:00Z",
            },
            "ppe": {
                "person_index": 0,
                "compliance": "NON_COMPLIANT",
                "required_ppe": ["helmet", "safety-vest"],
                "camera_id": "CAM-B-01",
                "timestamp": "2026-10-06T12:01:00Z",
            },
        },
        "expected_domains": ["PHYSICAL_SECURITY", "SAFETY"],
        "expected_specialists": ["physical_safety"],
        "identity_boundary": (
            "No explicit cross-model identity evidence links PPE person_index=0 "
            "to Face person_id=TEST-P003."
        ),
    }
