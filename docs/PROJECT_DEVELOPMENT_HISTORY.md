# DC-GUARDIAN — Development history and current implementation

**Snapshot:** 2026-10-10, `feature/presentation-dashboard`  
**Purpose:** consolidate earlier model, reasoning, response, decision, presentation, and security stages without rewriting historical validation reports.

## Architecture

```text
Evidence: SSH | PPE | Face | SMART | Environmental
  -> Common Event Schema and topology mapping
  -> Neo4j mapped Evidence and infrastructure relationships
  -> Deterministic correlation candidates
  -> Approved-knowledge RAG + domain-scoped specialist assessments
  -> Deterministic Decisions / provisional unified evidence review
  -> Monitoring Center / Analytics / Human Review Queue
  -> Audited human reviewer outcomes (separate from Evidence/Decision)
```

**New stage — AI Investigator (October 2026):** The presentation now supports an opt-in OpenAI Responses API Investigator over existing unified, operational, and individual five-domain Evidence; expand/collapse chat; safe domain-colored response formatting; operator-scoped, opt-in SQLite history; and deterministic source-reference manifests. The Investigator does not assign severity or create correlations. Source manifests are not claim-level verification. See [AI Investigator](AI_INVESTIGATOR.md) for endpoint contracts and limitations.

**Scope:** a controlled research prototype. Data may be synthetic, operator-declared, historical, or unverified. Autonomous action is disabled.

## Stage 1 — Frozen Evidence baselines

| Domain | Implementation | Boundaries |
|---|---|---|
| Cybersecurity | Frozen SSH detector; OpenSSH parsing, source-IP/five-minute windows, anomaly metrics and votes | Raw SSH logs are not retained by the validated presentation workflow; original timestamps are preserved; contextual test time is explicitly unverified. |
| Safety | YOLO-based PPE image inference, stored image observations, annotated detections, per-person helmet/vest policy results | A missing detection is not proof of physical absence; no identity-to-PPE association is assumed. |
| Physical security | RetinaFace/ArcFace controlled face recognition, private local enrollment, Neo4j read-only zone authorization | Recognition is distinct from authorization and does not prove entry or physical presence. |
| Predictive maintenance | Temporal RF v2; SMART-history validation and seven-day risk estimates | Risk scores are predictions, not guaranteed failures or exact failure dates. |
| Environmental | Timestamped sensor CSV and deterministic threshold assessment | Sensor anomalies alone do not establish damage or cause. |

The individual Evidence component READMEs remain the authoritative detailed model references.

## Stage 2 — Reasoning and correlation

- Common Event Schema, controlled DC-01 topology, Neo4j Evidence projection, source references, and infrastructure graph viewers.
- Explicit environmental + maintenance zone/time correlation and controlled PPE + Face and Face + SSH contextual candidates.
- Unified grouping of connected source candidates into multi-domain investigations without fabricating pairwise edges.
- Person and Zone nodes can appear in a unified graph without an `AUTHORIZED_FOR` edge. An unconnected Person is not proof of physical presence.
- Idempotent ingestion/state handling and a guarded local-test reset utility; original incoming source files are preserved by the reset workflow.
- Operator-declared camera/capture metadata is labeled unverified. SSH original log time and controlled context time remain separate.

## Stage 3 — Response and deterministic Decision

- Governed approved-source RAG, local sentence-transformer retrieval, domain-scoped specialist agents, grounding/citation limitations, and specialist synthesis.
- Standalone SSH and environmental + maintenance supported Decision workflows can assign policy-based severity and human review.
- Unified multi-domain investigations use `DCG-UNIFIED-EVIDENCE-REVIEW-v1`: provisional review reasons, **no unified severity**, no autonomous action.
- A recognized person whose independent graph check returns unauthorized for a declared zone can trigger `RECOGNIZED_IDENTITY_NOT_AUTHORIZED_FOR_DECLARED_ZONE`; this does not establish entry, wrongdoing, or SSH attribution.
- Saved Face + SSH specialist assessments and unified specialist results can be reopened and re-evaluated; historical source assessments are preserved.

See [Response Architecture and Validation](DC_Guardian_Response_Architecture_and_Validation.md) for earlier Response-stage evaluation details.

## Stage 4 — Presentation and Scenario Lab

React + TypeScript + Vite frontend, FastAPI backend, SQLite presentation state, Neo4j read-only graph retrieval.

- **Monitoring Center:** original Evidence viewers, received/observed/evaluated timestamps, graph topology, correlation candidates, saved specialist assessments and Decisions.
- **Scenario Lab:** controlled validators for SSH logs, SMART CSV, sensor CSV, PPE images, and Face images; camera/time declaration where supported; controlled synthetic event tools.
- **Analytics Dashboard:** domain distribution, saved severity, zone distribution, multi-domain groups, receipt-time filtering, activity counts, review/workflow charts, and click-through record drill-down.
- **Human Review Queue:** source-review status, unified candidates, deterministic review requirements, saved Decision review requirements, and recorded human outcomes.
- **Audit UI:** administrator-triggered local hash-chain integrity verification.
- **AI Investigator sidebar:** currently a disabled placeholder; approved read-only tools and grounded chat are not connected.

## Stage 5 — Human oversight and security

- RBAC and zone-scoped Evidence access; local HTTP Basic prototype identity adapter (not a production identity/session system).
- Authenticated, append-only local human review records with rationale, outcome, timestamps, policy version, Evidence signature, and chained hashes.
- Supported human outcomes: `INCONCLUSIVE`, `NEEDS_FOLLOW_UP`, `REVIEWED_NO_FINDING`.
- Audit verifier detects modified entries and broken intermediate links; backend blocks further append when local verification fails.
- Global audit-integrity endpoint is administrator-only. Reviewer identity is server-derived.
- A recorded `NEEDS_FOLLOW_UP` remains outstanding; no outcome silently changes Evidence or unified Decision severity.

**Security limitations:** SQLite audit hashes are not independently anchored; local credentials and a controlled synthetic topology are not production security controls. See [Security Assessment and Hardening](DC_Guardian_Security_Assessment_and_Hardening.md) for the earlier scoped baseline and [Remaining Roadmap](REMAINING_ROADMAP.md) for outstanding work.

## Demonstrated local scenario results (not universal acceptance tests)

- ZONE-A: SSH anomaly + recognized P005 unauthorized for ZONE-A + PPE person-level results, grouped as a three-domain controlled candidate. No SSH actor attribution or verified PPE-person association.
- ZONE-B: controlled unified three-domain candidate and an environmental + maintenance correlation with a saved MEDIUM operational Decision.
- Dashboard observations during October 2026 testing included 8 source Evidence records, 2 unified candidates, 3 saved medium/high Decisions, and 1 recorded human `NEEDS_FOLLOW_UP` outcome. These are **time-specific local test data**, not permanent expected counts.

See [Validation and Operations](VALIDATION_AND_OPERATIONS.md) for the latest reported regression results and commands.
