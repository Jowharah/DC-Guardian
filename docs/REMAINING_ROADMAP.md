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
| Unified cross-domain severity | **DCG-DECISION-v2 implemented** (most severe member, +1 level for a known mechanism within 10 min; chosen on dev split, test split +0.51 genuine-share difference, CI +0.08 to +0.88; author labels) | Independent labelling dropped (2026-10-21); stated as a limitation. Future work: independent labels, severity labels to validate MEDIUM vs LOW ordering, more 3+-event test groups |
| Single-event severity (all domains) | **DCG-DECISION-v2 policy** (operator-approved, conservative; not data-validated) | Operator/stakeholder review of the levels; consider detector-strength grading |
| Single-event specialists (all domains) | **Implemented** 2026-10-11: consented, administrator-only evaluation for any single Evidence record; saved with an Evidence/verdict fingerprint (outdated flag) | Live OpenAI check by the operator |
| AI Investigator | **Implemented research prototype**; numeric/identity field checks; sentence-level claim checks (boundary + state claims); outbound minimization; hash-chained call audit | Evaluate the claim checker on real answers (precision/recall), abstention evaluation, prompt-injection evaluation, cost limits and production hardening; see [AI Investigator](AI_INVESTIGATOR.md) |
| Probabilistic correlation (Bayesian) | **Research component:** labelled-scenario evaluation with bootstrap confidence intervals, blind labelling pack, contract tests; display-only P(Related) beside each dashboard pair | Independent labelling dropped (2026-10-21; the pack stays for future use). Future work: TimeGap conditioned on Topology for slow cascades; independent labels before any non-display use; see [Uncertainty Reasoning](UNCERTAINTY_REASONING.md) |
| Deployment / production security | Pending | Production authentication, TLS, secrets, monitoring, dependency audit, threat modeling, penetration tests |

## Testing modernization (agreed 2026-10-11)

