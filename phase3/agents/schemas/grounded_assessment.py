"""Grounded-assessment schema and deterministic validation."""

from __future__ import annotations

REQUIRED_KEYS = {
    "assessment",
    "supported_findings",
    "recommended_considerations",
    "grounding_status",
    "citations",
    "limitations",
}

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": sorted(REQUIRED_KEYS),
    "properties": {
        "assessment": {"type": "string"},
        "supported_findings": {
            "type": "array",
            "items": {"type": "string"},
        },
        "recommended_considerations": {
            "type": "array",
            "items": {"type": "string"},
        },
        "grounding_status": {
            "type": "string",
            "enum": ["SUPPORTED", "PARTIALLY_SUPPORTED", "INSUFFICIENT"],
        },
        "citations": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["chunk_id", "document_id"],
                "properties": {
                    "chunk_id": {"type": "string"},
                    "document_id": {"type": "string"},
                },
            },
        },
        "limitations": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
}


def validate_grounded_assessment(
    assessment: dict,
    retrieved_evidence: list[dict],
) -> None:
    missing = REQUIRED_KEYS - assessment.keys()
    extra = assessment.keys() - REQUIRED_KEYS
    if missing:
        raise ValueError(f"Missing assessment keys: {sorted(missing)}")
    if extra:
        raise ValueError(f"Unexpected assessment keys: {sorted(extra)}")

    if not isinstance(assessment["assessment"], str):
        raise ValueError("assessment must be a string.")
    for key in (
        "supported_findings",
        "recommended_considerations",
        "citations",
        "limitations",
    ):
        if not isinstance(assessment[key], list):
            raise ValueError(f"{key} must be a list.")
    if assessment["grounding_status"] not in {
        "SUPPORTED",
        "PARTIALLY_SUPPORTED",
        "INSUFFICIENT",
    }:
        raise ValueError("Invalid grounding_status.")

    allowed = {
        (item["chunk_id"], item["document_id"])
        for item in retrieved_evidence
    }
    for citation in assessment["citations"]:
        if set(citation) != {"chunk_id", "document_id"}:
            raise ValueError("Citation shape is invalid.")
        pair = (citation["chunk_id"], citation["document_id"])
        if pair not in allowed:
            raise ValueError(
                "Assessment cited evidence that was not retrieved: "
                f"{pair}"
            )

    if assessment["grounding_status"] in {
        "SUPPORTED",
        "PARTIALLY_SUPPORTED",
    } and not assessment["citations"]:
        raise ValueError(
            "Supported or partially supported assessments must cite retrieved evidence."
        )

    if not retrieved_evidence and assessment["grounding_status"] != "INSUFFICIENT":
        raise ValueError(
            "Grounding must be INSUFFICIENT when no approved evidence exists."
        )

    if assessment["grounding_status"] == "INSUFFICIENT" and not assessment["limitations"]:
        raise ValueError(
            "INSUFFICIENT assessments must state at least one limitation."
        )
