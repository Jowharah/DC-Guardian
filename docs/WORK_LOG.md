# DC-GUARDIAN — Engineering work log

Dated record of changes to DC-GUARDIAN (on `main` since 2026-10-11; earlier entries were made on `feature/presentation-dashboard`, merged by PR #2): what changed, why, the commit, how it was verified, and known caveats. Newest first. Detailed contracts live in the linked documents; this log is the index of *what happened when*.

Conventions: commit hashes are in the history of `main` (PR #2 used a merge commit, so every hash cited before the merge remains valid). "Verified" lists what was actually run. Local data results are time-specific, not permanent expected values.

---

## 2026-10-11 — API access matrix (every endpoint × every role)

- **What:** `test_access_matrix.py`: a reviewed `POLICY` table classifying all 99 API operations (public, any role, a domain's detail permission, administrator only, or permission-filtered lookup), and tests that call each operation (each `{kind}` expanded, schema-generated valid bodies) without credentials and as each non-admin role.
- **How it was built:** a probe ran every operation as every role in isolation (temp DB, Neo4j at an unreachable port, OpenAI blocked); results were read against the handler code before being written into the table. The first runs corrected three classifications (cross-domain `check-published`, SSH controlled time and image capture declarations are administrator-only by design).
- **Findings:** no endpoint answers without credentials except `/health`; no role reaches another domain's detail. Two **policy differences** (not changed, awaiting the operator): maintenance/environment feeds are readable by every role in its zones, while SSH/PPE/Face feeds need detail permission (an existing test makes this deliberate); PPE/Face uploads need only the safety detail permission, while maintenance/environment/SSH uploads need `scenario:execute`.
- **Verified:** backend pytest 339 passed. Runs in CI with the other backend tests.

---

## 2026-10-11 — Specialist evaluation for single events (all domains)

- **What:** `single_specialists.py` (`GET/POST /api/v1/evidence/{kind}/{id}/specialist`) and `SingleSpecialistPanel.tsx` beside the verdict panel for any selected single event. Reuses the unified specialists (same retrieval, grounding check, retry); consent required (400 without it), administrator only, authorization before Evidence is read; saved with an Evidence + verdict fingerprint so a later verdict shows "changed since; re-run". New table `single_specialist_results` (included in the dev reset).
- **Why:** PPE and Face events alone had no specialist path, and a maintenance event whose ingestion-time specialist failed could not be retried.
- **Verified:** backend pytest 333 passed (new `test_single_specialists.py`, OpenAI blocked); Playwright 9 passed (consent flow). No live OpenAI call made; first live run is the operator's.

---

## 2026-10-11 — Live check: blank page on a group with an overridden PPE image

- **Symptom:** opening the unified group `DCG-UNIFIED-EF17…` blanked the whole dashboard.
- **Cause** (reproduced with a browser script against the running app; `TypeError: Cannot read properties of undefined (reading 'replaceAll')` in `PPEObservationViewer`): the PPE detail endpoint carries the detector status in `assessment.overall_status` and has no top-level `status`; the viewer read `detail.status`, which only rendered empty text normally but crashed in the human-override branch. Pre-existing, exposed by the first PPE override inside a group.
- **Fix:** the viewer reads `assessment.overall_status` (fallbacks for older records); per-person status is null-safe. Long status pills in the feed (e.g. HIGH TEMPERATURE) now wrap inside the column instead of being clipped (`.severity` had `width:max-content`).
- **Live check of the specialist fix:** the group's specialists were re-run by the operator at 18:27 and succeeded (operations PARTIALLY_SUPPORTED, physical security SUPPORTED); `logs/errors.log` has no errors after the 18:15 failure that led to the grounding fix.
- **Verified:** the Playwright override test now opens the overridden PPE image (it would have hit the same crash); 8 browser tests pass; the live app renders the group.

---

## 2026-10-11 — Documentation refresh

- Roadmap (`REMAINING_ROADMAP.md`) updated to 2026-10-11: rows for the Monitoring summary, single-event severity, single-event specialists; human-verdict row no longer lists browser validation as missing; suggested order refreshed (independent labelling first, since it now validates both the Bayesian study and the v2 group rule).
- `VALIDATION_AND_OPERATIONS.md`: latest full check (54/54) and the Decision v2 validation command; `docs/README.md` distinction 4 now describes v1/v2 Decision severity; testing plan item 4 counts 8 browser tests.

---

## 2026-10-11 — Decision Rules v2: every domain and unified groups

- **Why:** unified groups had only a provisional severity that validation showed was non-discriminating (3+ domains → HIGH regardless of whether the events belong together), and single maintenance, environment, PPE and Face events had no severity at all.
- **What:** `decision/rules_v2.py` (`DCG-DECISION-v2`; v1 unchanged): conservative single-event policy for every domain (operator choice); group severity = most severe active member, +1 level for linked evidence (`L2_KNOWN_MECHANISM_WITHIN_10_MIN`). Live: unified groups carry the v2 Decision and linkage signals (`unified_severity.group_severity`, `annotate`); new `GET /api/v1/decisions/standalone` (`standalone_decision.py`) gives v2 Decisions for PPE/Face/Maintenance/Environment after human verdicts. Dashboard: severity pills on single-event rows, "HIGH · LINKED" on escalated groups, group detail explains base level and linkage, the Unified Decision line shows the v2 severity with its caveat; the severity filter, Decisions card and Analytics now use one `entrySeverity` (a correlated event counts once, with its group).
- **Validation protocol** (`presentation/backend/validation/decision_v2_validation.py`): candidates and criterion declared in code before scoring; selection on dev only; the script refuses to score the test split until the rule is fixed and fails if the fixed rule differs from the dev selection. Test split, evaluated once: escalated 89% genuine vs 38% (difference +0.51, 95% CI +0.08 to +0.88); v2 HIGH 86% genuine vs 67% for the old policy.
- **Verified:** backend pytest 327 passed (new `test_decision_v2.py`: policy table, escalation, KB consistency, dev selection reproduces the fixed rule, live wiring, verdict handling); `tsc`, build, Playwright 8 passed (new v2 test); on the local data the SSH + unauthorized Face + PPE group is HIGH (linked) and the operator-cleared group is LOW.
- **Caveats:** author labels (independent round pending); small test sample; MEDIUM/LOW ordering is policy, not validated. Correlation group IDs are unchanged, so saved specialist results stay valid.

---

## 2026-10-11 — Monitoring Center summary redesign

- **What:** the four total-count cards (including the redundant "Operating mode" card) became an attention-first summary (`MonitoringSummary.tsx`):
  - **Live indicator** in the header (live / delayed / offline, from the last API answer below 500; network errors and 5xx count as failures, a 404/409 does not). Replaces "refresh every 5 seconds".
  - **Needs attention:** abnormal detector results without a human verdict, unified groups without a current saved specialist evaluation (404 or 409 from the saved-specialists endpoint, polled every 10 s), and Decisions flagged for re-evaluation.
  - **Abnormal detector results** (with the last-24 h count), **Correlations** (groups, pairs, groups awaiting specialists), **Saved Decisions** split HIGH/MEDIUM/LOW with the re-evaluation count.
  - **Domain strip:** abnormal/total and time since the last record per domain; the dot goes grey after 24 h without data.
  - Cards and domain chips filter the feed ("Showing: … · Show all"); correlation rows count as abnormal because they only link abnormal Evidence.
- **Shared logic:** `detectorOutcomes.ts` holds the abnormal-state definition and per-record outcomes, used by both Monitoring Center and Analytics so their counts agree.
- **Verified:** `tsc`, `npm run build`, Playwright 7 passed (new summary/filter test); screenshots at 1500 px and 420 px checked.
- **Caveats:** display only; no new severity logic. The "not evaluated" check adds one GET per unified group every 10 s.

---

## 2026-10-11 — Logo in the dashboard

- **What:** the operator's logo set (`logo/`: mark, dark/light lockups, PNG sizes, favicons) is now the source of the dashboard branding. Copies served by Vite live in `presentation/frontend/public/` (favicon.ico, favicon-32.png, mark SVG, 256 px mark for touch icons, dark-background lockup).
- **Where:** browser-tab icons and theme colour in `index.html`; sidebar brand is the mark plus "DC-GUARDIAN" with the pink hyphen (mark only when the Investigator is expanded on narrow screens); the sign-in card shows the dark-background lockup.
- **Verified:** `npm run build`; Playwright 6 passed; screenshots of sign-in and sidebar checked.
- **Note:** if the logo changes, update `logo/` and re-copy the five files into `public/`.

---

## 2026-10-11 — Specialist grounding failures, verdict badge, detector-outcome analytics

- **Verdict badge** (`f32b7a0`): on PPE, Face, Maintenance and Environment feed rows the human-verdict pill was a fifth grid cell and wrapped onto its own line; it now shares the status cell (as SSH rows did) and never wraps. Specialist failures in the maintenance/environment ingestion workflows and the unified endpoint are now logged to `logs/errors.log` (type and message only) instead of being swallowed.
- **Unified specialist 503, cause found from that log:** `ValueError: Supported or partially supported assessments must cite retrieved evidence.` The Operations specialist retrieved knowledge with a generic query ("Data center operations evidence review"), got unrelated passages, answered SUPPORTED without citations, and the grounding check rejected it, which failed the whole group. Fix: a domain-specific retrieval query per specialist (`DOMAIN_QUERIES`), one retry when an answer fails the grounding check (the check is unchanged; provider errors are not retried), and a 503 detail that names the specialist. Groups stay all-or-nothing on purpose: synthesis and review assume every domain was assessed. The dashboard now shows the server's error detail instead of only "API request failed (503)".
- **Analytics:** new "Detector outcomes by domain" panel (state counts per domain, abnormal share, human confirmed/overridden/inconclusive counts beside the detector result, drill-down), plus "Abnormal detector results" and "Human verdicts recorded" cards. Abnormal follows the Reasoning layer's states; environment uses the detector's own `anomaly_detected` flag. Display only, no severity.
- **Verified:** backend pytest 319 passed (new `test_unified_specialist_grounding.py`, stub agents, no OpenAI); `npm run build`; Playwright 6 passed (new analytics test).
- **Caveats:** the retry costs one extra OpenAI call when it triggers. The first two standalone maintenance events from 2026-10-11 show RESPONSE UNAVAILABLE from before logging existed; a later maintenance event completed, so the cause was likely the same intermittent grounding failure, but this is not confirmed. Single PPE and Face events still have no standalone specialist.

---

## 2026-10-11 — LLM rater for the uncertainty study

- **What:** ChatGPT labelled the blind pack; scored with `score_labels.py` into `reasoning/uncertainty/labelling/results/llm-chatgpt.*` (labels kept as `llm-chatgpt_labels.csv`).
- **Result (test split):** 78% agreement with the author (kappa 0.55); Bayesian F1 0.756 vs crisp 0.596, difference +0.03 to +0.29, so the Bayesian advantage holds with a second labeller.
- **Caveat:** recorded as an LLM rater, not independent validation. Its labels follow a fixed same-zone/domain-pair rule that mirrors the knowledge base's known mechanisms (partly circular), and it labelled all chiller-to-hall cascades unrelated despite the stated cooling dependency. Human labellers are still needed.

---

## 2026-10-11 — `main` brought up to date; branch and path references

- **PR #2** merged `feature/presentation-dashboard` into `main` (merge commit `f2b8273`, 653 commits); CI green on `main` afterwards. `main` is now the default working line.
- **Workflow** (recorded in `CLAUDE.md`): short-lived branches from `main` (`feat/`, `fix/`, `docs/`, `test/`), pull request into `main`, green CI, **Create a merge commit**, delete the branch.
- **Stale references fixed:** docs and `CLAUDE.md` that named `feature/presentation-dashboard` as the active branch (headers, the `git pull` command, the README baseline) now name `main`; the roadmap's Bayesian row no longer lists live scoring as missing. Historical statements ("developed on …", "reported on …") were kept as written.
- **Path references:** a script checked every path in tracked Markdown files; none are broken (the remaining mentions of `phase1/` describe its removal).
- **`feature/presentation-dashboard` archived:** fully merged (no unique commits), tagged `archive/feature/presentation-dashboard` at its last commit `aafd492`, then deleted on GitHub and locally.
- **CI** now runs on pushes to any branch (it previously covered only `main` and `feature/**`, so `docs/` or `fix/` branches had no checks before a pull request).

---

## 2026-10-11 — Research strengthening, testing plan items 3–5, security gates

### Uncertainty study: confidence intervals and a blind labelling pack — `59c7e89`

- **Confidence intervals:** `evaluate.py` adds a scenario-level bootstrap (2,000 draws, separate seed; all earlier numbers unchanged). Test split: crisp F1 0.375–0.788, Bayesian F1 0.571–0.862, **difference +0.022 to +0.261**, Bayesian higher in 99.2% of resamples. The advantage is unlikely to be noise; its size is uncertain.
- **Blind labelling pack** (`reasoning/uncertainty/labelling/`): the scenario file states its answers in titles and narratives, so teammates get a generated `pack/` instead: neutral shuffled IDs, events only, a facility brief and glossary, and `labels.csv` with the 85 candidate pairs. `score_labels.py` reports agreement (percent, Cohen's kappa) and re-evaluates both methods on the independent labels with bootstrap intervals. Contract tests check the pack leaks no answers and that the author's own labels reproduce the published F1 exactly.

### Research P(Related) in the dashboard — `b7352bf`

- Every pair from `GET /api/v1/correlations/pairs` carries the Bayesian estimate and factor explanation, shown in all pair views as a research estimate. Display only; the deterministic rule stays authoritative. Unobservable factors (PPE confidence) are marginalized; non-abnormal pairs are "not scored".
- Local example: unauthorized Face + SSH in ZONE-A 0.96; PPE + SSH 0.51 (unlikely mechanism).

### Group severity validation — `48cd511`

- `presentation/backend/validation/group_severity_validation.py` applies the provisional group severity to groups formed from the labelled scenarios. Finding: severity does **not** separate genuine incidents from coincidences (test split genuine share HIGH 2/3, MEDIUM 5/8, LOW 4/6), because the level depends only on domain count. The policy stays provisional; validating levels needs severity labels.

### Security gates in CI — `41ebea3`, `109c42b`, `5ac2996`

- Bandit (medium/high), pip-audit and `npm audit` (high) now fail the build. Baseline locally: Bandit 0 medium/high after refactoring `evidence_review.rows()` to fixed parameterized queries and annotating reviewed-safe findings with their reason; pip-audit and npm audit 0.
- CI found what local runs could not: the runner's preinstalled **setuptools 78.1.0** had two advisories (upgraded in CI). CPU PyTorch wheels are not on PyPI and are reported as not auditable.
- pip-audit findings are emitted as annotations so they are readable without admin log access. Actions upgraded to their Node 24 releases.

### Browser tests (testing plan item 4) — `109c42b`

- Playwright 1.63.0, five tests against the built dashboard with a stateful mocked API (synthetic data): sign-in; PPE override shown as human verified; override validation; consented specialist evaluation then group review; Decision re-evaluation after a cleared input. Locally they use the installed Edge (`npm run test:e2e`); CI runs them on Chromium.
- **Bug found by the tests:** before any verdict existed, the override list offered the detector's own status, which the backend rejects. The verdict endpoint now returns `detector_status` and the panel excludes it.

### Pytest pilot (testing plan item 3) — `5ac2996`

- The two graph contracts that left nodes behind (SSH and maintenance ingestion) are now pytest with a shared `reasoning/graph/conftest.py`: session Neo4j driver (skip with reason), `single()` query helper, `cleanup_graph()` before and after. Same 15 checks per file (counted), 12 named tests; ~1,290 lines became ~200. Reasoning suite 24/24; end-of-suite cleanup now removes 40 instead of 42 nodes.
- **For review:** if the group likes this style, the remaining 21 Reasoning, 29 Evidence and 15 Response/integration script contracts can follow the same pattern (item 5).

---

## 2026-10-11 — Uncertainty study: dev-split disclosure

- **What:** `UNCERTAINTY_REASONING.md` now states that seven dev scenarios (D06, D07, D08, D12, D13, D15, D16) were scored by hand with the Bayesian model while being written, so dev results are not independent; the test split (written unscored) is the one to cite.
- **Why:** disclosed by the web session that wrote the scenarios; the local session could not know it from the commit history.
- **Verified:** documentation only; no code, scenario or result changed.

---

## 2026-10-11 — Repository housekeeping and shared session context

### Branch cleanup

- **What:** five fully merged branches with no unique commits were archived as tags and deleted from GitHub: `archive/docs/security-assessment-report`, `archive/feature/phase3-grounded-reasoning`, `archive/feature/phase3-rag-foundation`, `archive/refactor/architecture-naming`, `archive/security/pre-dashboard-hardening`. Each tag was verified to point at the branch's last commit before deletion. `feature/uncertainty-reasoning` was deleted after its merge.
- **Result:** GitHub branches are `main` and `feature/presentation-dashboard`. Recreate an archived branch with `git switch -c <name> archive/<name>`.

### `CLAUDE.md`

- **What:** a root `CLAUDE.md` that Claude Code reads at the start of every session, locally and on the web: project layers, non-negotiable rules, environment and run commands, how to verify (`check_all.py`, CI), conventions (branches, work log, commit style, line endings, test isolation) and where to look.
- **Why:** the Claude Code web session that produced the uncertainty study started without this context: it could not run the full check and did not know the project's conventions. Workflow now: web sessions work on a branch and push; the local session reviews, runs the full check and merges; CI checks every push.

---

## 2026-10-11 — Reasoning under uncertainty (developed on `feature/uncertainty-reasoning`, merged)

- **What:** a Bayesian correlation model that estimates P(Related) for a pair of abnormal events from time gap, topology, domain mechanism and evidence strength, with a per-factor explanation. Expert knowledge base with sources, 40 labelled DC-01 scenarios (16 dev, 24 test), offline evaluation against the frozen crisp rule, and 15 contract tests added to `check_all.py`. Details: [Uncertainty Reasoning](UNCERTAINTY_REASONING.md).
- **Why:** the crisp zone/15-minute rule cannot express degrees of belief or explain itself, and the cross-domain claim had no quantitative evaluation.
- **Commits:** `c0b9dc3` committed the knowledge base, scenarios and model code before the evaluation script (`22119f2`); the knowledge base is unchanged since. The commit order cannot show that no scenario was scored before that commit (same session, three minutes apart).
- **Verified:** `python reasoning/uncertainty/test_uncertainty_reasoning.py` (15/15) and `python reasoning/uncertainty/evaluate.py` in a cloud session (Python 3.13, no Neo4j). Test split: crisp F1 0.593, Bayesian F1 0.731; alerts 65 single-domain / 44 crisp / 43 Bayesian.
- **Merged** into `feature/presentation-dashboard` on 2026-10-11 after review: tests 15/15 and the evaluation reproduced byte for byte locally; full `python check_all.py` on the merged code: **52/52**. The branch was then deleted.
- **Caveats:** author-labelled synthetic scenarios and a small sample; not yet wired into the dashboard or Decision layer.

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
| 3 | Pilot: convert Reasoning graph/correlation scripts to pytest with shared Neo4j fixtures and markers (`neo4j`, `gpu`, `private_data`) | ~19,400 lines for 541 checks; 13 copies of driver/cleanup code; stops at first failure; order-dependent | **Pilot done** 2026-10-11 (SSH and maintenance ingestion); awaiting group review |
| 4 | Browser tests (Playwright) for verdict, group review and Decision re-evaluation | Frontend has no automated tests | **Done** 2026-10-11 (5 tests, in CI); 8 tests since (analytics outcomes, monitoring summary, v2 Decisions) |
| 5 | Convert remaining script tests (Evidence, Response, integration) after the pilot is reviewed | Single runner, per-test results, selectable tests | Planned |

Rule for conversions: the same checks must still run — assertion counts are compared before and after.
