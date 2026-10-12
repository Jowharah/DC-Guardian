"""Model-based check of Investigator answers for overclaims (after generation).

The pattern checks (investigator_claim_checks) miss new wording (holdout recall
0/3, 2026-10-12), and tighter instructions did not reduce overclaims (2/20 vs
3/20, blind). This judge reads only the answer text, with identifiers still
pseudonymized, and flags sentences that state as fact one of:

- PRESENCE:  a person was physically present or located somewhere;
- CAUSATION: why something happened, including why a model reached its output;
- ABSENCE:   a person was not wearing / lacked PPE (rather than "not detected").

Negated, hedged ("may", "could") or human-verdict-attributed statements are not
flags. The judge never blocks an answer: the operator sees the answer with the
flagged sentences, and a judge failure is reported as UNAVAILABLE. Measured on
labelled live answers (presentation/backend/validation/judge_eval.py).
Enabled with DCG_INVESTIGATOR_JUDGE_ENABLED=1 (default on when the Investigator
is enabled); one extra short model call per answer.
"""
import json
import logging

from presentation.backend.app.authentication import local_setting

logger = logging.getLogger(__name__)
VERSION = "DCG-INVESTIGATOR-JUDGE-v3"

JUDGE_INSTRUCTIONS = """You check answers written by a data-center investigation assistant.
The assistant only has detector records (camera images, sensor readings, SSH logs,
drive-health model outputs) and must not state more than they establish.
Most sentences are fine. Flag a sentence only if it clearly states AS A REAL-WORLD FACT:

PRESENCE - where a person physically was: "was standing in", "was in the hall/room/area/building",
  "was on site", "was inside", "physically detected in", "indicating physical presence".
  NOT presence: "detected/recognized in ZONE-X", "recognized in an image from a camera in ZONE-X",
  "N people detected in the scene/image", record fields, or authorization ("is authorized for ZONE-X").

CAUSATION - a real-world cause of an event or condition (drive failure or degradation, temperature
  rise, damage, a worker's behaviour), or which inputs drove a statistical model's risk score
  ("failing primarily due to", "degrading because of", "risk based largely on X",
  "X is not a contributing factor").
  NOT causation: an observation meeting a stated rule or threshold ("classified as anomalous due to
  6 failed attempts", "exceeds the 35 C threshold"), reasons for the assistant's own limits
  ("not allowed due to read-only restrictions"), or "the cause was not assessed".

ABSENCE - a person did not wear or lacked PPE: "was not wearing", "did not wear", "was without".
  NOT absence: "missing", "not detected", "not associated", "non-compliant", "detected wearing only",
  "detected wearing only a helmet and missing the safety-vest", or any statement attributed to the
  detector or assessment ("according to the PPE assessment").

Never flag negated statements ("does not establish that the heat caused"), hedged ones ("may",
"might", "could", "possibly", "suggests", "potential"), statements attributed to a human reviewer,
statements attributed to the detector or the assessment ("according to the detector/assessment"),
headings, or limitations. When unsure, do not flag.
Return JSON only. Quote each flagged sentence exactly as written."""

SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["findings"],
    "properties": {"findings": {"type": "array", "items": {
        "type": "object", "additionalProperties": False, "required": ["type", "sentence", "reason"],
        "properties": {"type": {"type": "string", "enum": ["PRESENCE", "CAUSATION", "ABSENCE"]},
                       "sentence": {"type": "string"}, "reason": {"type": "string"}}}}},
}


def enabled():
    value = local_setting("DCG_INVESTIGATOR_JUDGE_ENABLED")
    return value != "0" if value else local_setting("DCG_INVESTIGATOR_ENABLED") == "1"


def judge(masked_answer, client=None, model=None):
    """{"status": FLAGGED|CLEAN|UNAVAILABLE|DISABLED, "findings": [...]} for a pseudonymized answer."""
    if not enabled():
        return {"status": "DISABLED", "findings": [], "version": VERSION}
    try:
        if client is None:
            from openai import OpenAI
            client = OpenAI(api_key=local_setting("OPENAI_API_KEY"), timeout=30.0, max_retries=0)
        response = client.responses.create(
            model=model or local_setting("DCG_INVESTIGATOR_JUDGE_MODEL") or local_setting("DCG_INVESTIGATOR_MODEL") or "gpt-4.1-mini",
            instructions=JUDGE_INSTRUCTIONS, input=masked_answer, max_output_tokens=600, store=False,
            text={"format": {"type": "json_schema", "name": "overclaim_findings", "strict": True, "schema": SCHEMA}})
        findings = json.loads(response.output_text)["findings"]
        # Keep only quotes that really occur in the answer (no invented sentences).
        plain = masked_answer.replace("*", "")
        findings = [f for f in findings if f["sentence"].strip()
                    and f["sentence"].replace("*", "").strip()[:40] in plain]
    except Exception as exc:  # noqa: BLE001 - the answer is still shown, marked unchecked
        logger.warning("Investigator judge unavailable: %s", type(exc).__name__)
        return {"status": "UNAVAILABLE", "findings": [], "version": VERSION}
    return {"status": "FLAGGED" if findings else "CLEAN", "findings": findings, "version": VERSION}
