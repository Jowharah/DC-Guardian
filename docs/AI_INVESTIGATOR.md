# AI Investigator — architecture, usage, safeguards, and validation

**Updated:** 2026-10-10  
**Branch:** `feature/presentation-dashboard`  
**Status:** Implemented research prototype, locally demonstrated on approved test observations; **not** production-certified.

## Purpose and operating boundaries

The Investigator is an OpenAI-powered, read-only explanation interface over **existing DC-GUARDIAN integrations**. It does not generate synthetic Evidence, rerun frozen detectors, create graph relationships, determine correlation, assign Decision severity, or perform autonomous remediation.

Source records can still originate from controlled uploads, historical logs, or operator-declared camera/time metadata. A successful LLM answer does **not** independently verify the underlying observation.

## Existing integrations and three investigation modes

| Mode | Backend question endpoint | Sources |
|---|---|---|
| Unified correlation | `POST /api/v1/investigator/unified/{group_id}/ask` | Saved SSH, Face and PPE Evidence, correlation links, deterministic unified review, human-review outcomes |
| Operational correlation | `POST /api/v1/investigator/operations/{candidate_id}/ask` | Existing SMART/Maintenance and Environmental assessments, operational correlation, saved specialist and deterministic Decision |
| Individual Evidence | `POST /api/v1/investigator/evidence/{kind}/{evidence_id}/ask` | Existing authorized SSH, PPE, Face, Maintenance, or Environmental Evidence detail/feed |

The read-only context endpoints are `/api/v1/investigator/unified/{group_id}/context`, `/api/v1/investigator/operations/{candidate_id}/context`, and `/api/v1/investigator/evidence/{kind}/{evidence_id}/context`. Unified and operational graph endpoints reuse existing Neo4j read-only projections.

FastAPI authenticates the operator, enforces the existing role and zone checks, retrieves saved Evidence, applies bounded outbound context selection, and then calls the OpenAI Responses API. The browser requires explicit operator consent for each request. The API key is never supplied by React. The provider call uses `store=False`, but data handling and retention still require organizational review.

### LLM explanation vs authoritative Decision

- **Detector Evidence:** model classification, sensor threshold assessment, or frozen person-level PPE policy outcome.
- **Correlation:** controlled topology/time candidate only. A single-event request returns `NOT_ASSESSED_BY_SINGLE_EVIDENCE_TOOL`; this **does not** mean that no correlation exists elsewhere.
- **Saved specialist:** approved-knowledge assessment with its own limitations; it is not an independent revalidation of source Evidence.
- **Saved deterministic Decision:** may carry a standalone or operational severity; the Investigator must not modify or inherit it.
- **Human review:** an operator-recorded outcome such as `NEEDS_FOLLOW_UP`, not investigation resolution.

For SSH, six failed root logins with zero successful logins support anomalous authentication activity, **not** confirmed malicious activity, a brute-force attack, or compromise. A historical timestamp such as `2000-12-10` must remain distinct from receipt time or operator-declared controlled context time. For PPE, a missing safety-vest detection does not prove physical absence. Face recognition does not prove physical presence or entry, and does not establish identity-to-SSH or person-to-PPE association. For SMART, a seven-day failure horizon is a prediction window, not an exact failure date. Shared zone/time with a high-temperature sensor reading does not establish causation or hardware damage.

## Source references and grounding limitations

`investigator_sources.py` constructs deterministic **source manifests** from authorized context, returned as `sources` with `source_validation: REFERENCES_ONLY_NOT_CLAIM_VERIFIED`. The React UI shows a collapsible **Source Evidence** list beneath newly generated answers.

The backend now also returns a conservative `grounding_check` that compares explicit Evidence IDs appearing in generated text against the authorized source manifest. Unknown IDs are reported as `UNVERIFIED_REFERENCES`; matching IDs yield `REFERENCE_CHECK_ONLY`. The check explicitly reports `claim_validation: NOT_PERFORMED` and must not be presented as factual verification. This feature has focused tests but requires local validation after pulling.\n\n**Current limitation:** this is a source manifest, **not claim-level citation validation**. A model can still make unsupported or overly strong assertions; the presence of an Evidence ID under an answer does not validate each sentence. Previously stored conversations lack the new source metadata. Claim-to-field verification, approved knowledge citation checking, and explicit abstention/grounding evaluations remain future work.

## Frontend interaction

