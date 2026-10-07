"""Grounded reasoning orchestration for DC-GUARDIAN Phase 3.2."""

from __future__ import annotations

from response.agents.schemas.grounded_assessment import (
    validate_grounded_assessment,
)


def build_reasoning_payload(
    *,
    incident_evidence: dict,
    retrieved_evidence: list[dict],
    task: str,
) -> dict:
    return {
        "task": task,
        "incident_evidence": incident_evidence,
        "retrieved_approved_knowledge": [
            {
                "chunk_id": item["chunk_id"],
                "document_id": item["document_id"],
                "title": item["title"],
                "authority_type": item["authority_type"],
                "publisher": item["publisher"],
                "version": item.get("version"),
                "pages": item["pages"],
                "text": item["text"],
            }
            for item in retrieved_evidence
        ],
    }


def grounded_reason(
    *,
    provider,
    incident_evidence: dict,
    retrieved_evidence: list[dict],
    task: str,
) -> dict:
    payload = build_reasoning_payload(
        incident_evidence=incident_evidence,
        retrieved_evidence=retrieved_evidence,
        task=task,
    )
    result = provider.reason(payload)
    validate_grounded_assessment(result, retrieved_evidence)
    return result

