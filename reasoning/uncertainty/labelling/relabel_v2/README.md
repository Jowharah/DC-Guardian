# Blind relabelling of the 8 rewritten scenarios (scenario set v2)

Scenario set v2 (`../../scenarios/labelled_scenarios_v2.json`) replaced the leak, smoke, airflow and cooling alerts with the temperature or humidity readings the real environmental detector would give. These 8 scenarios were changed:
- dev: D03, D10, D14;
- test: T02, T09, T12, T19, T22.

What an operator would conclude from heat or humidity alone may differ from what they would conclude from a leak or smoke alarm, so their labels are redone blind. The old labels are not reused, and until new labels exist these scenarios are marked `PENDING_BLIND_RELABEL` and carry no ground truth.

## Round 1: operator labels (the new author labels)

1. Open only `pack/`: `INSTRUCTIONS.md`, `scenarios_blind.md`, `labels.csv` (20 rows, about 10–15 minutes). Do not look at `pack_key.json`, the v1 scenario file or the extended-sensor file while labelling.
2. Fill `related` (Y/N), `confidence` (1–3) and an optional `note` in a copy of `labels.csv`.
3. Save the copy here as `operator_labels.csv`, then run:

   ```powershell
   python reasoning/uncertainty/scenarios/build_scenarios_v2.py
   ```

   The script turns the pair labels into incident labels: events joined by Y pairs form one incident. If two events end up in one incident although you marked them N, it stops and names the pair, so you can resolve it.

## Round 2: ChatGPT comparison labels

Paste the same `pack/` files into ChatGPT, as in the first round (`../results/llm-chatgpt.md`), and save its filled sheet as `../results/llm-chatgpt-v2_labels.csv`. Nothing in this repository calls OpenAI for this.

## Then

Re-run the uncertainty evaluation and the baseline comparison on v2. Report v1 and v2 results side by side (`docs/WORK_LOG.md`, `docs/report/evaluation_baseline_and_latency.md`). The extended-sensor set (`../../scenarios/extended_sensor_scenarios.json`, v1 labels) is reported apart, as future-work evidence.

Rebuild this pack with `python reasoning/uncertainty/labelling/build_relabel_pack.py` (deterministic; a test checks it is current).
