# DC-GUARDIAN documentation index

**Updated:** 2026-10-10  
**Scope:** `feature/presentation-dashboard` research prototype; controlled/synthetic demonstration, not production certification.

Start with [Project Development History](PROJECT_DEVELOPMENT_HISTORY.md) for what has been implemented, [Validation and Operations](VALIDATION_AND_OPERATIONS.md) for reproducible commands and tested boundaries, and [Remaining Roadmap](REMAINING_ROADMAP.md) for open work.

## Existing reference documents

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
4. **Saved Decision severity** applies only when an explicit validated policy assigns it. Unified evidence review does not inherit SSH/operational severity.
5. **Human review outcomes** are authenticated operator records, not incident resolution or changes to frozen Evidence.
6. **Audit integrity PASS** verifies local record/hash consistency only; an independent checkpoint is needed to detect database replacement or deletion of the trailing suffix.

This index describes the current branch and includes local validation results reported during development. It does not imply that every endpoint, browser workflow, or deployment mode has been independently tested.
