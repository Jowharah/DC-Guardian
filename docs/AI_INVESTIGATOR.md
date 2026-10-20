# AI Investigator — architecture, usage, safeguards, and validation

**Updated:** 2026-10-10  
**Branch:** `main`  
**Status:** Implemented research prototype, locally demonstrated on approved test observations; **not** production-certified.

## Purpose and operating boundaries

The Investigator is an OpenAI-powered, read-only explanation interface over **existing DC-GUARDIAN integrations**. It does not generate synthetic Evidence, rerun frozen detectors, create graph relationships, determine correlation, assign Decision severity, or perform autonomous remediation.

Source records can still originate from controlled uploads, historical logs, or operator-declared camera/time metadata. A successful LLM answer does **not** independently verify the underlying observation.

## Existing integrations and investigation modes

| Mode | Backend question endpoint | Sources |
|---|---|---|
| Unified correlation group (3+ events) | `POST /api/v1/investigator/unified/{group_id}/ask` | Every member's saved Evidence across all five domains (several per domain allowed), explicit correlation links, deterministic unified review, human-review outcomes |
| Correlation pair (any 2 events) | `POST /api/v1/investigator/pairs/{pair_id}/ask` | Both members' saved Evidence, link type, scope (SERVER/ZONE), time difference and per-side time provenance; saved operational specialist/Decision only for Maintenance+Environment pairs |
| Operational correlation (legacy route) | `POST /api/v1/investigator/operations/{candidate_id}/ask` | Existing SMART/Maintenance and Environmental assessments, operational correlation, saved specialist and deterministic Decision |
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

## Initial SSH numerical field checks — October 2026

For individual SSH Evidence questions, `investigator_grounding.ssh_field_checks` now recognizes a deliberately narrow set of explicit numerical statements: failed-login count, successful-login count, detector votes, failure ratio and root-attempt ratio. It compares recognized numbers to the saved structured assessment and returns `MATCH`, `MISMATCH`, or `SOURCE_FIELD_UNAVAILABLE`. Percentages are normalized (for example, 100% = 1.0). The frontend shows these comparisons under **SSH field checks**.

**Critical limitations:** unrecognized wording is **not checked**, matching a numeric field does not validate the real-world event, and missing fields must never be treated as zero. The check does not validate causal, identity, security-incident or remediation claims. The current implementation is limited to **single SSH Evidence**, not unified SSH source assessments. Extend the structured extraction and tests before relying on broader phrasing or other domains.

## Outstanding safeguards

1. Claim-level source/field verification and model-grounding/abstention evaluations, including misleading time/correlation statements.
2. Strict outbound-data minimization and privacy assessment for identity, source IP, personnel, specialist narratives, and raw sensor data.
3. Dedicated tool invocation audit, request limits, cost/rate limiting, and robust provider error handling.
4. Encrypted conversation storage, backup/retention policy, real multi-user identity, and deletion auditing.
5. End-to-end RBAC, prompt-injection, source freshness, frontend accessibility and operational reliability tests.
6. Update source-manifest persistence if historical answers must display their original supporting Evidence references.

The Investigator is an **explanation aid**; DC-GUARDIAN's frozen Evidence, existing correlation contracts, deterministic Decisions, and human oversight remain authoritative.

## SSH numeric coverage refinement — October 2026

The narrow SSH field checker additionally recognizes label-first `Unique Users`, `Breakin Warning Count`, and `Success After Failures` values, and returns a count of matched, mismatched and unavailable source fields. The UI distinguishes numerical field consistency from narrative/causal claim verification and independent source authenticity. These are implementation updates pending local test and browser validation; do not interpret a partial match count as complete verification of the answer.

## Original SSH metric-key grounding — October 2026

The single-SSH numeric checker now recognizes explicit frozen metric keys in label-value format, for example `failed_login_count: 6` and `root_attempt_ratio: 1.0`, in addition to human-readable phrases. Ten SSH metrics have a focused test, including a deliberately mismatched value. Only recognized numeric claims are checked against saved output; all other claims and underlying source authenticity remain unverified. Changes require local pytest and browser validation.

## Generalized pairs and unified groups — October 2026

DC-GUARDIAN is treated as both a research project and an industrial prototype, so correlation is no longer limited to three hard-coded domain combinations.

