"""Structured output contract for cross-domain synthesis."""

from __future__ import annotations

SYNTHESIS_REQUIRED_KEYS = {
    "assessment",
    "contributing_specialists",
    "supported_cross_domain_findings",
    "recommended_considerations",
    "grounding_status",
    "citations",
    "limitations",
    "boundary_claims",
}

SYNTHESIS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": sorted(SYNTHESIS_REQUIRED_KEYS),
    "properties": {
        "assessment": {"type": "string"},
        "contributing_specialists": {
            "type": "array",
            "items": {"type": "string"},
        },
        "supported_cross_domain_findings": {
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
        "boundary_claims": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "identity_link_established",
                "confirmed_compromise",
                "causal_relationship_established",
                "root_cause_established",
            ],
            "properties": {
                "identity_link_established": {"type": "boolean"},
                "confirmed_compromise": {"type": "boolean"},
                "causal_relationship_established": {"type": "boolean"},
                "root_cause_established": {"type": "boolean"},
            },
        },
    },
}
