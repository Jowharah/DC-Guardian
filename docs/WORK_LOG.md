# DC-GUARDIAN — Engineering work log

Dated record of changes on `feature/presentation-dashboard`: what changed, why, the commit, how it was verified, and known caveats. Newest first. Detailed contracts live in the linked documents; this log is the index of *what happened when*.

Conventions: commit hashes refer to `feature/presentation-dashboard`. "Verified" lists what was actually run. Local data results are time-specific, not permanent expected values.

---

## 2026-10-11 — Continuous integration and fresh-clone reproducibility

### GitHub Actions — `.github/workflows/ci.yml`

- **What:** on every push to `main` / `feature/**` and every pull request, a Python job runs `python check_all.py --skip-live` against a CI-only Neo4j 2026.08.1 container (topology loaded first with `reasoning/graph/load_topology.py`), and a frontend job runs `npm ci && npm run build`. The check report is uploaded as a build artifact.
- **Cost notes:** CPU PyTorch wheels avoid a multi-GB CUDA download. The 318 MB Git LFS model is cached between runs; GitHub's free LFS bandwidth (1 GB/month) is spent only when the model changes or the cache expires.

### Fresh clone now runs cleanly

Simulated with a clean checkout (only Git-tracked files) before enabling CI. It first showed **11 failures** that a teammate or CI would hit:

| Problem | Fix |
|---|---|
| Neo4j modules (`ingest_event`, `load_topology`, `validate_graph`) refused to start without a `.env` file, even when environment variables were set | `.env` is now optional; real environment variables take precedence; default URI `127.0.0.1` |
| Checks needing private biometric data, the processed SH17 dataset or the locally rebuilt RAG knowledge base failed | `check_all.py` reports them as SKIP with the missing path |
| Reasoning suite stopped at the Face adapter contract (private enrollment data), so later graph contracts never ran | `run_contract_tests.py` skips contracts whose private data is absent and continues |

Result on a clean checkout: **35 passed, 0 failed, 15 skipped** (each skip names its reason). Locally with all data: still 51/51 and 24/24 Reasoning contracts.

To rebuild the RAG knowledge base on a new machine: `python response/rag/fetch_sources.py`, then the parse, preprocess, chunk and `build_index.py` steps in `response/rag/` (see the Response architecture document).

### First CI runs

| Run | Result | Finding |
|---|---|---|
| 1 (`5cca0ce`) | Frontend ✓ · Python ✗ | Failure details were only in admin-only job logs |
| 2 (`637d5fb`) | Frontend ✓ · Python ✗ | `check_all.py` now emits one error annotation per failed check plus the report as the job summary. Revealed a **real cross-platform bug**: the SSH detector refused to load on Linux |
| 3 (`4d055ef`) | **Frontend ✓ · Python ✓** | Fixed |

**The bug:** the SSH detector verifies `autoencoder_log_config.json` against a frozen SHA-256 before loading. Git stored the file with LF line endings and converted it to CRLF on Windows, where the digest was frozen, so any non-Windows machine failed the integrity check. The file is now marked `-text` in `.gitattributes` and stored with its exact frozen bytes; the pinned digest is unchanged. The other integrity-checked artifacts are binary and unaffected.

**Follow-ups:** runners pinned to `ubuntu-24.04` (`ubuntu-latest` moves to Ubuntu 26 on 2026-10-19). GitHub warns that `actions/checkout@v4`, `setup-python@v5`, `cache@v4` and `upload-artifact@v4` target the deprecated Node.js 20 runtime; upgrade them when their Node 24 versions are confirmed.

### Test hygiene

- Moved `inspect_sh17_class_mapping.py` and `inspect_sh17_split_distribution.py` to `evidence/ppe_detection/tools/` (exploration scripts, not tests).

---

## 2026-10-10 / 11 — Correlation generalization, human verdicts, Investigator grounding, operations

### Summary

