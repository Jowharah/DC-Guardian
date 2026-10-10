# DC-GUARDIAN — Remaining development roadmap

**Updated:** 2026-10-10. Status reflects observed code and reported local tests on `feature/presentation-dashboard`, not production readiness.

| Feature | Status | Remaining work |
|---|---|---|
| Severity colors and dashboard consistency | Implemented; targeted UI checks performed | Broader accessibility, contrast, responsive regression |
| Live-time synthetic events | Partial / controlled validators available | End-to-end time provenance and live simulation verification |
| SSH raw logs, usernames and source IPs | Detector Evidence and metadata implemented | Decide governed raw-log retention policy; currently raw logs intentionally not retained |
| PPE image upload and annotated detections | Implemented and demonstrated | Protected artifact-access and detector/association regression |
| Face recognition Evidence and zone authorization | Implemented and demonstrated | Enrollment privacy, zone access and identity-review hardening |
| SMART measurements and server health history | Implemented and demonstrated | Longitudinal reliability, edge cases and UI tests |
| Environmental measurements and trends | Implemented and demonstrated | Sensor data validation, temporal handling and UI tests |
| RBAC-protected Evidence artifact access | Implemented in part; regression tests passing | Full API/asset access matrix and multi-user integration testing |
| Analytics and interactive drill-down | Implemented and locally demonstrated | Additional chart and filter regression |
| Human Review Queue and saved outcomes | Implemented and locally demonstrated | Multi-review lifecycle policy and investigation resolution contract |
| Human verdicts on individual Evidence (confirm / override / inconclusive) | Implemented; focused tests and copy-database HTTP check | Browser validation; policy for who may override which domain in production; reporting overrides as model false-positive/negative metrics; Decision re-evaluation for human-escalated events that never had a Decision |
| Audit hash-chain verification | Implemented; local 11-test and 16-test runs reported | Trusted external checkpoint, backup/recovery and production audit controls |
| Unified cross-domain severity | **Provisional policy implemented** (`DCG-UNIFIED-SEVERITY-PROVISIONAL-v1`: Decision Rules v1 on active-concern member domains) | Validate the policy against labelled multi-domain scenarios and approve it before treating group severity as authoritative |
| AI Investigator | **Implemented research prototype**; numeric/identity field checks for all domains and modes | Narrative/causal claim grounding, abstention evaluation, outbound privacy review, tool audit, prompt-injection evaluation, cost limits and production hardening; see [AI Investigator](AI_INVESTIGATOR.md) |
| Deployment / production security | Pending | Production authentication, TLS, secrets, monitoring, dependency audit, threat modeling, penetration tests |

## Suggested order

1. Full API authorization and protected artifact-access regression; browser-level end-to-end test.
2. Review lifecycle, audit integrity external checkpoint design, and failure/recovery handling.
3. AI Investigator **claim-level grounding**, source-field citations, privacy review, audit and authorization regression (read-only Evidence tools and source manifests are already implemented).
4. Dashboard accessibility, live-time synthetic event contracts, and multi-domain demo verification.
5. Production deployment design and independent security review.

## Acceptance rules

- Never reinterpret contextual correlation as verified identity, causation, or physical presence.
- Group severity stays labelled provisional until `DCG-UNIFIED-SEVERITY-PROVISIONAL-v1` is validated; never derive it from specialist or standalone severity.
- Do not replace original detector output with agent-generated conclusions.
- Do not claim human review resolution solely from a recorded follow-up outcome.
- Treat local test results as revision-specific and rerun after code changes.
