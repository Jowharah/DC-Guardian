# DC-GUARDIAN documentation index

**Updated:** 2026-10-11  
**Scope:** DC-GUARDIAN research prototype on `main`; controlled/synthetic demonstration, not production certification.

For the current OpenAI-powered investigation feature, see [AI Investigator](AI_INVESTIGATOR.md) (all five Evidence domains, correlations, conversation history, source manifests, privacy and grounding limitations).

Start with [Project Development History](PROJECT_DEVELOPMENT_HISTORY.md) for what has been implemented, the [Work Log](WORK_LOG.md) for dated changes, commits and the agreed testing plan, [Validation and Operations](VALIDATION_AND_OPERATIONS.md) for reproducible commands and tested boundaries, and [Remaining Roadmap](REMAINING_ROADMAP.md) for open work.

Working on the repository with Claude Code: see [`CLAUDE.md`](../CLAUDE.md) at the repository root for rules, commands and conventions.

## Existing reference documents

- [Installation and User Guide](INSTALLATION_AND_USER_GUIDE.md) — install on a new Windows computer with `setup.ps1` (CPU is enough), demo data, a first tour, optional GPU/face/OpenAI features, the dashboard screens, troubleshooting. Also the report's installation appendix.
- [Report draft: evaluation against single-domain monitoring, and latency](report/evaluation_baseline_and_latency.md) — answers the proposal's research question on the labelled scenarios (held-out test split, bootstrap intervals) and reports per-stage pipeline latency.
- [Report draft: PPE detector v2](report/ppe_v2_model_enhancement.md) — model enhancement: protocol, validation selection, the official locked test (helmet and overall improved, vest regressed) and the post-hoc evaluation of all candidates.
- [Report draft: industrial deployment considerations](report/industrial_deployment_considerations.md) — section for the project report: controls in place and how they were verified, production requirements, threat-model summary, limitations.
- [Usability study kit](usability_study/README.md) — protocol, facilitator script, task cards, answer key, observation sheet, questionnaire (SUS, concept check, trust) and results template; scored with `presentation/backend/validation/usability_score.py`.
- [Datasets and Citations](DATASETS_AND_CITATIONS.md) — every dataset, pretrained model and knowledge source used, with the citation and licence terms each requires (BibTeX), and what the terms mean for academic versus commercial use.
- [Testing](TESTING.md) — what each test suite covers, markers and automatic skips, commands, how the script tests were converted to pytest and shown to be equivalent, how to write new tests.
- [Production Readiness](PRODUCTION_READINESS.md) — what must change before real data or multiple users: target deployment, decisions to make, STRIDE threat model with existing controls and gaps, scope for the independent security review.
- [Development Workflow](DEVELOPMENT_WORKFLOW.md) — how changes reach `main` (protected branch, pull requests, merge commits), reading CI failures, GitHub CLI, and the operator PC setup (Kaspersky certificate fix for Node tools and `claude rc`).
- [Uncertainty Reasoning](UNCERTAINTY_REASONING.md) — Bayesian cross-domain correlation, expert knowledge base, labelled scenarios and evaluation against the crisp rule.
- [Response Architecture and Validation](DC_Guardian_Response_Architecture_and_Validation.md) — approved RAG, grounded specialist reasoning, evaluation methodology, and earlier Response contracts.
- [Security Assessment and Hardening](DC_Guardian_Security_Assessment_and_Hardening.md) — **pre-dashboard** security baseline, dependency/static analysis, and residual risks. This document is historical and is not a current penetration test.
- [Repository README](../README.md) — project overview and earlier Evidence/Reasoning setup.

## Component references

- [Face Recognition](../evidence/face_recognition/README.md)
- [PPE Detection](../evidence/ppe_detection/README.md)
- [Predictive Maintenance](../evidence/predictive_maintenance/README.md)
- [SSH Anomaly](../evidence/ssh_anomaly/README.md)
- [Environmental Monitoring](../evidence/environmental_monitoring/README.md)

## Important distinctions

1. **Evidence** is a detector output or operator-declared controlled test record. Detection is not independently verified physical reality.
2. **Correlation candidates** use explicit source rules and topology. Same zone/time does not establish identity, causation, compromise, or physical presence.
3. **Specialist assessments** use approved knowledge and may be partially supported. They do not override deterministic correlation or Decision authority.
4. **Decision severity** comes only from deterministic rules: DCG-DECISION-v1 (saved SSH, operational and pipeline Decisions) and DCG-DECISION-v2 (single events in every domain, and unified groups: most severe member, +1 level only for linked evidence; validated on author labels, independent labels pending). Specialists and the Investigator never assign severity; unified review does not inherit SSH/operational severity.
5. **Human review outcomes** are authenticated operator records, not incident resolution or changes to frozen Evidence.
6. **Audit integrity PASS** verifies local record/hash consistency only; an independent checkpoint is needed to detect database replacement or deletion of the trailing suffix.

This index describes the current branch and includes local validation results reported during development. It does not imply that every endpoint, browser workflow, or deployment mode has been independently tested.