| Area | Before | After |
|---|---|---|
| Correlation | 3 hard-coded pair types; "unified" groups of 2+ events, SSH/Face/PPE only | Pairs for **any two events**; unified groups = **3+ events, any domains** |
| Human review | Notes only on unified groups; PPE/Face stuck in "Source review" | **Verdicts on any Evidence** (confirm / override / inconclusive), audited |
| Severity | Unchanged by humans; no group severity | Decisions **flagged and re-evaluated** on human-verified inputs; **provisional group severity** |
| Investigator | Unified + operational + single modes; numeric checks for single SSH only | Adds **pair mode**; numeric + identity checks for **all domains and modes** |
| Operations | No logs; checks scattered across scripts | `logs/` folder; `python check_all.py` runs every layer |
| Test result | Several stale/failing tests unnoticed | **51/51** checks passing |

### Correlation: any pair, groups of three or more

- **What:** `correlation_pairs.py` returns every pair in one shape (`GET /api/v1/correlations/pairs`). The 3 dedicated matchers keep their stricter rules; the other 7 domain combinations use the Reasoning-layer contract (both abnormal, different domains, same zone, within 15 minutes; SERVER scope when both name the same server). Unified groups are connected components of 3+ events. Commit `67bdfcf`, UI `c2f8fbc`.
- **Why:** the project is both research and an industrial prototype; correlation should not be limited to three combinations.
- **Caveats:** group IDs hash their membership, so a group that grows gets a new ID and needs its specialist evaluation re-run. Rack-level scope is not yet resolved.

### Investigator: pair mode and all-domain group context

- **What:** `/api/v1/investigator/pairs/{id}/ask` for any pair; unified mode now sends every member of all five domains (previously Maintenance/Environment were dropped and only one member per domain kept); one shared provider helper. Commit `c14546b`.
- **Fixed:** the reference check flagged pair IDs (which embed member Evidence IDs) as unknown.

### Human verdicts on individual Evidence

- **What:** `evidence_review.py`. Operators record CONFIRMED / OVERRIDDEN (with a human-verified status, e.g. PPE `COMPLIANT`) / INCONCLUSIVE plus a rationale, for any SSH, PPE, Face, Maintenance or Environmental Evidence. Detector output is never modified; each verdict is a hash-chained audit entry, checked by the audit-integrity endpoint. Domain operators review their own domain in their zones; viewers cannot. Commits `09113c5`, UI `5282a1c`.
- **Effect:** an override to a non-concerning status removes the event from the pair list; an override to a concerning status makes it eligible for pairing. The Investigator receives the verdict (without rationale or reviewer identity).

### Decisions after human verdicts

- **What:** `decision_reevaluation.py`. A Decision whose input a human changed is flagged "re-evaluation required"; re-evaluation re-runs Decision Rules v1 on human-verified inputs (no model call) and is appended to history. A cleared input gives **no severity** (`INPUT_CLEARED_BY_HUMAN_VERDICT`), never a guessed lower level. Commit `73b6fb1`.
- **Caveat:** escalating an event that never had a Decision does not create one yet (on roadmap).

### Groups: cleared members kept, provisional severity

- **What:** cleared members stay in their group, marked, so the group keeps its ID and review history; a group with fewer than two un-cleared members is dropped. `unified_severity.py` (`DCG-UNIFIED-SEVERITY-PROVISIONAL-v1`) applies Decision Rules v1 to active-concern member domains. Group disposition is verdict-aware; the queue shows "Member verdict changed" when a verdict follows the last group review. Commit `b785310`.
- **Decision record:** group severity was previously "not implemented by design"; it was added at the operator's request and stays labelled provisional until validated against labelled scenarios.
- **Local example:** ZONE-A (unauthorized Face + PPE + SSH) = HIGH; clearing the PPE keeps the same group at MEDIUM.

### Investigator numeric and identity checks

