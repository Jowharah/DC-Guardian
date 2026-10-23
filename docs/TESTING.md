# DC-GUARDIAN — Testing guide

**Updated:** 2026-10-23. Every automated test in the repository runs under **pytest**. The only exceptions are the two verification tools `verify_runtime.py` and `response/rag/verify_response_rag.py`, which stay scripts, and the browser tests, which use Playwright.

## 1. What runs where

| Suite | Location | Runs with | Notes |
|---|---|---|---|
| Evidence | `evidence/*/tests/` | main environment | Detector configs, artifacts, frozen evaluations |
| Evidence, GPU | 3 PPE files, 1 GRU file | `.venv-ppe`, `.venv-gru` | Marked `gpu`; skipped in the main environment |
| Reasoning contracts | `reasoning/` (adapters, topology, graph, correlation) | `reasoning/run_contract_tests.py` | Runs each contract with pytest **in dependency order** (correlation-store contracts use scenarios created by the contract before them); removes its `SCENARIO-*` test nodes afterwards |
| Uncertainty study | `reasoning/uncertainty/` | main environment | Bayesian correlation contracts, labelling pack |
| Response RAG | `response/rag/tests/` | main environment | Most need the locally rebuilt knowledge base (`private_data`) |
| Response agents | `response/agents/tests/` | main environment | One test per check (37) |
| Decision / integration | `integration/tests/` | main environment | One test per check (12); one module needs Neo4j |
| Presentation backend | `presentation/backend/tests/` | main environment | Isolated database per test (`conftest.py`), OpenAI blocked |
| Frontend | `presentation/frontend/e2e/` | Playwright | Mocked API; 24 tests, including WCAG and keyboard tests and one test per usability-study change (`usability-findings.spec.ts`) |

`python check_all.py` runs all of them (14 checks) and writes `logs/checks/<time>/report.md`; each check's log lists every test and every skip reason. CI runs the same script.

## 2. Markers and automatic skips

Defined in `pytest.ini` and enforced by the repository-root `conftest.py`. They work the same locally, in CI and on a fresh clone:

| Marker | Meaning | Skipped when |
|---|---|---|
| `private_data(*paths)` | Needs local data excluded from Git (face enrollment, datasets, RAG knowledge base) | A listed path is missing |
| `gpu` | Needs a CUDA PyTorch component environment | The interpreter has no CUDA |
| `neo4j` | Needs a running Neo4j | Neo4j cannot be reached |

Examples:

```powershell
python -m pytest evidence -q -rs                     # all Evidence tests, with skip reasons
python -m pytest -m "not neo4j" integration/tests   # without the database
.venv-ppe\Scripts\python.exe -m pytest evidence\ppe_detection\tests\test_ppe_runtime_pipeline.py -q
python reasoning\run_contract_tests.py               # Reasoning, in order
python evidence\predictive_maintenance\tests\test_config.py   # any test file still runs alone
```

`pytest.ini` sets `--import-mode=importlib` and `pythonpath = .`, because several Evidence folders have test files with the same name (`test_config.py`, `test_final_test_artifact.py`).

## 3. How the scripts were converted (2026-10-12)

The script tests were long programs that printed `PASS` lines and stopped at the first failed `assert`. They were converted without changing what they check:

1. **Fine-grained (one test per check):** `response/agents/tests` (8 files → 37 tests), `integration/tests` (4 → 12), the Reasoning graph pilot (2 files), the uncertainty study, and `test_cfr_sections.py`.
2. **Module-level (55 files):** each straight-line script body moved, unchanged, into one `test_<name>_contract()` function. Scripts that already had a `main()` got a test that calls it. Lines inside multi-line strings were not re-indented, so no string changes; a `__main__` guard keeps `python <file>` working.
3. **A trap that was caught:** six scripts ran their checks inside `if __name__ == "__main__":`. Once wrapped in a function, that block would not run under pytest, so its checks would have silently passed. These guards were made unconditional (`if True:  # the script's former __main__ block`).
4. **Proof of equivalence:**
   - the number of `assert` and `raise` statements per file is identical before and after (889 asserts and 133 raises across the 55 converted files);
   - every file prints exactly the same `PASS` lines as a script and under pytest (`pytest -s`): 55 of 55 files identical, including the four GPU files in their component environments;
   - all suites pass.

Module-level conversion means one pytest result per file for those 55 files: the first failing check still stops that file, as it did before. Splitting them into one test per check is optional further work. Follow the agents/integration style: shared fixtures, then one test per check, and compare the `PASS` lines before and after.

## 4. Writing new tests

- Write pytest functions (`def test_...`), one behaviour per test, with shared setup in fixtures.
- Reasoning graph tests: use the `neo4j_driver` fixture and `graph_test_support.cleanup_graph(...)` (see `reasoning/graph/test_event_ingestion.py`), so a test removes its own nodes, pass or fail.
- Mark tests that need private data, a GPU or Neo4j, so they skip with a reason instead of failing.
- Never call OpenAI from a test: patch the client (see `test_investigator_judge.py`) and keep `DCG_INVESTIGATOR_ENABLED=0`.
- Backend tests never touch the real database: `presentation/backend/tests/conftest.py` isolates storage per test.
