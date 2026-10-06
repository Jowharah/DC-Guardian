"""OpenAI provider for validated cross-domain specialist synthesis."""

from __future__ import annotations

import json
import os

from openai import OpenAI

from phase3.agents.schemas.cross_domain_synthesis import SYNTHESIS_SCHEMA


SYNTHESIS_INSTRUCTIONS = """You are the cross-domain synthesis component of DC-GUARDIAN.

You receive validated specialist findings, not raw evidence. Synthesize only
what those findings establish. Do not redo Phase 2 correlation and do not
strengthen a specialist's evidence boundary.

A false boundary claim supplied in boundary_summary remains false. You must not
promote identity linkage, confirmed compromise, causation, or root cause unless
the supplied boundary_summary explicitly establishes it.

Preserve specialist limitations and citations. Cite only chunk_id/document_id
pairs already supplied by the specialist findings. External standards and
guidance are not DC-GUARDIAN internal policy.

You may identify that findings warrant coordinated review because Phase 2 has
already established their incident/correlation context, but do not invent
causal relationships between domains.

Do not assign final severity, escalation, autonomous action, or operational
authority. Those belong to deterministic DC-GUARDIAN decision rules.
"""


class OpenAICrossDomainSynthesisProvider:
    def __init__(self, model: str | None = None) -> None:
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is not configured.")
        self.model = model or os.getenv(
            "DC_GUARDIAN_OPENAI_MODEL",
            "gpt-6-luna",
        )
        self.client = OpenAI()

    def synthesize(self, payload: dict) -> dict:
        response = self.client.responses.create(
            model=self.model,
            instructions=SYNTHESIS_INSTRUCTIONS,
            input=json.dumps(payload, ensure_ascii=False),
            text={
                "format": {
                    "type": "json_schema",
                    "name": "dc_guardian_cross_domain_synthesis",
                    "strict": True,
                    "schema": SYNTHESIS_SCHEMA,
                }
            },
            store=False,
        )
        return json.loads(response.output_text)
