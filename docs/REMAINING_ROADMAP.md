# DC-GUARDIAN — Remaining development roadmap

**Updated:** 2026-10-11. Status reflects observed code and reported local tests on `main`, not production readiness.

| Feature | Status | Remaining work |
|---|---|---|
| Severity colors and dashboard consistency | Implemented; targeted UI checks performed | Broader accessibility, contrast, responsive regression |
| Live-time synthetic events | Partial / controlled validators available | End-to-end time provenance and live simulation verification |
| SSH raw logs, usernames and source IPs | Detector Evidence and metadata implemented | Decide governed raw-log retention policy; currently raw logs intentionally not retained |
| PPE image upload and annotated detections | Implemented and demonstrated | Protected artifact-access and detector/association regression |
| Face recognition Evidence and zone authorization | Implemented and demonstrated | Enrollment privacy, zone access and identity-review hardening |
| SMART measurements and server health history | Implemented and demonstrated | Longitudinal reliability, edge cases and UI tests |
| Environmental measurements and trends | Implemented and demonstrated | Sensor data validation, temporal handling and UI tests |
| RBAC-protected Evidence artifact access | **Access matrix test** (2026-10-11) covers all 99 operations × every role (401 without credentials, 403 exactly where a permission is missing); zone isolation with real records in the domain RBAC tests | Operator decisions on two policy differences (below); multi-user integration testing |
| Analytics and interactive drill-down | Implemented; detector outcomes per domain with human verdicts, Decision severity from one shared per-row rule; Playwright test | Additional chart and filter regression |
| Monitoring Center summary | Implemented 2026-10-11: live/delayed/offline status, Needs attention, abnormal results, correlations, Decisions by level, domain freshness strip, card filters; Playwright test | Accessibility review |
| Human Review Queue and saved outcomes | Implemented and locally demonstrated | Multi-review lifecycle policy and investigation resolution contract |
| Human verdicts on individual Evidence (confirm / override / inconclusive) | Implemented; backend and Playwright browser tests; v2 single-event Decisions follow verdicts (cleared → no severity, override → human status) | Policy for who may override which domain in production; reporting overrides as model false-positive/negative metrics |
| Audit hash-chain verification | Implemented; local 11-test and 16-test runs reported | Trusted external checkpoint, backup/recovery and production audit controls |
| Unified cross-domain severity | **DCG-DECISION-v2 implemented** (most severe member, +1 level for a known mechanism within 10 min; chosen on dev split, test split +0.51 genuine-share difference, CI +0.08 to +0.88; author labels) | Re-run `decision_v2_validation.py` on the teammates' independent labels; add severity labels to validate MEDIUM vs LOW ordering; more 3+-event test groups |
| Single-event severity (all domains) | **DCG-DECISION-v2 policy** (operator-approved, conservative; not data-validated) | Operator/stakeholder review of the levels; consider detector-strength grading |
| Single-event specialists (all domains) | **Implemented** 2026-10-11: consented, administrator-only evaluation for any single Evidence record; saved with an Evidence/verdict fingerprint (outdated flag) | Live OpenAI check by the operator |
| AI Investigator | **Implemented research prototype**; numeric/identity field checks; sentence-level claim checks (boundary + state claims); outbound minimization; hash-chained call audit | Evaluate the claim checker on real answers (precision/recall), abstention evaluation, prompt-injection evaluation, decisions on SSH usernames/IPs and person IDs leaving the system, cost limits and production hardening; see [AI Investigator](AI_INVESTIGATOR.md) |
| Probabilistic correlation (Bayesian) | **Research component:** labelled-scenario evaluation with bootstrap confidence intervals, blind labelling pack, contract tests; display-only P(Related) beside each dashboard pair | Independent labelling by teammates (pack ready), TimeGap conditioned on Topology for slow cascades, validation on independent labels before any non-display use; see [Uncertainty Reasoning](UNCERTAINTY_REASONING.md) |
| Deployment / production security | Pending | Production authentication, TLS, secrets, monitoring, dependency audit, threat modeling, penetration tests |

## Testing modernization (agreed 2026-10-11)

Keep every existing check; reorganize them. Tracked with status in [Work Log — Testing plan](WORK_LOG.md#testing-plan-agreed-2026-10-11): GitHub Actions for fast tests, move exploration scripts out of `tests/`, pytest pilot for Reasoning graph/correlation with shared Neo4j fixtures and markers, Playwright browser tests for key review flows, then remaining script conversions.

## Suggested order (refreshed 2026-10-11)

1. **Independent labelling round** (pack ready in `reasoning/uncertainty/labelling/pack/`): it now validates two things at once, the Bayesian correlation study and the Decision v2 group rule. Then re-run `evaluate.py` and `decision_v2_validation.py` on those labels.
2. **Live checks of today's changes:** restart the backend, re-run the specialists on the operator-cleared group (sends Evidence to OpenAI; operator consent), confirm `logs/errors.log` is clean.
3. ~~Single-event specialists~~ (done 2026-10-11).
4. ~~API authorization matrix~~ (done 2026-10-11; two policy questions open: who may read maintenance/environment feeds, who may upload PPE/Face images).
5. Testing plan item 5: convert the remaining script tests after the pytest pilot is reviewed; branch protection on `main` (CI required).
6. ~~AI Investigator claim checks, privacy review, call audit~~ (done 2026-10-11; next: measure the claim checker on real answers).
7. Review lifecycle, audit external checkpoint, failure/recovery; dashboard accessibility.
8. Production deployment design and independent security review.

## Acceptance rules

- Never reinterpret contextual correlation as verified identity, causation, or physical presence.
- Group severity (DCG-DECISION-v2) is shown as "validated on author labels; independent labels pending" until the independent labelling round confirms it; never derive it from specialist or standalone severity. Single-event v2 severities are policy, not data-validated.
- Do not replace original detector output with agent-generated conclusions.
- Do not claim human review resolution solely from a recorded follow-up outcome.
- Treat local test results as revision-specific and rerun after code changes.
