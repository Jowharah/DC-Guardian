"""Deterministic knowledge-eligibility policy for DC-GUARDIAN RAG."""

from __future__ import annotations

import json
from pathlib import Path

RAG_ROOT = Path(__file__).resolve().parent
MANIFEST_FILE = RAG_ROOT / "manifests" / "knowledge_manifest.json"


def _manifest() -> dict:
    with MANIFEST_FILE.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def active_sources_for_domains(domains: list[str]) -> list[dict]:
    requested = {str(x).upper() for x in domains}
    return [
        source
        for source in _manifest()["sources"]
        if source.get("approval_status") == "APPROVED"
        and source.get("retrieval_status") == "ACTIVE"
        and requested.intersection(
            {x.upper() for x in source.get("applicable_domains", [])}
        )
    ]


def evaluate_knowledge_eligibility(
    *,
    domains: list[str],
    required_authority_type: str | None = None,
    required_source_type: str | None = None,
) -> dict:
    if not domains:
        raise ValueError("domains must be a non-empty list.")

    candidates = active_sources_for_domains(domains)

    if required_authority_type:
        candidates = [
            x for x in candidates
            if x.get("authority_type") == required_authority_type
        ]
    if required_source_type:
        candidates = [
            x for x in candidates
            if x.get("source_type") == required_source_type
        ]

    eligible = bool(candidates)
    return {
        "status": (
            "ELIGIBLE"
            if eligible
            else "INSUFFICIENT_APPROVED_KNOWLEDGE"
        ),
        "eligible": eligible,
        "domains": domains,
        "required_authority_type": required_authority_type,
        "required_source_type": required_source_type,
        "eligible_document_ids": [
            x["document_id"] for x in candidates
        ],
        "reason": (
            "Approved active knowledge is available for the requested scope."
            if eligible
            else "No approved active knowledge satisfies the requested authority/source scope."
        ),
    }
