# CLAUDE.md — working on DC-GUARDIAN

Read this first in every session (Claude Code locally or on the web). Then read `docs/WORK_LOG.md` for what changed recently and what is planned.

## What this project is

A research project **and** an industrial prototype for multi-domain data-center monitoring. Layers, in order:

| Layer | Folder | What it does |
|---|---|---|
| Evidence | `evidence/` | Five frozen detectors: SSH anomaly, PPE (YOLOv8n), Face (ArcFace), predictive maintenance (Temporal RF v2), environmental thresholds |
| Reasoning | `reasoning/` | Common event schema, synthetic DC-01 topology, Neo4j graph, deterministic correlation; `reasoning/uncertainty/` is an offline Bayesian correlation study |
| Response | `response/` | Approved-knowledge RAG and grounded specialist agents |
| Decision | `decision/` | Deterministic severity rules: `rules.py` (DCG-DECISION-v1, saved SSH/operational/pipeline Decisions) and `rules_v2.py` (DCG-DECISION-v2, single events in every domain and unified groups) |
| Presentation | `presentation/` | FastAPI backend + React/Vite dashboard: Monitoring Center, Review Queue, AI Investigator |

Default branch: **`main`** (current code; CI runs on every push). Work happens on short-lived branches from `main`, merged back by pull request. Retired branches are kept as `archive/*` tags.

## Non-negotiable rules

- **Never modify frozen detector output or model artifacts.** Human verdicts and re-evaluations are stored beside them, never in them.
- **Correlation is contextual.** Never claim causation, identity, physical presence or compromise from shared zone/time.
- **Severity comes only from deterministic rules,** never from an LLM, a specialist, or a human typing a level. Group severity is DCG-DECISION-v2: most severe member, +1 level only for linked evidence; it is "validated on author labels; independent labels pending" and must be shown with that caveat. v1 stays unchanged so saved Decisions remain reproducible; change rules only as a new version.
- **No autonomous action** anywhere.
- **Keep research claims precise.** State what evidence shows and what it cannot show (see the uncertainty doc for an example).
- **Never commit** `.env`, `logs/`, `presentation/backend/data/`, datasets, face photos or enrollment embeddings.
- **Never call OpenAI from tests or checks.** Keep `DCG_INVESTIGATOR_ENABLED=0` when testing; ask the operator before any live Investigator or specialist call (it sends Evidence to OpenAI).

## Environment (operator's Windows PC)

- Python 3.12 in `.venv-dc-guardian` (main). Component environments: `.venv-ppe` and `.venv-gru` (GPU PyTorch), `.venv-face`.
- Neo4j 2026.08.1 at `bolt://127.0.0.1:7687`. Use `127.0.0.1`, not `localhost` (about 2 s slower per connection on Windows).
- Settings come from `.env` (template: `.env.example`). Real environment variables take precedence; `.env` is optional.
- Run the app:
  - Backend: `python -m uvicorn presentation.backend.app.main:app --host 127.0.0.1 --port 8000 --reload`
  - Frontend: `cd presentation/frontend && npm run dev` (port 5173, proxies `/api` to 8000)
  - If a backend change does not show up, restart uvicorn; `--reload` has missed changes before.

## How to verify (always, before saying something works)

```powershell
python check_all.py              # every layer, ~3 min; report in logs/checks/latest.md
python check_all.py --only <x>   # checks whose name contains <x>
```

- Locally all **54** checks run (including the Playwright browser tests). A fresh clone or CI skips GPU, private-data and RAG-knowledge-base checks with a stated reason; CI (`.github/workflows/ci.yml`) runs the rest on every push.
- Narrower runs: `python -m pytest presentation/backend/tests -q`, `python reasoning/run_contract_tests.py` (needs Neo4j; removes its `SCENARIO-*` test nodes afterwards), `npm run build` and `npm run test:e2e` (Playwright browser tests, mocked API, local Edge) in `presentation/frontend`.
- Most Evidence, Reasoning, Response and integration tests are **scripts** (run with `python <file>`). The pytest pilot (`reasoning/graph/conftest.py`, SSH and maintenance ingestion) shows the target style: shared fixtures, per-test results, cleanup of the test's own graph nodes. New Reasoning graph tests should follow it.
- CI gates on Bandit (medium/high), pip-audit and `npm audit` (high). Annotate a reviewed-safe Bandit finding with `# nosec <code>: <reason>`; never suppress without a reason.
- Backend runtime logs: `logs/errors.log` (start here), `logs/api_access.log`, `logs/backend.log`.

## Conventions

- **Work on a short-lived branch from `main`** (`feat/<topic>`, `fix/<topic>`, `docs/<topic>`, `test/<topic>`), push it, and open a pull request into `main`. CI must be green; the operator reviews and merges with **Create a merge commit** (never squash or rebase: the docs cite commit hashes). Delete the branch after merging.
- **Record every change in `docs/WORK_LOG.md`:** what, why, commit, how verified, caveats. Update the testing-plan status there when items land.
- Update the relevant doc (`docs/README.md` indexes them) when behaviour or contracts change.
- Commit messages: `type(scope): summary` (`feat`, `fix`, `test`, `docs`, `ci`, `perf`, `chore`, `ui`), with a body explaining why.
- Backend tests must never touch the real database: `presentation/backend/tests/conftest.py` isolates storage; keep it that way.
- **Line endings:** the repo stores LF and Windows checks out CRLF. Integrity-checked text artifacts are pinned byte-for-byte with `-text` in `.gitattributes`; never re-save them.
- Correlation group IDs hash their membership: changing correlation rules can create new group IDs, which need their specialist evaluation re-run.

## Where to look

- `docs/WORK_LOG.md`: dated changes and the testing plan
- `docs/README.md`: documentation index
- `docs/AI_INVESTIGATOR.md`: Investigator, verdicts, field checks, group severity
- `docs/REMAINING_ROADMAP.md`: open work and acceptance rules
- `docs/UNCERTAINTY_REASONING.md`: Bayesian correlation study
- `docs/VALIDATION_AND_OPERATIONS.md`: commands and validation results
