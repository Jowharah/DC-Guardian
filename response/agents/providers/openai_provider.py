"""OpenAI Responses API provider for DC-GUARDIAN grounded reasoning."""

from __future__ import annotations

import json
import os

from openai import OpenAI

from response.agents.providers.base import GroundedReasoningProvider
from response.agents.schemas.grounded_assessment import SCHEMA


SYSTEM_INSTRUCTIONS = """You are the grounded reasoning component of DC-GUARDIAN.

Use only INCIDENT_EVIDENCE and RETRIEVED_APPROVED_KNOWLEDGE supplied in the
request. Do not use outside knowledge to fill missing project policy, facts,
identities, procedures, thresholds, or escalation rules.

External standards/guidance are not DC-GUARDIAN internal policy.

Every supported finding and recommendation must be supportable by the supplied
incident evidence and retrieved approved knowledge. Cite only supplied chunk_id
and document_id pairs.

If the available approved evidence does not support the requested conclusion,
set grounding_status to INSUFFICIENT, state the limitation, and do not invent
the missing answer.

Use grounding_status as follows:
- SUPPORTED: the supplied evidence supports the requested assessment/conclusion.
- PARTIALLY_SUPPORTED: some useful findings are supported, but material parts of
  the requested conclusion remain unresolved.
- INSUFFICIENT: the supplied approved evidence cannot support the requested
  conclusion.

Do not assign final severity, execute actions, unlock doors, disable systems,
or claim autonomous authority. Those decisions belong to deterministic
DC-GUARDIAN rules.
"""


class OpenAIResponsesProvider(GroundedReasoningProvider):
    def __init__(self, model: str | None = None) -> None:
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is not configured.")
        self.model = model or os.getenv(
            "DC_GUARDIAN_OPENAI_MODEL",
            "gpt-6-luna",
        )
        self.client = OpenAI()

    def reason(self, payload: dict) -> dict:
        response = self.client.responses.create(
            model=self.model,
            instructions=SYSTEM_INSTRUCTIONS,
            input=json.dumps(payload, ensure_ascii=False),
            text={
                "format": {
                    "type": "json_schema",
                    "name": "dc_guardian_grounded_assessment",
                    "strict": True,
                    "schema": SCHEMA,
                }
            },
            store=False,
        )
        return json.loads(response.output_text)

