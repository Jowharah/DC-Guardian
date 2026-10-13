# DC-GUARDIAN — Engineering work log

Dated record of changes to DC-GUARDIAN (on `main` since 2026-10-11; earlier entries were made on `feature/presentation-dashboard`, merged by PR #2): what changed, why, the commit, how it was verified, and known caveats. Newest first. Detailed contracts live in the linked documents; this log is the index of *what happened when*.

Conventions: commit hashes are in the history of `main` (PR #2 used a merge commit, so every hash cited before the merge remains valid). "Verified" lists what was actually run. Local data results are time-specific, not permanent expected values.

---

## 2026-10-13 — PPE-v2 detector candidate (roadmap item 9, model enhancement)

- **Why (operator decision):** PPE-v1 had the lowest recall of the detectors (locked test 0.524; vest 0.449). It is YOLOv8n at 640 px on 2,000–6,000 px photos.
- **Protocol:** committed before training (`de1a113`). Revised once, before any candidate result (`a448fef`): the first epoch took 7 minutes, so the protocol moved to resized 1024-px training copies, 60 epochs and 4 workers. The scripts are `evidence/ppe_detection/src/train_v2.py`, `select_v2.py` and `evaluate_final_test_v2.py`.
  - **v1 untouched:** the v1 weights, config and metadata are never written; the training script checks their hashes before and after.
  - **Same data:** the PPE-v1 development split. Disjointness from the locked test is asserted.
  - **Selection:** on the original validation images; criterion = mean helmet and vest mAP@0.5; the smaller model wins within 0.01 and must beat v1.
  - **Locked test:** run once, by a script that refuses a second run.
- **Training (RTX 3080 Ti):**
  - YOLOv8s at 1024 px: 1 h 41 min;
  - YOLOv8m: 2 h 58 min;
  - YOLOv8n: 59 min.
- **Selection (validation), `f9f5914`:**
  - scores: v1 0.569, YOLOv8n 0.616, **YOLOv8s 0.648**, YOLOv8m 0.648;
  - YOLOv8s and YOLOv8m are tied within 0.01, so YOLOv8s was selected.
  - Vest recall at the reported operating point was 19 vs 21 of 48 vests, with vest precision 0.56 → 0.68.
- **Locked test, once (`aeb3e5f`), PPE-v1 → PPE-v2:**
  - all classes: mAP@0.5 0.545 → 0.595, recall 0.524 → 0.535;
  - helmet: recall 0.603 → 0.654, mAP 0.676 → 0.708;
  - **safety vest: recall 0.449 → 0.245, mAP 0.372 → 0.317.** This is the opposite of validation. There are only 49 vests in 23 images, so the size of the difference cannot be estimated, but v2 does not fix the vest weakness.
- **Runtime unchanged:** `ppe_config.json` (PPE-v1) still drives the pipeline; switching to v2 is the operator's decision. Missed vests turn compliant people into NON_COMPLIANT alerts.
- **Tests:** `evidence/ppe_detection/tests/test_ppe_v2_artifacts.py` (3, no GPU) checks:
  - the v1 hash and config are unchanged;
  - the recorded selection follows the rule;
  - the locked test used the selected weights.
- **Caveats:**
  - one seed per candidate;
  - small vest and helmet samples;
  - the tie between YOLOv8s and YOLOv8m depends on the declared 0.01 margin.

---

## 2026-10-13 — Scenario set v2 evaluation: operator relabel and ChatGPT sensitivity

- **Why:** item 8 of the roadmap. The operator finished the blind relabel of all 40 v2 scenarios and pasted ChatGPT's labels of the same pack, so the uncertainty evaluation and the baseline comparison can be re-run on v2 beside v1.
- **What:**
  - **Labels committed unchanged:** `labelling/results/operator-v2_labels.csv` (operator; while checking the sheet the operator corrected V04 E1–E4 to N, a contradiction the build script would have refused, and fixed notes and three confidences) and `llm-chatgpt-v2_labels.csv` (ChatGPT, pasted by the operator; no API call).
  - **Scenario sets:** `build_scenarios_v2.py` now gives `labelled_scenarios_v2.json` the operator's incidents (29) and also writes `labelled_scenarios_v2_chatgpt.json`, the same scenarios with ChatGPT's incidents (16), for the sensitivity check only.
  - **Scripts:** `evaluate.py`, `baseline_comparison.py` take `--set v1|v2|v2-chatgpt` (v1 default; v1 outputs regenerate byte-identical). `score_labels.py --pack v2` scores a v2 labeller against the operator's v2 labels and the v1 author labels.
  - **Results** (`reasoning/uncertainty/results/evaluation_report_v2*.md`, `presentation/backend/validation/results/baseline_comparison_v2*.md`, `labelling/results/{operator,llm-chatgpt}-v2.md`), test split:
    - Bayesian vs crisp F1: v1 0.731 vs 0.593 (difference +0.022 to +0.261); v2 operator 0.857 vs 0.784 (**−0.040 to +0.190**); v2 ChatGPT 0.703 vs 0.615 (−0.067 to +0.229). Perturbed models beating crisp: 87%, 48%, 62%.
    - Baseline, isolated → DC-GUARDIAN: alerts 65 → 44 under all labels; queue average precision 0.66 → 0.74 (v1), 0.73 → 0.81 (v2 operator, CI +0.02 to +0.19), 0.48 → 0.75 (v2 ChatGPT, CI +0.10 to +0.50).
    - Agreement (85 pairs): operator v2 vs v1 73% (kappa 0.46); ChatGPT v2 vs operator v2 73% (kappa 0.46). ChatGPT marks 22 pairs related, the operator 43; 10 of the 23 disagreements are heat or humidity followed by a drive at risk.
- **Reading:** correlation beats isolated monitoring under every labelling. The Bayesian gain over the crisp rule is positive but no longer significant on v2. The higher v2 scores reflect changed labels (same author, after discussing how the system links events), not a better model. Docs: UNCERTAINTY_REASONING (v2 results), report draft, VALIDATION_AND_OPERATIONS, roadmap item 8 closed, labelling README.
- **Tests:** v2 and v2-chatgpt evaluation results must be current; the ChatGPT set must differ from v2 only in labels.
- **Verified:** full `check_all.py` 14/14, run in a separate worktree with the local environments and private data linked in: Evidence 23 passed + 4 skipped (GPU, which pass in `.venv-ppe` 3/3 and `.venv-gru` 1/1); Reasoning contracts passed; uncertainty and labelling 30; RAG 10; agents 37; integration 12; backend 404; Playwright 14; live API smoke 0 server errors.
- **Caveat:** neither labelling is independent human validation; roadmap item 1 (teammates, preferably on `pack_v2/`) remains the missing evidence.

---

## 2026-10-13 — Scenario set v2: environmental states the detector can produce

- **Why (operator decision, relayed from the operator's other session):** 8 of 40 labelled scenarios used environmental states the frozen detector cannot produce: WATER_LEAK_DETECTED (D14, T22), SMOKE_DETECTED (D10, T12), AIRFLOW_ANOMALY (D03, T09) and COOLING_ANOMALY (T02, T19). Five of them are in the test split, so the PR #21 baseline numbers depend on alerts the prototype cannot raise.
- **What:**
  - **v2 scenario set:** `reasoning/uncertainty/scenarios/build_scenarios_v2.py` writes `labelled_scenarios_v2.json`.
    - Every environmental event (24) has a raw reading, and its state is assigned by `assess_environmental_condition`; no state is typed by hand.
    - Mapping: leak → HIGH_HUMIDITY; smoke, airflow and cooling → HIGH_TEMPERATURE.
    - The 16 unchanged environmental events reproduce their v1 state; the script stops otherwise.
    - The 8 rewritten scenarios have observation-only narratives.
    - **No v1 label is copied** (operator decision: full blind relabel). All 40 scenarios are `PENDING_BLIND_RELABEL`, with no ground truth, until the operator's labels exist.
  - **Extended-sensor set:** `extended_sensor_scenarios.json` holds the 8 v1 originals verbatim, reported apart as future-work evidence.
  - **v1 unchanged:** `labelled_scenarios.json` is pinned by a hash test.
  - **Full v2 blind pack:** `reasoning/uncertainty/labelling/pack_v2/`, built by `build_pack_v2.py`, with the key in `pack_v2_key.json`.
    - All 40 scenarios, 85 pairs, same format as the v1 pack, readings shown, neutral IDs V01–V40.
    - The order is new: no scenario sits in the same position as in the v1 pack.
    - `build_labelling_pack.build()` now takes parameters, and the published v1 pack rebuilds byte-identical.
  - **Labels to incidents:** the operator saves the filled sheet as `labelling/results/operator-v2_labels.csv`, which must cover all 85 pairs.
    - `build_scenarios_v2.py` turns connected related pairs into incidents. Contradictory labels are refused, not guessed.
    - Same-domain events join an incident only through a cross-domain event.
  - **First 8-scenario pack removed:** the `relabel_v2/` pack (8 scenarios, 20 pairs) from the first commit of this PR is redundant now that every scenario is relabelled.
  - **Tests:** `reasoning/uncertainty/scenarios/test_scenarios_v2.py` (12). Among them, a test fails if a v2 environmental state is outside what the detector produces, determined by running the detector over the measurement range.
- **Not independent:** the v2 labels are a full blind relabel by the same author who wrote v1, so they are still not independent labels.
- **Docs, person access:** the website and Neo4j are the authority for zone access. The topology file only seeds P001–P003, and P005's Zone B access exists only in Neo4j (VALIDATION_AND_OPERATIONS).
- **Expected effect:** the Bayesian knowledge base treats all dedicated room sensors as strong evidence, so model inputs barely change. Results can change through the new labels: heat alone is more ambiguous.
- **Not done yet (waiting on the operator):**
  - the operator's blind labels;
  - the ChatGPT labels (pasted by the operator, no API call);
  - the v2 re-run of the uncertainty evaluation and the baseline comparison, with old and new results side by side. The latency benchmark does not use the scenarios.
- **Verified:** full `check_all.py`, 14 of 14 suite-level checks (the 54 script checks became 14 pytest suites on 2026-10-12): Evidence 23 passed + 4 skipped (GPU tests, which pass in `.venv-ppe` 3/3 and `.venv-gru` 1/1); Reasoning contracts 24/24; uncertainty and labelling 28; RAG 10; agents 37; integration 12; backend 404; Playwright 14; live API smoke 0 server errors.

---

## 2026-10-13 — Single-domain baseline comparison and pipeline latency

- **Why:** a project-versus-proposal check found two gaps in the evaluation plan:
  - the research question compares DC-GUARDIAN with isolated single-domain monitoring, and that comparison was missing;
  - latency was logged but never measured.
- **Baseline (`presentation/backend/validation/baseline_comparison.py`):** the protocol was fixed before any result was computed.
  - Both systems use the DCG-DECISION-v2 single-event severities.
  - Queues are sorted by severity, ties random over 500 orders.
  - The held-out test split is primary, with a scenario bootstrap.
  - Results (test split):
    - alerts 65 → 44 (CI −29 to −14);
    - average precision 0.66 → 0.74 (CI +0.02 to +0.18);
    - 11 of 18 incidents shown whole (0 isolated);
    - 86% of HIGH alerts are incidents.
  - The dev split points the same way.
  - Alert and linkage counts match the uncertainty study's operator view (a test asserts this).
- **Latency (`presentation/backend/validation/latency_benchmark.py`):**
  - **Upload endpoints:** run in-process against a temporary database with publish and retain off, so there is no OpenAI call and nothing is stored.
  - **Neo4j:** ingestion and correlation of the correlation contract's controlled events, in a `SCENARIO-LATENCY-*` scope that is removed afterwards (verified: 0 nodes remain).
  - **Decision v2:** timed in-process.
  - **Observed use:** per-route latency from the access logs, matched against the OpenAPI path templates. FastAPI 0.143 wraps included routers, so `app.routes` no longer lists their paths.
  - **Results:**
    - inference 4.1 s (SSH), 4.2 s (PPE) and 10.1 s (Face): a new worker process per upload, model loading included;
    - graph and correlation 0.05 s;
    - Decision 8 µs;
    - Investigator 3.2 s;
    - specialists 12–24 s.
- **Report draft:** `docs/report/evaluation_baseline_and_latency.md`.
- **Verified:**
  - both scripts run;
  - new tests `test_baseline_comparison.py` (consistency with the uncertainty study, a hand-checked queue) and `test_latency_benchmark.py` (log parsing);
  - backend suite.
- **Caveats:**
  - author labels;
  - synthetic scenarios;
  - the baseline uses DC-GUARDIAN's own single-event policy;
  - one machine and one user, no load test;
  - few observed specialist calls.

---

## 2026-10-12 — Testing plan item 5 completed: every test under pytest

- **What (operator request):** the remaining 55 script tests are pytest modules: 27 Evidence (4 GPU), 6 RAG and 22 Reasoning, including the labelling pack. Each straight-line script body moved unchanged into a `test_<name>_contract()` function; scripts with a `main()` got a test that calls it; a `__main__` guard keeps `python <file>` working; multi-line string lines were not re-indented.
- **Infrastructure:**
  - The root `conftest.py` turns the markers `private_data(*paths)`, `gpu` and `neo4j` into skips with reasons.
  - `pytest.ini`: `--import-mode=importlib`, `pythonpath = .` (duplicate test file names across Evidence folders).
  - pytest 9.1.1 installed in `.venv-ppe`, `.venv-gru` and `.venv-face`.
  - The Reasoning graph helpers moved to `graph_test_support.py`: `from conftest import ...` would now resolve to the root conftest.
  - `reasoning/run_contract_tests.py` runs every contract with pytest, in the same dependency order.
  - `check_all.py` has one check per suite: **14 checks** (was 44; same tests).
- **A trap that was caught:** six scripts ran their checks inside `if __name__ == "__main__":`. Wrapped in a function, those checks would not have run under pytest, yet the test would have passed. The guards are now unconditional.
- **Equivalence:**
  - identical `assert`/`raise` counts per file (889 / 133 across the 55 files);
  - identical `PASS` output as a script and under pytest for 55/55 files (GPU files in their component environments).
- **Verified:** `check_all.py` 14/14:
  - Evidence 23 + 4 GPU;
  - Reasoning 24 contracts + 16;
  - RAG 10;
  - agents 37;
  - integration 12;
  - backend 400;
  - Playwright 14.
- **Remaining (optional):** splitting the 55 module-level files into one test per check.

---

## 2026-10-12 — Backup folder

- **Operator choice:** `C:\Users\Aljawharah\Documents\DC-Guardian Backup`. New setting `DCG_BACKUP_DIR` (in `.env`, documented in `.env.example`) gives `backup create` a default of `<dir>\backups` and `audit_checkpoint write` a default of `<dir>\checkpoints`; both still accept `--out-dir`.
- **First run:** backup (with the ingestion state) and checkpoint written; `backup verify` PASS, `audit_checkpoint verify` PASS (all four chains); 29 MB.
- **Verified:** backup and checkpoint tests 11 passed (new default-location test).
- **Caveat:** checkpoints on the same disk as the database are weaker against replacement than on a second drive.

---

## 2026-10-12 — Post-generation overclaim judge (measured)

- **What:** `investigator_judge.py`. After every Investigator answer, a short structured call reads only the pseudonymized answer text and quotes sentences that state presence, a cause (including which inputs drove a model) or PPE absence as fact.
  - Its findings are added to `claim_checks.model_judge`, and a flag raises the status to VIOLATION; the panel lists them as "Model check".
  - Invented quotes are dropped. A failure is shown as UNAVAILABLE and never blocks the answer.
  - Settings in `.env.example`: `DCG_INVESTIGATOR_JUDGE_ENABLED`, `DCG_INVESTIGATOR_JUDGE_MODEL`. The same file now also documents the rate limit and pseudonym key.
- **Measurement** (`presentation/backend/validation/judge_eval.py`; per-answer output local; summaries in `results/judge_{design,test}.md`):

  | Split | Answers | Overclaims | Caught | False alarms |
  |---|---:|---:|---:|---:|
  | Design (dev + holdout; instructions refined: v1 → v2 → v3) | 40 | 4 | v1 3/4, v3 **4/4** | v1 11/36, v3 **1/36** |
  | **Test** (round-2, blind labels, frozen v3, scored once) | 40 | 5 | **4/5** | **1/35** |

  - Missed: a presence claim ("in the area covered by ZONE-A").
  - False alarm: a factually wrong "second worker was wearing a vest" read as an absence claim.
- **Verified:** backend pytest 399 passed (new `test_investigator_judge.py` with a fake client: flag raises status, judge sees only the pseudonymized answer, invented quotes dropped, failure never blocks, can be disabled); Playwright 14 passed.
- **Caveats:**
  - Author labels and small samples.
  - One extra model call per answer (cost; covered by the rate limit).
  - Calls to the judge are not separate rows in the call audit: its status is folded into the answer's `claim_status`.
  - Confirm with labels from teammates.

---

## 2026-10-12 — Investigator instructions: presence and causation (measured, no effect)

- **What:** the Investigator instructions now give exact wording for presence ("recognized in an image from a camera declared in ZONE-X"; never present, standing, inside or on site; no room names the context lacks). They forbid stating causes ("model assessed elevated failure risk; reported SMART values include …", never "failing because of"), and say temperature, cooling and HVAC causes were not assessed.
- **Test:** 20 new questions (`ROUND2` in `claim_check_collect.py`) asked with the old instructions and again with the new ones (the backend restart was confirmed by process start time). The 40 answers were shuffled under neutral IDs and labelled blind; the key was opened only afterwards. Summary in `claim_check_labels.json` (`round2`).
- **Result:** answers with an overclaim 2/20 before, 3/20 after (presence 0→1, causation 1→1, vest "not worn" 1→1); factual errors 3→1. No measurable improvement. The wording got more precise, but overclaims persist at roughly 10–15% of tempting questions.
- **Decision:** keep the instructions (more precise, no harm) and record that they are not a control. Next: a post-generation check, measured on new questions.
- **Verified:** backend pytest 394 passed. Live calls: 40, operator-approved.

---

## 2026-10-12 — Open a listed record in the Monitoring Center

- **Why (operator request):** Analytics drill-down lists and Review Queue items showed record IDs, but the only way to reach the record was a generic "Open Monitoring Center" button and a search through the feed.
- **What:** `openInMonitoring(id)` in `App.tsx` finds the record by its ID in any feed (PPE, Face, SSH, maintenance, environment, unified group, pair, operational, physical, Face + SSH, pipeline incident). It switches to the Monitoring Center, clears feed filters, opens the record and scrolls to the investigation view.
  - Every Analytics drill-down ID is now a link.
  - Every Review Queue item has "View in Monitoring Center".
  - The PPE and Face detail panels now show the record ID.
- **Verified:** Playwright 14 passed (new test: Analytics → PPE record, Review Queue → unified group; accessibility scans pass).

---

## 2026-10-12 — RAG retrieval re-evaluation (all four experiments)

- **Why:** the Response document still reported the retrieval experiments on the 260-chunk corpus from before the CFR section fix; only the abstention configuration had been re-run.
- **What:** all four configurations (raw, diverse, controlled, controlled + abstention) re-run on the 255-chunk index with the same 18 frozen cases; `docs/DC_Guardian_Response_Architecture_and_Validation.md` now carries a dated re-evaluation table beside the original, and the updated chunk counts.
- **Result (selected controlled policy):** Recall@3 90.2% → 96.1%, Precision@3 65.7% → 71.6%, MRR 0.873 → 0.971; Hit Rate@3 100%; filter and provenance 100%. Controlled diversity remains the best trade-off; abstention remains experimental (MRR 0.618).
- **Weak cases:** heat + drive-risk with three expected sources (Recall@3 0.33); one physical-access case ranks the right source second; the no-source case still needs the eligibility check.
- **Verified:** `verify_response_rag.py` reports 13 sources and 255 chunks; all RAG checks pass.

---

## 2026-10-12 — Claim checker measured on live answers

- **Method:**
  - `claim_check_collect.py` asks a fixed question set (most worded to tempt overclaims) about the operator's Evidence through the running backend, paced under the rate limit. Operator-approved; the answers stay local because they contain Evidence.
  - The author labelled every answer (`claim_check_labels.json`: case IDs and judgements only).
  - `claim_check_report.py` re-runs the current checker against the record each answer saw and scores it.
  - Protocol: the checker was improved on the 20-answer development set only; a 20-answer holdout set with new wording was collected afterwards and scored once.
- **Development set:** 1 real overclaim. The original checker caught 0 and raised 2 false alarms:
  - a markdown heading "Missing PPE" read as non-compliance;
  - "not clearly benign" read as "benign".

  Fixed: headings skipped, negation limited to the three preceding words, "benign" only as a claim, wider physical-presence wording. Afterwards 1/1 with 0 false alarms (in-sample).
- **Holdout:** 3 real overclaims (2 physical presence, 1 causation); **0 caught**, 0 false alarms. The patterns do not generalise to unseen wording.
- **Model behaviour over all 40 answers:**
  - 4 boundary overclaims;
  - 3 out-of-scope factual errors;
  - all action requests refused, and no attacker ever named.
- **Verified:** backend pytest 394 passed (dev-set regression tests added); reports in `presentation/backend/validation/results/claim_check_{dev,holdout}.md`.
- **Caveats and next step:**
  - Author labels only; small sample.
  - Prevention through instructions, or a label-validated model judge, should be measured on a fresh holdout.
  - The holdout answers must not be used to tune patterns.

---

## 2026-10-12 — Safety knowledge: CFR section boundaries (PPE specialist fixed)

- **Cause:** the approved OSHA sources are official GovInfo PDFs of whole printed CFR pages, so each document also held its neighbours: 1910.135 (head protection) began with the end of 1910.134 (respirators), 1910.132 with the end of 1910.131, and 1910.137 repeated the 1910.135/136 text. Neighbouring text dominated the chunk embeddings, so PPE searches returned respirator, lockout and electrical-glove passages and the PPE specialist could not cite support.
- **Fix:** `preprocess_sources.py` trims each `OSHA-1910-*` document to its own section, from the heading `§ 1910.NNN Title` to the next section's heading. Page headers and cross-references are not treated as headings; text is cut, never rewritten; the cut is recorded per page (`cfr_section`, `cfr_chars_cut_before/after`). No source was added or changed; only the five OSHA documents' derived files differ.
- **Rebuild** (knowledge base and index are local, not in Git), from the repository root:
  ```
  PYTHONPATH=. python response/rag/preprocess_sources.py
  PYTHONPATH=. python response/rag/chunk_sources.py
  PYTHONPATH=. python response/rag/build_index.py
  ```
  Without `PYTHONPATH` the chunk and index steps fail with `No module named 'response'`.
- **Results:**
  - The index drops from 260 to 255 chunks (duplicates removed).
  - Safety searches now return OSHA 1910.132 (general PPE requirements, hazard assessment) and 1910.135 (protective helmets).
  - Retrieval evaluation (same settings as the saved report: controlled ranking, abstention on, 18 frozen cases):

    | Measure | Before | After |
    |---|---:|---:|
    | MRR | 0.461 | 0.618 |
    | hit@1 | 0.353 | 0.588 |
    | recall@5 | 0.510 | 0.608 |
    | Negative cases | 0.5 | 0.5 |

  - Live PPE specialist (operator-approved) on both non-compliant images: PARTIALLY_SUPPORTED, citing OSHA 1910.132/135, keeping "non-detection is not proof of absence" and the human override separate.
- **Verified:** new `response/rag/tests/test_cfr_sections.py` (pytest and script); all RAG checks pass.
- **Caveats:**
  - Abstention recalibrated on the rebuilt index (`calibrate_abstention.py`, development set): the threshold is unchanged at 0.5922, and the 12 development cases are still classified 6/6/0/0.
  - OSHA 1910 has no specific high-visibility vest rule; vest guidance rests on the general PPE duty in 1910.132.

---

## 2026-10-12 — Production readiness design and HTTP hardening

- **Design:** `docs/PRODUCTION_READINESS.md`:
  - where the prototype stands, area by area;
  - the target deployment and five decisions for the operator (identity, database, images, OpenAI, hosting);
  - a STRIDE threat model, mapping each threat to existing controls and gaps;
  - the scope and exit criteria for the independent security review;
  - the order of work before real data.
- **Hardening in place** (`http_hardening.py`):
  - security headers on every response (nosniff, no framing, no referrer, opener isolation, permissions policy);
  - `Cache-Control: no-store` on API responses;
  - a per-user limit on OpenAI-backed calls (`DCG_OPENAI_CALLS_PER_MINUTE`, default 10).
  - Only calls that pass authentication and authorization count. The first version counted before login, which would have let anyone use up another user's quota with a forged name; the access matrix exposed it.
- **Checked:** no secrets or keys in tracked files.
- **Verified:** backend pytest 391 passed (new `test_http_hardening.py`).
- **Not done (needs the operator, or an outside party):** the five decisions; the independent security review itself.

---

## 2026-10-12 — Backup routine and keyboard accessibility

- **Backup** (`presentation/backend/app/backup.py`, `create` / `verify`): consistent online copy of the database and ingestion state, retained images, read-only Neo4j export, manifest with hashes, table counts and audit-chain heads. Refuses a location inside the data folder. `verify` checks hashes, SQLite integrity and every audit chain, on a scratch copy (the store helpers create missing tables on connect, which first changed the backup after hashing; caught by the test).
- **Routine** documented in `VALIDATION_AND_OPERATIONS.md`:
  - daily backup and restore check;
  - checkpoints to separate media;
  - weekly checkpoint verification;
  - restore steps.
- **Trial on real data:** 27 tables, 65 nodes / 69 relationships, four chains PASS, 29 MB; verify PASS; trial copy deleted.
- **Keyboard:** form controls and disclosures had no visible focus indicator; they now have one. New `e2e/keyboard.spec.ts`: keyboard-only sign-in, feed, event and investigation controls.
- **Verified:** backend pytest 386 passed (new `test_backup.py`); Playwright 13 passed.

---

## 2026-10-12 — Testing plan item 5: first conversion batch

- **What:** `response/agents/tests` (8 files) and `integration/tests` (4 files) converted from scripts to pytest: one test function per original check (37 and 12 tests, the same count of checks as before, compared file by file); each file keeps a `main()` so `python <file>` still prints its PASSED banner. `pytest.ini` registers the markers `neo4j`, `gpu`, `private_data`; the real PPE/Face Reasoning test is marked `neo4j` and skips with a reason when Neo4j is down.
- **check_all:** the two folders run as pytest suites (one check each, test counts in the summary), so the total is **44 checks** (was 54; the same checks, grouped).
- **Verified:** both folders pass under pytest and as scripts; `check_all.py` 44/44.
- **Remaining:** Response RAG (6, need the local knowledge base), Reasoning (18, Neo4j; follow the graph pilot's fixtures and cleanup), Evidence (27, several need GPU or private data).

---

## 2026-10-12 — Investigation lifecycle

- **What:** `investigation_lifecycle.py` (policy `DCG-LIFECYCLE-v1`, the default chosen on the operator's go-ahead) and `LifecyclePanel.tsx` in the group and single-event detail.
  - States: open → in review → resolved; reopen.
  - Resolving: assigned reviewer or administrator, with a resolution, rationale and acknowledgment.
  - A resolved subject is reported reopened when its Evidence or human verdicts change.
  - Transitions are a fourth hash chain (audit integrity, checkpoints, dev reset); they never change Evidence, verdicts, Decisions or severity.
- **Also:** the shared chain verifier now reports the failing record by each chain's own ID field (it assumed `audit_id`).
- **Verified:**
  - backend pytest 381 passed (new `test_investigation_lifecycle.py`: full cycle, invalid transitions, assignee/administrator rule, required fields, other domains refused, automatic reopen, tampering blocks transitions);
  - Playwright 12 passed (new lifecycle flow; accessibility scans include the panel).

---

## 2026-10-12 — First live runs (operator-approved)

- **Runs** (sends Evidence to OpenAI; approved by the operator): single-event specialists on a non-compliant PPE image and an at-risk drive; Investigator questions on a Face, SSH, maintenance and PPE record, worded to provoke overclaims (presence, compromise, causation).
- **What worked:** the maintenance specialist (PARTIALLY_SUPPORTED, cited); all Investigator answers stayed within bounds (compromise and causation explicitly negated); numbers matched saved detector fields (6 matched, 0 mismatched); usernames, IPs and person IDs were sent as pseudonyms (per-install key created) and shown restored to the operator; all calls recorded in the Investigator audit, chain PASS.
- **Found and fixed:**
  1. Single-Evidence Face context lacked the zone-authorization result, so the Investigator could not say whether P005 was allowed; it is now included (re-run: answer states UNAUTHORIZED from the access graph).
  2. Claim checks flagged a per-person PPE status ("Person 0: COMPLIANT") as a mismatch against the overall NON_COMPLIANT status, and read "Missing PPE: none" as non-compliance; per-person statuses now count, negated "missing" lines are ignored (re-run: 5 matches, 0 mismatches).
  3. Safety retrieval wording reached lockout/tagout and electrical gloves; it now reaches OSHA 1910.132.
- **Open:**
  - **PPE specialist still fails grounding.** The approved safety knowledge is thin: OSHA 1910.132 has 2 chunks, and the one 1910.135 (head protection) chunk is mostly respirator text, apparently a parsing issue. The model claims support but cannot cite, so the check correctly refuses. Needs a knowledge-base source review (re-parse 1910.135, consider further approved PPE sources); not changed here.
  - **Claim checker gap:** a Face answer misdescribed similarity versus a distance threshold, and the claim checker did not catch it. It is an input for measuring the claim checker.
- **Verified:** backend pytest 374 passed (new tests for both fixes); live re-runs as above.

---

## 2026-10-12 — Development workflow guide

- **What:** `docs/DEVELOPMENT_WORKFLOW.md`: the pull-request workflow, the `main` ruleset and why each setting, the two CI jobs and how to read a failure, the GitHub CLI install and login, and the Kaspersky certificate fix for Node tools (`claude rc`, Playwright). Linked from `docs/README.md` and `CLAUDE.md`.

---

## 2026-10-12 — `main` branch protection and GitHub CLI

- **What:** the operator created a repository ruleset on `main`: block deletion and force pushes; require a pull request (0 approvals, merge commits only); require both CI jobs to pass with the branch up to date. GitHub CLI 2.102.0 installed (portable, user folder, checksum-verified) and signed in, so pull requests are opened with `gh pr create`.
- **Why:** CI results were advisory; a failing change could still land on `main`.
- **Verified:** `gh api repos/{owner}/{repo}/rules/branches/main` lists the four rules; this entry was merged through the first protected pull request (#4), which GitHub blocked until both checks passed.
- **CI on `main` had been red** since the Investigator audit merge (`a5592b4`) without anyone noticing, which is exactly what the ruleset now prevents. Two causes, both fixed in #4: Bandit B608 on the audit INSERT (constant placeholders, annotated with the reason), and Investigator history endpoints answering 503 "history disabled" before checking access, which the access matrix caught only in CI (local `.env` enables history). Authorization now runs first; the matrix pins the flag.
- **Also:** Kaspersky intercepts HTTPS; Node-based tools trust its root via the user variable `NODE_EXTRA_CA_CERTS` (fixes `claude rc` and the Playwright browser download).

---

## 2026-10-12 — Accessibility scan (axe-core)

- **What:** `@axe-core/playwright` 4.10.2 (dev dependency, pinned; `npm audit` clean) and `e2e/accessibility.spec.ts`: WCAG 2.1 A/AA scan of sign-in, Monitoring Center, group detail, single-event detail (verdict and specialist panels), Analytics, Review Queue and Scenario Lab; any violation fails with its element.
- **Found and fixed:** colour contrast only: white on the HIGH severity pill was 4.44:1 and on RECOGNIZED 4.14:1 (minimum 4.5:1); backgrounds darkened to `#C93360` (5.09:1) and `#287D5C` (5.03:1). The scan's flow also exposed an interaction bug: clicking a single event while a correlation group was open did not show its verdict and specialist panels; single-event rows now close open correlation views.
- **Verified:** Playwright 11 passed (in CI with the other browser tests).
- **Limits:** automated scans catch only part of accessibility problems; keyboard-only use and screen-reader wording still need a manual review.

---

## 2026-10-12 — Investigator pseudonyms for usernames, IPs and person IDs

- **Operator decision:** mask all three before anything leaves for OpenAI.
- **What:** `investigator_pseudonyms.py`, applied in `ask_model` after `minimize`: keyed HMAC pseudonyms (`USER-`, `IP-`, `PERSON-` + 10 hex), stable across calls; IPv4 addresses and person IDs inside free text and the operator's question are masked too; the answer is mapped back locally; the model is told to use pseudonyms verbatim. Key: `DCG_PSEUDONYM_SALT` or `presentation/backend/data/.investigator_pseudonym_key` (created on first use, not committed).
- **Verified:** backend pytest 372 passed; the privacy tests now assert no person ID, IP or username in the payload (Face and SSH), identical pseudonyms across calls, and real values restored in the operator's answer.
- **Caveat:** usernames inside free text are masked only once the same username appears in a username field of the context.

---

## 2026-10-12 — Access policy decisions applied

- **Operator decisions:** (1) maintenance and environment feeds require `maintenance:detail` / `environment:detail`, like the other domains (they were readable by every role in its zones); (2) each domain's operator uploads its own domain: maintenance/environment validation needs the domain's detail permission and SSH log validation, processing, publication and pipeline steps need `ssh:detail` (all previously `scenario:execute`, administrators only). Declaring controlled metadata (SSH controlled time, image capture declarations) stays administrator-only.
- **Tests:** `test_domain_feed_http_rbac` now asserts 403 for viewer/security/safety on those feeds and zone filtering for operations engineers; the access matrix encodes the new policy and now sends a real zone/server in request bodies (the dummy zone had made some uploads fail the zone check instead of the permission check).
- **Verified:** backend pytest 371 passed.

---

## 2026-10-11 — External audit checkpoints

- **What:** `audit_checkpoint.py` (CLI `write` / `verify`): records each audit chain's length and head hash (group reviews, Evidence verdicts, Investigator calls) in a JSON file stored outside the data folder, optionally HMAC-signed with `DCG_CHECKPOINT_KEY`. `verify` checks each chain is intact and still holds the checkpointed record at the checkpointed position.
- **Why:** the chains alone could not detect deletion of the newest records or replacement of the database (documented limitation since the audit was introduced).
- **Verified:** backend pytest 365 passed (new `test_audit_checkpoint.py`: added records pass, tail deletion and database replacement fail, forged signed checkpoint rejected, refuses a location inside the data folder); read-only snapshot and verify on the local data: PASS (1 group review, 4 verdicts, 0 Investigator calls).
- **Operator to decide:** where checkpoints are kept and how often they are written.

---

## 2026-10-11 — Investigator claim checks, outbound privacy, call audit

- **Claim checks** (`investigator_claim_checks.py`): every mode returns `claim_checks`: boundary claims (causation, identity, physical presence, compromise, autonomous action) flagged VIOLATION / NEGATED / HEDGED, and detector-state wording compared with the record and its human verdict (multi-member domains skipped). Shown under each answer in the Investigator panel (opens automatically on a violation or mismatch).
- **Privacy review:** the single-Evidence Face context sent `facial_area` (face box and eye/nose/mouth landmarks). `investigator_audit.minimize` now strips biometric, identity, rationale and credential fields at the one outbound point for all modes. Still sent, for the operator to decide: SSH attempted usernames and source IPs, pseudonymous person IDs. Table of what each mode sends in `AI_INVESTIGATOR.md`.
- **Call audit:** `investigator_audit` table, hash-chained, one row per OpenAI call (answered or failed) with payload/answer SHA-256 and claim status; verified by `/api/v1/reviews/audit-integrity` and shown in the audit panel. Added to the dev reset.
- **Verified:** backend pytest 360 passed (new `test_investigator_claim_checks.py` with 15 labelled answers and mode wiring; `test_investigator_privacy_audit.py` with a fake OpenAI client: no landmarks/embedding/reviewer/rationale in the payload, exact payload hash audited, failures audited, tampering detected); build; Playwright 9 passed. No live OpenAI call.
- **Caveats:** pattern-based; precision/recall on real Investigator answers not yet measured.

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
| 5 | Convert remaining script tests (Evidence, Response, integration) after the pilot is reviewed | Single runner, per-test results, selectable tests | **Done** 2026-10-12: every test runs under pytest (agents and integration one test per check; 55 Evidence/RAG/Reasoning files module-level, shown equivalent); see `docs/TESTING.md` |

Rule for conversions: the same checks must still run — assertion counts are compared before and after.