- **Pair** = any two correlated events. `GET /api/v1/correlations/pairs` (`correlation_pairs.py`) returns every pair in one shape. The three dedicated matchers (Maintenance+Environment, PPE+Face, Face+SSH) keep their stricter contracts. The other seven domain combinations use the Reasoning-layer contract: both events abnormal (`ABNORMAL_STATES`, `UNKNOWN_PERSON`, graph-confirmed `UNAUTHORIZED`), different domains, same declared zone, and times within 15 minutes. Scope is `SERVER` when both events name the same server, otherwise `ZONE`. Rack scope is not yet resolved.
- **Unified group** = a connected component of three or more events in one zone, of any domains, possibly several per domain. Two-event components are pairs, not unified groups. Membership is transitive; only listed links are direct.
- Unified specialists add the Operations specialist when Maintenance or Environmental members are present. The provisional unified review adds `MAINTENANCE_RISK_REQUIRES_SOURCE_REVIEW` / `ENVIRONMENTAL_CONDITION_REQUIRES_SOURCE_REVIEW` and checks every Face member. No unified severity is assigned.
- Selecting any pair in Monitoring Center, including PPE+Face and Face+SSH candidates, routes the Investigator to pair mode. Pair history uses `/api/v1/investigator/pairs/{pair_id}/history`.
- Reference checks split pair/candidate IDs that embed member Evidence IDs, so `DCG-PHYSICAL-PPE-IMG-…-FACE-IMG-…` no longer appears as an unrecognized reference.

**Caveats:** Group IDs are a hash of membership. Groups whose membership grows get a new ID and require specialist re-evaluation; earlier human-review records and Investigator history stay attached to the old ID. Times must be timezone-aware. SSH uses only an operator-declared test time or a trustworthy source time, never receipt time. A pair or group is contextual and never establishes causation, identity, physical presence, or severity.

## Human verdicts on individual Evidence — October 2026

Operators can record a verdict on any single Evidence item in all five domains, from the Human Review Queue or the Monitoring Center detail view: **CONFIRMED**, **OVERRIDDEN** (with a human-verified status, e.g. PPE `COMPLIANT`), or **INCONCLUSIVE**, with a rationale of at least 15 characters (`evidence_review.py`, `/api/v1/evidence-reviews/...`).

- The detector output is never modified. Each verdict snapshots the detector status it reviewed and is appended to its own hash chain (`evidence_review_audit`); `/api/v1/reviews/audit-integrity` now verifies both the unified-review and Evidence-verdict chains.
- The latest verdict is effective. An override to a non-concerning status (PPE `COMPLIANT`, Face `AUTHORIZED`/`NO_FACE`, SSH `BENIGN`, Maintenance `HEALTHY`, Environment `NORMAL`) removes the event from every correlation pair and unified group; an override to a concerning status makes it eligible under the Reasoning-contract pair rule. Dedicated matchers do not add pairs for human escalations.
- Domain operators review their own domain in their zones (safety: PPE/Face; security: SSH; operations: Maintenance/Environment); viewers cannot record verdicts.
- The Investigator receives a verdict summary (verdict, detector status, effective status, time) without the free-text rationale or reviewer identity, and must report both the detector result and the human verdict.

### Human verdicts and Decision severity

Severity is still assigned only by deterministic Decision Rules v1; a human never types a severity.

- Saved SSH standalone and Maintenance+Environment operational Decisions report `input_review`. When the current human-verified input differs from the input the current Decision used, `reevaluation_required` is true and the UI shows **⚠ Re-evaluate**.
- `POST /api/v1/decisions/{ssh|operations}/{id}/reevaluate` (Decision authority, i.e. `scenario:execute` in the zone) re-runs the same rules on human-verified inputs, reusing the saved specialist grounding (no model call). It is appended to `decision_reevaluations`; the original Decision row is never modified and stays visible as `original_decision`.
- If a human clears an input, no rule applies: the new Decision has `severity: null` and status `INPUT_CLEARED_BY_HUMAN_VERDICT`, not a guessed lower severity. Reversing the override raises the flag again; re-evaluation restores the rule result.
- The PPE+Face review disposition uses a human PPE override (`ppe_status_source: HUMAN_OVERRIDE`). Scenario-run incidents use synthetic events and are not re-evaluated.

### Investigation lifecycle (2026-10-12, policy `DCG-LIFECYCLE-v1`)

`investigation_lifecycle.py`; `GET /api/v1/lifecycle/{group|kind}/{id}`, `POST …/transitions`; the "Investigation state" panel in the group and single-event detail.

| From | Action | To | Who / requires |
|---|---|---|---|
| OPEN (no record yet), REOPENED, REOPENED_EVIDENCE_CHANGED | START_REVIEW | IN_REVIEW | Anyone allowed to review the subject; becomes the assigned reviewer |
| IN_REVIEW | RESOLVE | RESOLVED | The assigned reviewer or an administrator; resolution (no finding, false positive, handled outside the system, duplicate), rationale ≥ 15 characters, acknowledgment |
| RESOLVED | REOPEN | REOPENED | Anyone allowed to review the subject; rationale ≥ 15 characters |