- **What:** `investigator_field_checks.py`. Labelled numeric claims for Maintenance, Environment, PPE and Face (plus existing SSH) are compared with saved fields at the claim's precision; person IDs must belong to a Face record in context; every member of pairs/groups is checked against its own record; a domain with several members is skipped as ambiguous. Commit `23fb19b`.
- **Limit:** only explicitly labelled claims are checked; narrative and causal claims remain unverified.

### Performance

- **Found:** the review-decision endpoint took ~18 s, saturating the server under the queue's 5-second polling (reviews appeared stuck). Cause: a new Neo4j connection (~2 s) per Face authorization check, run several times per request.
- **Fixed:** shared driver, Evidence loaded once per grouping. Review decision 18.5 s → 0.12 s; groups 8.3 s → 0.09 s. Commit `4812bae`.
- **Config:** `NEO4J_URI` should use `127.0.0.1`, not `localhost`, on Windows (2.04 s → 0.00 s per connection). Applied to the local `.env`; noted in `.env.example`.

### Review workflow fixes

- Specialist evaluation can be run from the review form after explicit consent (`01fb563`); stale-review messages explain what to do (`5282a1c`).
- The fake test incident `DCG-TEST-001` had leaked into the real database from an unisolated test; removed, and all backend tests now use a temporary database (`478a45e`).

### Repository cleanup and test isolation — `478a45e`

- Removed stray logs, an old build log, a stale `phase1/` copy and three unused frontend components; tracked `package-lock.json`; ignored build caches.
- Reasoning contract runner removes `SCENARIO-*` test nodes from Neo4j after the suite (previously 42 test nodes had accumulated in the shared graph) and forces UTF-8 output (DeepFace's emoji crashed logged runs).

### Operations: logs and full project check — `6736540`

- **Logs:** the backend writes `logs/api_access.log`, `logs/backend.log`, `logs/errors.log` (rotating, git-ignored; no bodies, headers, credentials or query strings). See `logs/README.md`.
- **One command:** `python check_all.py` runs runtime, Evidence (GPU scripts in their component environments), Reasoning, Response, Decision/integration, backend tests, frontend build and a GET-only live API test; report in `logs/checks/`. Never calls OpenAI.
- **Stale tests fixed** (`a03772e`): PPE final-test (policy frozen after the locked evaluation) and integration service contract (Decision rules connected since `d4cb326`).

### Verified (2026-10-11)

`python check_all.py`: **51/51** after the private Face image `validation_known/P005` was restored by the operator — runtime 4/4, Evidence 29/29, Reasoning 24/24, Response 15/15, Decision/integration 4/4, backend 305 tests, frontend build, live API 54 GET requests with 0 server errors. Backend access log at the time: 325 requests, all 200, slowest 0.27 s.

Not covered automatically: browser click-through of the dashboard, and live OpenAI Investigator answers (everything around the provider call is tested with fakes).

---

## Testing plan (agreed 2026-10-11)

Keep every existing check; change how they are organized. Status is updated as items land.

| # | Item | Why | Status |
|---|---|---|---|
| 1 | GitHub Actions: run the fast tests on every push | Automatic ✓/✗ per commit | **Done** 2026-10-11 (`ci.yml`; green since `4d055ef`) |
| 2 | Move `inspect_sh17_*.py` to `evidence/ppe_detection/tools/` | Exploration scripts, not tests | **Done** 2026-10-11 |
| 3 | Pilot: convert Reasoning graph/correlation scripts to pytest with shared Neo4j fixtures and markers (`neo4j`, `gpu`, `private_data`) | ~19,400 lines for 541 checks; 13 copies of driver/cleanup code; stops at first failure; order-dependent | Planned |
| 4 | Browser tests (Playwright) for verdict, group review and Decision re-evaluation | Frontend has no automated tests | Planned |
| 5 | Convert remaining script tests (Evidence, Response, integration) after the pilot is reviewed | Single runner, per-test results, selectable tests | Planned |

Rule for conversions: the same checks must still run — assertion counts are compared before and after.