`InvestigatorPanel.tsx` provides selected-context chat, explicit outbound-data consent, separate operator/AI personas, expand/collapse beside the navigation, and a safe structured answer renderer (`InvestigatorMessage.tsx`). Markdown-like headings, bullets, emphasized statuses, and domain accents are presentation only; untrusted answer text must not become executable HTML.

Selected Monitoring Center context determines whether a question targets a unified group, operational pair, or individual source Evidence. Different context types must not be silently merged. The current chat does not use earlier saved messages as model input.

## Private opt-in conversation history

`investigator_history.py` stores optional question/answer pairs in **plaintext local SQLite**. It is disabled by default. `DCG_INVESTIGATOR_HISTORY_ENABLED=1` enables it, and `DCG_INVESTIGATOR_HISTORY_DAYS=7` sets a default seven-day retention (supported range: 1–30 days). History is scoped by authenticated operator, selected Evidence/group ID, and mode; single-source keys additionally include domain. Authorized users can retrieve, save, and clear their own scoped conversations.

Existing unified history routes: `GET/POST/DELETE /api/v1/investigator/unified/{group_id}/history`. Operational and single-source history use the analogous `/operations/{candidate_id}/history` and `/evidence/{kind}/{evidence_id}/history` paths. Conversation saving is explicitly opt-in; earlier unsaved conversations cannot be recovered. Storage is **not encrypted at rest** and is appropriate only for approved test conversations. A local single-operator HTTP Basic adapter is not production multi-user identity management. Retention cleanup is performed on history access, not by a guaranteed scheduled deletion job.

## Configuration

Use the repository-root private `.env` (ignored by Git). Keep `.env.example` free of secrets:

```dotenv
OPENAI_API_KEY=
DCG_INVESTIGATOR_ENABLED=0
DCG_INVESTIGATOR_MODEL=gpt-4.1-mini
DCG_INVESTIGATOR_HISTORY_ENABLED=0
DCG_INVESTIGATOR_HISTORY_DAYS=7
```

The Investigator reads values through the existing `local_setting` loader, where process environment overrides local `.env`. Enable outbound requests only after approved-data/privacy review. Never commit or paste actual credentials.

## Validation snapshot

**Reported local result, 2026-10-10:** 23 passed in 0.23s for the six focused Investigator test modules below, after the source-manifest update. This does not replace browser or production security testing.

```powershell
python -m pytest presentation/backend/tests/test_investigator_sources.py presentation/backend/tests/test_investigator_history.py presentation/backend/tests/test_investigator_tools.py presentation/backend/tests/test_investigator_chat.py presentation/backend/tests/test_investigator_operations.py presentation/backend/tests/test_investigator_single_evidence.py -q
cd presentation/frontend
npm run build
```

The browser has demonstrated live OpenAI answers for a unified investigation, a Maintenance/Environmental operational correlation, and individual SSH Evidence; unified history persistence was also demonstrated. Do not infer that every workflow or the latest frontend build has passed solely from those demonstrations.

## Grounding UI and provenance wording — October 2026

New Investigator answers display the backend `grounding_check` below the response: either **Reference check only** or **Unrecognized Evidence IDs**, and explicitly **Claim-level verification: Not performed**. This is intentionally a neutral/limitation indicator, not a green validation badge. Historical saved answers without grounding metadata do not retroactively gain a check.

The model instructions now distinguish single-source `NOT_ASSESSED_BY_SINGLE_EVIDENCE_TOOL` from confirmed absence of correlation. They also prohibit guessing why historical source timestamps exist; timestamp origin and timezone require verified provenance.

**Remaining:** deterministic numeric field-level validation (for example, failed login count and detector votes), claim-to-field citations, and tests with deliberately unsupported model claims. These have not yet been implemented.

## Outstanding safeguards

1. Claim-level source/field verification and model-grounding/abstention evaluations, including misleading time/correlation statements.
2. Strict outbound-data minimization and privacy assessment for identity, source IP, personnel, specialist narratives, and raw sensor data.
3. Dedicated tool invocation audit, request limits, cost/rate limiting, and robust provider error handling.
4. Encrypted conversation storage, backup/retention policy, real multi-user identity, and deletion auditing.
5. End-to-end RBAC, prompt-injection, source freshness, frontend accessibility and operational reliability tests.
6. Update source-manifest persistence if historical answers must display their original supporting Evidence references.

The Investigator is an **explanation aid**; DC-GUARDIAN's frozen Evidence, existing correlation contracts, deterministic Decisions, and human oversight remain authoritative.