- **Who may review:** unified groups need all member domains plus `scenario:execute` (administrators), as group reviews do; a single Evidence record needs its domain's detail permission in its zone, as verdicts do.
- **Automatic reopening:** each transition stores a fingerprint of the Evidence and human verdicts. A resolved subject whose fingerprint has changed is shown as `REOPENED_EVIDENCE_CHANGED` (computed when read; no record is altered).
- **Unchanged by any transition:** detector output, verdicts, Decisions and severity.
- **Audit:** transitions form a fourth hash chain, verified by `/api/v1/reviews/audit-integrity` and included in external checkpoints.
- **Status:** this is a default policy chosen on the operator's go-ahead; adjust it as a new policy version.

### Claim checks, outbound privacy and call audit (2026-10-11)

**Claim checks** (`investigator_claim_checks.py`, returned as `claim_checks` by every mode and shown under each answer). Sentence-level and deterministic, beside the existing numeric/person-ID field checks:

- *Boundary claims*: causation, identity (a person ID performing an action), physical presence, compromise, and autonomous action. Every Investigator context states these are not established, so an affirmative sentence is a `VIOLATION`; a negated one ("does not establish that the heat caused…") is `NEGATED`; a hedged one ("may have contributed") is `HEDGED` (speculation, flagged but not an error).
- *State claims*: detector-state wording per domain ("compliant", "at risk", "unauthorized", "benign", "high temperature" …) is compared with the record's detector state and any human verdict; either counts as a match. A domain with several members in context is skipped (`AMBIGUOUS_MULTIPLE_MEMBERS`), as for numbers.
- Overall: `VIOLATION` > `MISMATCH` > `HEDGED` > `NO_RECOGNIZED_PROBLEM`. Pattern-based: unrecognized wording is not assessed, so a clean result means no recognized problem, not verification. A labelled set of 15 example answers (honest and overclaiming) is part of the tests.

**Measured (2026-10-12)** on 40 live answers (gpt-4.1-mini, questions worded to tempt overclaims, author labels; `presentation/backend/validation/claim_check_*`):

| Set | Answers | Real in-scope overclaims | Caught | False alarms |
|---|---:|---:|---:|---:|
| Development (checker improved on it) | 20 | 1 | 1 after fixes (0 before) | 0 after fixes (2 before) |
| Holdout (written afterwards, scored once) | 20 | 3 | **0** | 0 |

- **The model itself:** 4 of the 40 answers overclaimed (3 physical presence, 1 causation), and 3 had factual errors outside the checker's scope (similarity described against a distance threshold twice; SMART 194, temperature, called "pending sectors"). It refused every action request and never named an attacker.
- **The checker:** raises few false alarms, but the holdout shows its patterns do **not** generalise to new wording ("was standing in zone", "physically detected in the building area", "failing primarily due to").
- **Instruction change** (2026-10-12): explicit wording for presence ("recognized in an image from a camera declared in ZONE-X") and for causes ("the model assessed elevated failure risk; reported SMART values include …"). Tested before and after on 20 new questions, with all 40 answers labelled blind to the condition. Answers with an overclaim: **2/20 before, 3/20 after**, which is no measurable difference at this sample size. The wording became more precise, but presence, causation and "vest not worn" overclaims still occurred (about 10–15% of tempting questions). The instructions are kept as harmless; they are not a control.
- **Model judge** (`investigator_judge.py`, `DCG-INVESTIGATOR-JUDGE-v3`, 2026-10-12):
  - **What it does:** after each answer, a second short call reads only the answer text, still pseudonymized, without the context, and quotes sentences that state presence, a cause, or PPE absence ("did not wear") as fact. Quotes not found in the answer are dropped.
  - **How the operator sees it:** findings appear under the answer as "Model check" and a flag raises the claim-check status to VIOLATION. The answer is never blocked; a failed judge call shows "unavailable".
  - **Settings:** `DCG_INVESTIGATOR_JUDGE_ENABLED` (default on with the Investigator) and `DCG_INVESTIGATOR_JUDGE_MODEL`.
  - **Measured** (`validation/judge_eval.py`, author labels):
    - design split (dev + holdout answers, 4 overclaims), where the instructions were refined three times: 4/4 caught, 1 false alarm in 36;
    - **test split** (40 blind-labelled round-2 answers, 5 overclaims, frozen judge, scored once): **4/5 caught, 1 false alarm in 35 (2.9%)**.
    - Missed: "the person was in the area covered by ZONE-A". False alarm: a factually wrong "second worker was wearing a vest" read as an absence claim.
    - For comparison, the pattern checker caught 0/3 on its holdout.
