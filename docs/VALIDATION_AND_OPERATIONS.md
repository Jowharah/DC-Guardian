# DC-GUARDIAN — Validation and local operations

**Updated:** 2026-10-10  
**Branch:** `main`

## Environment

The validated local development workflow uses Windows PowerShell, a Python 3.12 virtual environment, FastAPI, SQLite, Neo4j for graph-dependent operations, and React/TypeScript/Vite.

Use the repository-level `requirements.txt` and `presentation/frontend/package.json` for dependencies. Do not commit private enrollment, biometric images, credentials, model artifacts, or `dcg-private` ingestion state.

## Local update and checks

From the repository root:

```powershell
git pull --ff-only origin main
python check_all.py          # every layer below in one run; report in logs/checks/latest.md
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

## AI Investigator validation — 2026-10-10

**Reported local result:** **23 passed in 0.23s**, covering source manifests, history, unified context, OpenAI feature-gate behavior, operational correlations and single-source retrieval.

```powershell
python -m pytest presentation/backend/tests/test_investigator_sources.py presentation/backend/tests/test_investigator_history.py presentation/backend/tests/test_investigator_tools.py presentation/backend/tests/test_investigator_chat.py presentation/backend/tests/test_investigator_operations.py presentation/backend/tests/test_investigator_single_evidence.py -q
```

Browser demonstrations included live OpenAI responses for unified, operational, and individual SSH Evidence, as well as opt-in history restoration. The latest frontend build and full end-to-end security suite have not been confirmed by this test result. See [AI Investigator](AI_INVESTIGATOR.md).

## Full project check — 2026-10-12

`python check_all.py`: **54 passed, 0 failed, 0 skipped** — backend pytest 372 (including the 99-operation access matrix, claim checks, privacy/pseudonym and audit-checkpoint tests), frontend build, Playwright 11 browser tests (including the WCAG A/AA scans), live API GET smoke test with 0 server errors. Report: `logs/checks/20261012-090248/report.md` (local, not committed). Previous run (2026-10-11, after Decision Rules v2): 54/54 with 327 backend and 8 browser tests.

## Operations routine (2026-10-12)

**Backup folder** (operator choice): `C:\Users\Aljawharah\Documents\DC-Guardian Backup`, set as `DCG_BACKUP_DIR` in `.env`.
- Backups go to `backups\` and checkpoints to `checkpoints\`, so `--out-dir` can be left out.
- First backup and checkpoint written and verified 2026-10-12: 28 tables, 65 nodes / 69 relationships, four chains PASS, 29 MB.
- Moving `checkpoints\` to a second drive (USB, OneDrive) makes the checkpoints stronger evidence against database replacement.

Short form:

```powershell
python -m presentation.backend.app.backup create --state C:\Users\Aljawharah\Documents\dcg-private\ingestion_state.sqlite3
python -m presentation.backend.app.backup verify --backup "<folder printed by create>"
python -m presentation.backend.app.audit_checkpoint write
```

| When | Do | Command |
|---|---|---|
| Daily, and before any reset or upgrade | Back up the local data to encrypted storage outside the repository | `python -m presentation.backend.app.backup create --out-dir <encrypted folder> --state <path to ingestion_state.sqlite3>` |
| After each backup | Check that it could be restored | `python -m presentation.backend.app.backup verify --backup <folder>` |
| Daily, and after each review session | Write an audit checkpoint to separate media the database operator cannot change | `python -m presentation.backend.app.audit_checkpoint write --out-dir <other media>` |
| Weekly | Verify against the latest checkpoint | `python -m presentation.backend.app.audit_checkpoint verify --file <checkpoint.json>` |
| Before a demo or after a change | Full check | `python check_all.py` |

**What a backup contains** (`presentation/backend/app/backup.py`):
- a consistent copy of the presentation database, made with SQLite's online backup, so the backend can keep running;
- the ingestion state, when given;
- retained PPE and Face images;
- a read-only export of the Neo4j graph (`graph.jsonl`);
- a manifest with SHA-256 hashes, row counts and the audit chains' head hashes.

`verify` checks the hashes, runs SQLite's integrity check and verifies every audit chain inside the copy, on a scratch copy so the backup stays unchanged.

A trial on the operator's data (2026-10-12) produced 27 tables, a 65-node / 69-relationship graph export and four PASS chains, 29 MB in total; verify PASS.

**Restore** (stop the backend and ingestion first):
1. Keep the current `incidents.sqlite3` aside.
2. Copy `presentation.sqlite3` back as `presentation/backend/data/incidents.sqlite3`, and the image folders beside it.
3. For the graph, prefer `neo4j-admin database dump` / `load` with Neo4j stopped; `graph.jsonl` is the fallback record.
4. Run `check_all.py` and the audit-integrity check.

Backups contain private Evidence, including face images: keep them encrypted, never commit them, and delete old ones on a retention schedule the operator sets.

**Keyboard and screen-reader review:**
- automated: `e2e/keyboard.spec.ts` (sign-in, feed, opening an event and the investigation controls with the keyboard alone, with a visible focus indicator) and `e2e/accessibility.spec.ts` (WCAG A/AA);
- still manual: a pass with a screen reader (NVDA or Narrator) through the Monitoring Center, Review Queue and an investigation.

## Audit checkpoints — 2026-10-11

The audit chains detect edited records; a checkpoint also detects deleted recent records and a replaced database. Keep checkpoint files **outside** `presentation/backend/data/` (the tool refuses otherwise), on media or in a place the database operator cannot alter:

```powershell
python -m presentation.backend.app.audit_checkpoint write --out-dir E:\dcg-checkpoints
python -m presentation.backend.app.audit_checkpoint verify --file E:\dcg-checkpoints\dcg-audit-checkpoint-<time>.json
```

Optional: set `DCG_CHECKPOINT_KEY` (kept out of the repository) to sign checkpoints with HMAC-SHA256, so a forged checkpoint is rejected. Verification reports each chain's records added since the checkpoint; anything added after the latest checkpoint is covered only by the next one.

## API access matrix — 2026-10-11

`presentation/backend/tests/test_access_matrix.py` lists every operation from the OpenAPI schema (99; 147 calls with each `{kind}` expanded) in a reviewed `POLICY` table and checks, with a throw-away database, unreachable Neo4j and OpenAI blocked: every operation except `/health` answers 401 without credentials; each non-admin role gets 403 exactly where it lacks the required permission and is not refused where it holds it. A new endpoint fails the test until classified. Zone isolation with real records stays in the domain RBAC tests. Policy (operator decisions 2026-10-12): every domain feed needs that domain's detail permission (maintenance/environment feeds were open to every role before); each domain's operator uploads and runs the pipeline for its own domain (security operators: SSH logs, safety operators: PPE/Face images, operations engineers: maintenance/environment), where maintenance/environment/SSH previously required `scenario:execute`. Declaring controlled metadata (SSH controlled time, image capture declarations), cross-domain views, unified groups and specialist evaluations stay administrator-only.

## Decision Rules v2 validation — 2026-10-11

`python presentation/backend/validation/decision_v2_validation.py` reproduces the dev-split selection and the single test-split evaluation of the group linkage rule (`results/decision_v2_validation.md`): escalated groups 89% genuine vs 38% (difference +0.51, 95% CI +0.08 to +0.88, scenario bootstrap). Author labels; see [AI Investigator — Decision Rules v2](AI_INVESTIGATOR.md#decision-rules-v2-2026-10-11).

## Full project check and logs — 2026-10-10

`python check_all.py` runs every layer and writes `logs/checks/<timestamp>/report.md`. Reported local run on this branch: **50 passed, 1 failed, 0 skipped** — runtime 4/4; Evidence 28/29; Reasoning 24/24 (contract-test graph nodes removed afterwards); Response 15/15; Decision/integration 4/4; Presentation backend 305 tests; frontend build; live API 54 GET requests with 0 server errors. The one failure is local data, not code: the private Face `validation_known/P005` folder is empty (expected 1 image).

Fixed during this check: a stale PPE final-test assertion (the compliance policy was frozen after the locked detector evaluation; separation is now asserted on the evaluation record) and a stale integration service test (the service has applied Decision Rules v1 since `d4cb326`).

The backend logs requests (method, path, status, duration), application messages and errors with tracebacks to `logs/`. Bodies, headers, credentials and query strings are never logged; HTTP client libraries are limited to warnings so outgoing URLs are not recorded.

## Continuous integration

`.github/workflows/ci.yml` runs `check_all.py --skip-live` (with a CI-only Neo4j container) and the frontend build on every push and pull request. GPU-environment, private-data and locally rebuilt RAG checks are skipped with a reason; the full 51-check run requires the local machine. See [Work Log](WORK_LOG.md).

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

`git status --short` uses `??` for untracked files. Review contents before staging; do not use `git add .` blindly when local private datasets or credentials may exist. `tsconfig.tsbuildinfo` and build logs are ignored; `presentation/frontend/package-lock.json` is tracked for reproducible installs.

The Presentation backend tests isolate all storage in a temporary `DCG_PRESENTATION_DB`. `reasoning/run_contract_tests.py` writes contract data to the configured Neo4j database and removes `SCENARIO-*` Event/Correlation nodes after the suite (set `DCG_KEEP_TEST_GRAPH=1` to keep them for debugging).

## Known limitations

- No production-grade session management, independent audit anchoring, or external checkpoint.
- No verified live camera identity or timestamp attestation for controlled image observations.
- Unified group severity uses a provisional, not yet validated deterministic policy; no autonomous remediation.
- AI Investigator chat and tools remain disabled.
- Full penetration testing, load testing, deployment hardening, and end-to-end multi-user authorization validation remain outstanding.