Keep every existing check; reorganize them. Tracked with status in [Work Log — Testing plan](WORK_LOG.md#testing-plan-agreed-2026-10-11): GitHub Actions for fast tests, move exploration scripts out of `tests/`, pytest pilot for Reasoning graph/correlation with shared Neo4j fixtures and markers, Playwright browser tests for key review flows, then remaining script conversions.

## Suggested order (refreshed 2026-10-12)

Done since 2026-10-11: live specialist check, single-event specialists, API access matrix and policy decisions, Investigator claim checks / privacy / pseudonyms / call audit, external audit checkpoints, accessibility scan, `main` branch protection with required CI.

1. ~~Independent labelling round~~ **dropped 2026-10-21 (time limitation, operator decision).** The evaluations use the operator's blind v2 relabel, with ChatGPT labels as a second opinion only. Both come from or follow the author, so the result is stated as author-validated. The packs (`labelling/pack/`, `pack_v2/`) and `score_labels.py` stay for future work. Original plan: teammates label; then re-run `evaluate.py` and `decision_v2_validation.py`. Validates both the Bayesian study and the Decision v2 group rule. Consider a severity column to validate MEDIUM vs LOW.
2. ~~First live runs~~ (done 2026-10-12; found and fixed three issues). Safety knowledge fixed 2026-10-12 (CFR section boundaries; PPE specialist now grounded). Abstention recalibrated (threshold unchanged). Claim checker measured 2026-10-12: holdout recall 0/3, no false alarms. Instruction tightening tested 2026-10-12 (blind before/after): no measurable effect (2/20 vs 3/20). Model judge added 2026-10-12 (post-generation): 4/5 overclaims caught on blind test answers, 1 false alarm in 35. Next: teammates label a fresh answer set to confirm with independent labels.
3. ~~Review lifecycle~~ (done 2026-10-12, default policy `DCG-LIFECYCLE-v1`, operator-adjustable): open → in review → resolved, reopen; automatic reopen when Evidence or verdicts change; hash-chained.
4. ~~Testing plan item 5~~ (done 2026-10-12: every test under pytest, equivalence shown; see [Testing](TESTING.md)). Optional: split the 55 module-level files into one test per check.
5. ~~Operations routines~~ (done 2026-10-12: backup + restore check, routine table in VALIDATION_AND_OPERATIONS, keyboard-only test). Backup folder chosen 2026-10-12 (`Documents\DC-Guardian Backup`, `DCG_BACKUP_DIR`); first backup and checkpoint verified. Remaining: a manual screen-reader pass; optionally checkpoints on a second drive and a daily scheduled run.
6. **Production readiness** (design done 2026-10-12, [Production Readiness](PRODUCTION_READINESS.md)): the operator decides identity provider, database, image storage and whether real Evidence may go to OpenAI; then OIDC, PostgreSQL/object storage, containers behind a TLS proxy, and the **independent security review** (scope in the document). Security headers and the OpenAI rate limit are in place.
7. ~~Baseline comparison and latency~~ (done 2026-10-13; [report draft](report/evaluation_baseline_and_latency.md)):
   - correlation against isolated single-domain monitoring on the held-out scenarios: fewer alerts, higher queue average precision, incidents shown whole;
   - per-stage latency: detector start-up dominates, about 4 to 10 s per upload.
8. ~~Scenario set v2 relabelling~~ (done 2026-10-13). The 8 scenarios that used leak, smoke, airflow or cooling states the detector cannot produce were rewritten with detector-derived readings; all 40 were relabelled blind by the operator, with ChatGPT's labels of the same pack as a sensitivity check ([results](UNCERTAINTY_REASONING.md#results-on-scenario-set-v2-2026-10-13)).
   - Correlation beats isolated single-domain monitoring under every labelling.
   - The Bayesian advantage over the crisp rule is no longer statistically clear on v2 (interval includes zero).
   - The labellings disagree mainly on whether heat or humidity plus a drive at risk is one incident: item 1 (independent human labels) should settle it.
9. **Model enhancement and workflow optimisation** (proposal "optimization", operator interpretation 2026-10-13): new detector versions beside the frozen ones, selected on validation data and evaluated once on the locked test; a persistent inference worker to remove per-upload model loading.
   - **PPE-v2 done 2026-10-13** (YOLOv8s, 1024 px; see `evidence/ppe_detection/README.md`). Locked test: overall mAP@0.5 0.545 → 0.595 and helmet recall 0.603 → 0.654, but safety-vest recall 0.449 → 0.245 (49 vests; validation pointed the other way).
   - **Post-hoc** (after selection; not used to choose): on the locked test, the unselected YOLOv8m matches v1 on vests (recall 0.449, mAP 0.416 vs 0.372) and is best overall (mAP@0.5 0.625). The combined v1-vest detector was therefore not built.
   - **Runtime switched to PPE-v2m 2026-10-14** (operator decision; test-informed, recorded as such). Before switching: same frozen policy, validation compliance-status agreement 95.3% vs 94.8%, upload 4.06 s vs 3.90 s. `DCG_PPE_DETECTOR=v1` returns to PPE-v1.
   - **PPE-v3 done 2026-10-15** (SH17 + Kaggle helmet/jacket training, persons pseudo-labelled, protocol `f23f01e`): accepted on validation; final test: Kaggle helmet/vest mAP@0.5 0.962/0.958 (PPE-v2m 0.401/0.418, same-source) but on SH17 no better than PPE-v2m (all-class 0.619 vs 0.625, vest recall 0.388 vs 0.449). Runtime stays PPE-v2m.
   - Open: a fresh held-out set of data-centre-like images (ideally with compliant staff) to choose between PPE-v2m and PPE-v3 and to test false alarms.
   - **External test (2026-10-14)** on the Kaggle *Safety Helmet and Reflective Jacket* test split (1,571 images; 3,080 helmets, 2,343 vests; independent of SH17):
     - helmets favour PPE-v1 (mAP@0.5 0.495 vs v2m 0.401);
     - vests favour v2m (0.418 vs 0.368; 0.495 when run at the images' native 640 px);
     - all models are well below their SH17 figures;
     - the v2 improvement is dataset-dependent.
   - Possible next step: a PPE-v3 trained on SH17 plus this dataset, with pseudo-labelled persons; or data-centre images.
   - **Maintenance operating curve done 2026-10-14** (validation only; `evidence/predictive_maintenance/README.md`):
     - the frozen threshold 0.45 sits at a knee (about 31 extra checks per extra failure above it, about 70 below it);
     - 0.30 is the other defensible point (60% of failing drives caught vs 50%, 2.3 times as many drives flagged).
     - Operator decision 2026-10-14: keep 0.45; 0.30 is reported as the documented alternative (not deployed).
   - **Third-dataset test (CHV) done 2026-10-15** (test only):
     - PPE-v3m (PR #31) detects helmets and vests best on unseen data (vest recall 0.84 vs 0.63 for v2m);
     - for compliance it halves false alarms (31.5% vs 59.9%) but misses more violations (9.3% vs 3.2%).
     - **Operator decision 2026-10-15: the runtime stays on PPE-v2m.** It misses fewer real violations (26 vs 76 of 821 non-compliant CHV images); a missed violation raises no alert for human review, while a false alarm does. PPE-v3m is reported as the better detector. Revisit after re-tuning v3m's vest threshold on validation data and confirming it on fresh images.
   - **Persistent inference workers done 2026-10-14:** median upload SSH 7.3 → 0.56 s, PPE 7.6 → 0.60 s, Face 17.8 → 3.1 s, with identical results; `DCG_PERSISTENT_WORKERS=0` restores the old behaviour.
10. **Usability study** (proposal evaluation item; kit ready 2026-10-15, `docs/usability_study/`; pilot done 2026-10-20 with fixes; **sessions complete 2026-10-21**): 3–5 sessions with non-team participants; score with `presentation/backend/validation/usability_score.py` and add the results to the report.

## Acceptance rules

- Never reinterpret contextual correlation as verified identity, causation, or physical presence.
- Group severity (DCG-DECISION-v2) is shown as "validated on the author's labels only (no independent labelling round)"; never derive it from specialist or standalone severity. Single-event v2 severities are policy, not data-validated.
- Do not replace original detector output with agent-generated conclusions.
- Do not claim human review resolution solely from a recorded follow-up outcome.
- Treat local test results as revision-specific and rerun after code changes.