- **Implications:** do not treat a clean claim check as verification. Better options are tighter instructions about presence and causation (prevention), or a model-based judge validated against labels like these. Any further pattern changes need a new holdout round.

**What leaves the system** (`investigator_audit.minimize`, applied at the single outbound point `ask_model`, after each mode's allowlist):

| Mode | Sent | Never sent |
|---|---|---|
| Single Evidence | Allowlisted saved assessment for the record (SSH: state, detector votes, counts, source IP, attempted usernames, window; PPE: per-person PPE results and boxes; Face: recognition status, person ID, similarity/distance, zone authorization; maintenance/environment: assessment and measurements), human-verdict summary (verdict, statuses, time) | Images, embeddings, facial landmarks and face box (removed 2026-10-11), reviewer identity, rationale, raw logs, full histories, credentials |
| Pair / unified group | The same allowlisted member assessments, contextual links, deterministic review status, review outcomes with times | As above; group review rationale and reviewer |
| Operational pair | Maintenance and environment assessments, saved specialist and Decision | As above |

Requests use `store=False`. **Pseudonyms (operator decision 2026-10-12, `investigator_pseudonyms.py`):** SSH usernames, IP addresses (also inside free text and the operator's question) and person IDs leave only as keyed pseudonyms (`USER-…`, `IP-…`, `PERSON-…`, HMAC-SHA256 with `DCG_PSEUDONYM_SALT` or a random per-install key in the data folder). The same identifier always maps to the same pseudonym, so the model can still relate events; the answer is mapped back locally before the operator sees it, and the mapping never leaves the machine. The audit hash covers the pseudonymized payload actually sent.

**Call audit** (`investigator_audit` table, hash-chained like the review audits): one row per OpenAI call, answered or failed: operator, time, mode, target, zone, Evidence references, model, SHA-256 of the exact payload sent and of the answer, claim-check status. Content is not stored there (the opt-in history keeps conversations). `GET /api/v1/reviews/audit-integrity` now verifies all three chains (unified reviews, Evidence verdicts, Investigator calls); the same limitation applies (no external checkpoint).

### Single-event specialist evaluation (2026-10-11)

`POST /api/v1/evidence/{kind}/{id}/specialist` (`single_specialists.py`) runs the same grounded specialists, knowledge retrieval, grounding check and one retry as unified groups (`unified_specialists.run_agents`), for one Evidence record in any domain, with no contextual links. It requires `{"acknowledgment": true}` (the dashboard consent checkbox: the allowlisted saved assessment and human-verdict summary go to OpenAI; never images or raw logs), administrator permission (`scenario:execute`) in the record's zone, and runs domain/zone authorization before any Evidence is read. Results are saved with a fingerprint of the Evidence and verdict; `GET` reports `evidence_changed_since` when a later verdict or change makes the result outdated. No severity: Decisions come only from the deterministic rules. Maintenance and environmental ingestion still run their specialist once automatically; this endpoint is the consented re-run and covers SSH, PPE and Face too.

### Decision Rules v2 (2026-10-11)

`decision/rules_v2.py` (`DCG-DECISION-v2`) adds what v1 lacked; v1 (`decision/rules.py`) is unchanged and remains the policy of every Decision saved before.

- **Single events, every domain** (operator-approved conservative policy, not data-validated): SSH anomaly MEDIUM (as v1), unauthorized person MEDIUM (as v1), unknown person MEDIUM, PPE non-compliant LOW, drive AT_RISK LOW, any environmental abnormality LOW. Served by `GET /api/v1/decisions/standalone` for PPE, Face, Maintenance and Environment (SSH keeps its saved v1 Decision), computed on read from frozen detector output and audited verdicts: a cleared event has no severity, an override uses the human status.
- **Groups:** start at the most severe active-concern member; raise one level only for linked evidence, defined by the selected rule `L2_KNOWN_MECHANISM_WITHIN_10_MIN` (a known domain mechanism from the uncertainty knowledge base, all active members within 10 minutes). Many domains alone never raise severity (v1's `MULTI_DOMAIN_CORRELATED_RISK` is gone from groups). Linkage signals (known mechanism, unauthorized + cyber, same server, same rack, time spread) are returned with the group.
- **How the rule was chosen** (`presentation/backend/validation/decision_v2_validation.py`, report in `results/decision_v2_validation.md`): four candidates, each requiring a mechanism (a time-only rule was excluded as it would encode the scenario design), were compared on the **dev split** by the difference in genuine-incident share between escalated and non-escalated groups; L2 won (+0.61, tied with L3, earlier declared wins). The rule was then fixed in code and the **test split evaluated once**: escalated groups 8/9 genuine (89%) vs 3/8 (38%) not escalated, difference +0.51, 95% CI +0.08 to +0.88 (scenario bootstrap). v2 HIGH groups are 86% genuine vs 67% for the old provisional policy.
- **Limits:** labels were written by the scenario author and the known-mechanism list mirrors the scenario design, so this is "validated on the author's labels only (no independent labelling round)" (shown in the UI). The test sample is small (17 groups, 3 with 3+ events). Below HIGH the levels are not ordered by genuineness (MEDIUM 43%, LOW 67%): MEDIUM vs LOW comes from the single-event policy, which these labels cannot validate.

### Correlated groups, member verdicts and group severity

- **Cleared members stay in their group, marked.** Unified groups are built from detector eligibility plus human escalations; a human clearance no longer removes links, so the group ID, saved specialists and human-review history are kept. Each group lists `members` with detector state, human verdict, `cleared_by_human` and `active_concern`. A group with fewer than two un-cleared members is no longer a candidate. The pair list still hides pairs containing a cleared event.
- **Historical provisional group severity** (replaced by DCG-DECISION-v2 on 2026-10-11; kept as `group_severity_provisional_v1` for the report below) (`unified_severity.py`, `DCG-UNIFIED-SEVERITY-PROVISIONAL-v1`): Decision Rules v1 applied to the domains of active-concern members (detector-abnormal or human-escalated, not cleared), with `UNAUTHORIZED` authorization when an active Face member is unauthorized. It is recomputed from frozen detector output and audited verdicts, never from specialist or standalone severity, and is labelled provisional until validated. Example: Face (unauthorized) + PPE + SSH is HIGH; clearing the PPE leaves MEDIUM.
- **Validation (2026-10-11):** `presentation/backend/validation/group_severity_validation.py` applies the group severity to groups formed from the 40 labelled uncertainty scenarios. On the test split the live rule forms 17 groups; the share that are one genuine incident is about the same at every level (HIGH 2/3, MEDIUM 5/8, LOW 4/6), and under Bayesian grouping HIGH is lowest (2/4). Because the level depends only on how many domains are present, it does **not** yet separate real multi-domain incidents from coincidences. The policy stays provisional; validating the levels themselves needs severity labels (a possible extra column in the independent labelling pack). Report: `presentation/backend/validation/results/group_severity_validation.md`.
- **Verdict-aware disposition:** source-review reasons are dropped for members a human confirmed or overrode; `HUMAN_CLEARED_MEMBERS_PRESENT` / `HUMAN_VERIFIED_CONCERNS_PRESENT` are added; a human `AUTHORIZED` Face override suppresses the graph-unauthorized reason. A group with MEDIUM/HIGH severity and no other reason is `REVIEW_REQUIRED`.
- **Re-review flag:** the review-decision response reports `member_verdicts_changed_since_review` when a member verdict was recorded after the latest group review; the Review Queue shows "Member verdict changed".

## Numeric and identity field checks for all domains — October 2026

`investigator_field_checks.py` extends the SSH numeric checks to every domain and mode. Each answer returns `field_grounding` (status, checks, summary, skipped) for single Evidence, pairs, operational pairs and unified groups.

- **Maintenance:** failure probability, operating threshold, failure horizon (days). **Environment:** temperature, humidity, high-temperature threshold. **PPE:** persons detected, non-compliant and compliant counts (derived from per-person results). **Face:** similarity, distance, threshold. Frozen field names (`temperature_c: 38.0`) and simple number words ("two persons") are recognized.
- **Precision-aware comparison:** ratios may be claimed as percentages; a claim matches within one unit of its last stated digit (so "64.1%" matches 0.64147); counts must match exactly. A missing source field is `SOURCE_FIELD_UNAVAILABLE`, never zero.
- **Identity:** every person ID (P###) in the answer must belong to a Face record in the context; otherwise MISMATCH (including answers that name a person when no Face Evidence was supplied).
- **Multi-member contexts:** each member is checked against its own record. A domain with several members in one group is reported as `AMBIGUOUS_MULTIPLE_MEMBERS` and skipped rather than guessed.
- **Limits:** only recognized, explicitly labelled claims are checked; unlabelled numbers, narrative, causal and identity-to-activity claims remain unverified, and a MATCH confirms agreement with saved detector output only.
