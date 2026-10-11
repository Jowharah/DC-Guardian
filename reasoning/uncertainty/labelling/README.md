# Independent labelling of the uncertainty scenarios

The 40 scenarios in `../scenarios/labelled_scenarios.json` were written and labelled by the same author as the Bayesian model, and seven dev scenarios were scored while being written. Independent labels from a teammate are the strongest available check of the result.

The scenario file cannot be shared as-is: its titles and narratives state the answers. This folder provides a blind version.

## For the group: how to run a labelling round

1. **Send the labeller only the `pack/` folder** (zip it): `INSTRUCTIONS.md`, `scenarios_blind.md`, `labels.csv`. Do not send a link to the repository; it contains the answers.
2. The labeller reads `INSTRUCTIONS.md`, fills `related` (Y/N), `confidence` (1–3) and an optional `note` for all 85 rows of `labels.csv`, working alone. About 60–90 minutes.
3. Save the returned file somewhere outside `pack/` and score it:

   ```powershell
   python reasoning/uncertainty/labelling/score_labels.py path\to\returned_labels.csv --name <labeller-code>
   ```

4. Commit `results/<labeller-code>.md` and `.json` (use a code, not a full name, if the group prefers), and record the round in `docs/WORK_LOG.md`.

Two or more labellers make the result stronger: compare their reports, and discuss the listed disagreements as a group **after** all labels are in.

## What the score shows

- **Agreement with the author** (percent and Cohen's kappa). Kappa above about 0.6 is usually read as substantial agreement; lower values mean "related" is ambiguous in these scenarios.
- **Crisp rule vs Bayesian model against the independent labels**, with 95% scenario-bootstrap intervals. The **test split** is the result to cite.
- **Consensus pairs**: the same comparison on pairs where author and labeller agree.
- **Disagreements**: every pair where the labeller and author differ, with the model's P(Related).

## Files

| File | Purpose |
|---|---|
| `pack/` | What the labeller receives. Regenerate with `build_labelling_pack.py` (deterministic). |
| `pack_key.json` | Maps neutral IDs (S01-E1) to original IDs (D01-E1) and splits. Never send it to a labeller. |
| `build_labelling_pack.py` | Builds the blind pack from the scenarios and the facility topology. |
| `score_labels.py` | Validates and scores a returned `labels.csv`. |
| `test_labelling_pack.py` | Checks the pack reveals no answers, covers every pair, and that the scorer reproduces the published results. |
| `results/` | One report per labeller. |
