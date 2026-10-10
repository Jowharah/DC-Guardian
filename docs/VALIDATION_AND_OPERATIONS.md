# DC-GUARDIAN — Validation and local operations

**Updated:** 2026-10-10  
**Branch:** `feature/presentation-dashboard`

## Environment

The validated local development workflow uses Windows PowerShell, a Python 3.12 virtual environment, FastAPI, SQLite, Neo4j for graph-dependent operations, and React/TypeScript/Vite.

Use the repository-level `requirements.txt` and `presentation/frontend/package.json` for dependencies. Do not commit private enrollment, biometric images, credentials, model artifacts, or `dcg-private` ingestion state.

## Local update and checks

From the repository root:

```powershell
git pull --ff-only origin feature/presentation-dashboard
python verify_runtime.py
python verify_dc_guardian_pipeline.py
python reasoning/run_contract_tests.py
python -m pytest presentation/backend/tests -q
cd presentation/frontend
npm run build
npm run dev
```

The full test suite and build are **recommended verification commands**, not claims of a fresh successful run on this branch. Some checks require installed model dependencies, private artifacts, a running Neo4j instance, or configured credentials.

For a focused review/audit check:

```powershell
python -m pytest presentation/backend/tests/test_human_review_api_security.py presentation/backend/tests/test_human_review_audit.py presentation/backend/tests/test_review_integrity.py presentation/backend/tests/test_review_integrity_access.py -q
```

**Reported local result (2026-10-10):** 16 passed in 0.17s. Other reported local runs: 11 passed for audit-integrity and review-audit tests after the append guard, 23 passed for earlier human-review/Decision/security contract groups, and successful Vite builds at prior development milestones. These runs are snapshots of their respective revisions, not a blanket claim that the entire suite passes today.

## Consolidated HTTP security regression — 2026-10-10

**Reported local PowerShell result:** **46 passed, 1 warning in 0.42s**. The user ran this combined command on `feature/presentation-dashboard`:

```powershell
python -m pytest presentation/backend/tests/test_image_http_rbac.py presentation/backend/tests/test_domain_feed_http_rbac.py presentation/backend/tests/test_review_http_rbac.py presentation/backend/tests/test_human_review_api_security.py presentation/backend/tests/test_human_review_audit.py presentation/backend/tests/test_review_integrity.py presentation/backend/tests/test_review_integrity_access.py -q
```

Coverage includes PPE/Face image authentication, response headers and zone isolation; SSH/Maintenance/Environmental feed RBAC and zone filtering; human-review HTTP authentication, reviewer identity and audit-history access; audit-chain verification, mutation detection, and rejection of appends to an inconsistent chain.

**Warning:** `StarletteDeprecationWarning` in FastAPI TestClient regarding `httpx` / `httpx2`. This was non-fatal; review framework compatibility before changing dependencies.

**Boundary:** These are isolated targeted regression tests with stubbed model/database inputs where appropriate. They do not establish complete production security, live multi-user penetration testing, or independent audit tamper resistance. Re-run on subsequent revisions.

## Local controlled ingestion

A previously used workflow:

```powershell
python -m presentation.backend.app.continuous_ingestion --config "C:\Users\<USER>\Documents\dcg-private\ingestion.json" --state "C:\Users\<USER>\Documents\dcg-private\ingestion_state.sqlite3"
```

The local reset tool supports a dry-run report and a guarded, backed-up execution mode. **Never run reset on production or shared Evidence.** Resetting presentation/ingestion test state is unnecessary for normal frontend, documentation, or regression updates. Incoming source files should remain preserved.

The SSH validator expects approved OpenSSH-style records. Changing the timestamp syntax without parser support can yield zero parsed events. Historical log timestamps must not be silently replaced by controlled test timestamps.

## Dashboard verification checklist

- Monitoring Center receipt timestamps show actual ingestion/storage time; original observation/capture and specialist evaluation times remain distinct.
- Unified graphs show only existing Neo4j edges, even when Person/Zone nodes are shown independently.
- PPE and Face results remain separate from person-to-PPE association and physical presence.
- Correlation candidates never inherit standalone Decision severity.
- Human Review Queue distinguishes pending source review, provisional unified review, saved Decision review, and recorded human outcomes.
- Analytics time filters use receipt timestamps; authorized feed limits and RBAC can change counts.
- Audit integrity `PASS` checks only local chain consistency.

## Review and integrity API contracts

- `GET /api/v1/correlations/unified/{group_id}/review-decision`: deterministic provisional review of saved grounded specialists.
- `GET /api/v1/reviews/unified/{group_id}/records`: authorized historical human reviews.
- `POST /api/v1/reviews/unified/{group_id}/records`: authorized reviewer outcome, rationale, acknowledgment; original Evidence/Decision unchanged.
- `GET /api/v1/reviews/audit-integrity`: administrator-only full local chain verification.

Do not infer review completion from a deterministic `EVIDENCE_REVIEW_REQUIRED` result. A saved `NEEDS_FOLLOW_UP` is not an investigation resolution.

## Local Git hygiene

`git status --short` uses `??` for untracked files. Review contents before staging; do not use `git add .` blindly when local private datasets or credentials may exist. Generated logs and `tsconfig.tsbuildinfo` are typically ignored; `package-lock.json` may be worth tracking after reviewing dependency policy. Local `phase1/` contents must be inspected before committing.

## Known limitations

- No production-grade session management, independent audit anchoring, or external checkpoint.
- No verified live camera identity or timestamp attestation for controlled image observations.
- No validated unified severity policy or autonomous remediation.
- AI Investigator chat and tools remain disabled.
- Full penetration testing, load testing, deployment hardening, and end-to-end multi-user authorization validation remain outstanding.
