# DC-GUARDIAN — Remaining development roadmap

**Updated:** 2026-10-11. Status reflects observed code and reported local tests on `main`, not production readiness.

| Feature | Status | Remaining work |
|---|---|---|
| Severity colors and dashboard consistency | Implemented; **automated WCAG 2.1 A/AA scan (axe-core) of every main screen in the Playwright suite, zero violations** (2026-10-12) | Manual keyboard and screen-reader review; responsive regression |
| Live-time synthetic events | Partial / controlled validators available | End-to-end time provenance and live simulation verification |
| SSH raw logs, usernames and source IPs | Detector Evidence and metadata implemented | Decide governed raw-log retention policy; currently raw logs intentionally not retained |
| PPE image upload and annotated detections | Implemented and demonstrated | Protected artifact-access and detector/association regression |
| Face recognition Evidence and zone authorization | Implemented and demonstrated | Enrollment privacy, zone access and identity-review hardening |
| SMART measurements and server health history | Implemented and demonstrated | Longitudinal reliability, edge cases and UI tests |
| Environmental measurements and trends | Implemented and demonstrated | Sensor data validation, temporal handling and UI tests |
| RBAC-protected Evidence artifact access | **Access matrix test** (2026-10-11) covers all 99 operations × every role (401 without credentials, 403 exactly where a permission is missing); zone isolation with real records in the domain RBAC tests | Multi-user integration testing |
| Analytics and interactive drill-down | Implemented; detector outcomes per domain with human verdicts, Decision severity from one shared per-row rule; Playwright test | Additional chart and filter regression |
| Monitoring Center summary | Implemented 2026-10-11: live/delayed/offline status, Needs attention, abnormal results, correlations, Decisions by level, domain freshness strip, card filters; Playwright test | Accessibility review |
| Human Review Queue and saved outcomes | Implemented and locally demonstrated | Multi-review lifecycle policy and investigation resolution contract |
| Human verdicts on individual Evidence (confirm / override / inconclusive) | Implemented; backend and Playwright browser tests; v2 single-event Decisions follow verdicts (cleared → no severity, override → human status) | Policy for who may override which domain in production; reporting overrides as model false-positive/negative metrics |
| Audit hash-chain verification | Three chains (group reviews, Evidence verdicts, Investigator calls) verified together; **external checkpoints** (2026-10-11): length + head hash per chain in a file kept outside the data folder, optional HMAC, detects tail deletion and database replacement | Operator routine for storing checkpoints (where, how often); backup/recovery; production audit controls |
| Unified cross-domain severity | **DCG-DECISION-v2 implemented** (most severe member, +1 level for a known mechanism within 10 min; chosen on dev split, test split +0.51 genuine-share difference, CI +0.08 to +0.88; author labels) | Re-run `decision_v2_validation.py` on the teammates' independent labels; add severity labels to validate MEDIUM vs LOW ordering; more 3+-event test groups |
| Single-event severity (all domains) | **DCG-DECISION-v2 policy** (operator-approved, conservative; not data-validated) | Operator/stakeholder review of the levels; consider detector-strength grading |
| Single-event specialists (all domains) | **Implemented** 2026-10-11: consented, administrator-only evaluation for any single Evidence record; saved with an Evidence/verdict fingerprint (outdated flag) | Live OpenAI check by the operator |
| AI Investigator | **Implemented research prototype**; numeric/identity field checks; sentence-level claim checks (boundary + state claims); outbound minimization; hash-chained call audit | Evaluate the claim checker on real answers (precision/recall), abstention evaluation, prompt-injection evaluation, cost limits and production hardening; see [AI Investigator](AI_INVESTIGATOR.md) |
| Probabilistic correlation (Bayesian) | **Research component:** labelled-scenario evaluation with bootstrap confidence intervals, blind labelling pack, contract tests; display-only P(Related) beside each dashboard pair | Independent labelling by teammates (pack ready), TimeGap conditioned on Topology for slow cascades, validation on independent labels before any non-display use; see [Uncertainty Reasoning](UNCERTAINTY_REASONING.md) |
| Deployment / production security | Pending | Production authentication, TLS, secrets, monitoring, dependency audit, threat modeling, penetration tests |

## Testing modernization (agreed 2026-10-11)

Keep every existing check; reorganize them. Tracked with status in [Work Log — Testing plan](WORK_LOG.md#testing-plan-agreed-2026-10-11): GitHub Actions for fast tests, move exploration scripts out of `tests/`, pytest pilot for Reasoning graph/correlation with shared Neo4j fixtures and markers, Playwright browser tests for key review flows, then remaining script conversions.

## Suggested order (refreshed 2026-10-12)

Done since 2026-10-11: live specialist check, single-event specialists, API access matrix and policy decisions, Investigator claim checks / privacy / pseudonyms / call audit, external audit checkpoints, accessibility scan, `main` branch protection with required CI.

1. **Independent labelling round** (pack in `reasoning/uncertainty/labelling/pack/`): teammates label; then re-run `evaluate.py` and `decision_v2_validation.py`. Validates both the Bayesian study and the Decision v2 group rule. Consider a severity column to validate MEDIUM vs LOW.
2. ~~First live runs~~ (done 2026-10-12; found and fixed three issues). Safety knowledge fixed 2026-10-12 (CFR section boundaries; PPE specialist now grounded). Abstention recalibrated (threshold unchanged). Claim checker measured 2026-10-12: holdout recall 0/3, no false alarms. Instruction tightening tested 2026-10-12 (blind before/after): no measurable effect (2/20 vs 3/20). Next: a check after generation (hold back answers with presence/cause/absence claims, or a label-validated model judge), measured on new questions.
3. ~~Review lifecycle~~ (done 2026-10-12, default policy `DCG-LIFECYCLE-v1`, operator-adjustable): open → in review → resolved, reopen; automatic reopen when Evidence or verdicts change; hash-chained.
4. **Testing plan item 5** (in progress): Response agents and integration converted (49 tests); Response RAG, Reasoning and Evidence scripts remain.
5. ~~Operations routines~~ (done 2026-10-12: backup + restore check, routine table in VALIDATION_AND_OPERATIONS, keyboard-only test). Remaining: the operator picks the backup and checkpoint locations; a manual screen-reader pass.
6. **Production readiness** (design done 2026-10-12, [Production Readiness](PRODUCTION_READINESS.md)): the operator decides identity provider, database, image storage and whether real Evidence may go to OpenAI; then OIDC, PostgreSQL/object storage, containers behind a TLS proxy, and the **independent security review** (scope in the document). Security headers and the OpenAI rate limit are in place.

## Acceptance rules

- Never reinterpret contextual correlation as verified identity, causation, or physical presence.
- Group severity (DCG-DECISION-v2) is shown as "validated on author labels; independent labels pending" until the independent labelling round confirms it; never derive it from specialist or standalone severity. Single-event v2 severities are policy, not data-validated.
- Do not replace original detector output with agent-generated conclusions.
- Do not claim human review resolution solely from a recorded follow-up outcome.
- Treat local test results as revision-specific and rerun after code changes.
