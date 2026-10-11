# DC-GUARDIAN — Reasoning under uncertainty (Bayesian correlation)

**Updated:** 2026-10-11  
**Branch:** developed on `feature/uncertainty-reasoning` (from `bf37dba`), merged into `feature/presentation-dashboard` on 2026-10-11  
**Status:** research component with contract tests and an offline evaluation. Not yet wired into the dashboard, the Decision layer or Neo4j.

## Why

The frozen Reasoning rule is crisp: two abnormal events in different domains correlate when they share a declared zone and are at most 15 minutes apart. Real incidents are messier. A cooling fault can stress a drive 30–50 minutes later in another hall, and two strong alerts can share a zone by pure coincidence. A crisp rule cannot express "probably related" or explain why.

This component estimates **P(Related)**, the probability that two abnormal events belong to the same incident, with a Bayesian network built from documented expert knowledge. It runs beside the crisp rule; it does not replace it.

## Design

```text
Abnormal event pair
   │
   ├─ TimeGap          ≤5 min · ≤15 min · ≤60 min · >60 min
   ├─ Topology         same server · same rack · same zone · cooling dependency · unrelated
   ├─ DomainMechanism  known · possible · unlikely
   └─ EvidenceStrength both strong · mixed · both weak
   │
   ▼
Bayesian network (hidden cause "Related" → four observed factors)
   │
   ▼
P(Related) + per-factor likelihood ratios (explanation)
```

| File | Role |
|---|---|
| `reasoning/uncertainty/knowledge_base.json` | All expert knowledge: prior, conditional probability tables, domain mechanisms, evidence-strength rules, cooling dependency. Each entry carries its rationale or source. |
| `reasoning/uncertainty/bayesian_network.py` | Small dependency-free discrete Bayesian network with exact inference by enumeration. Missing factors are marginalized, never guessed. |
| `reasoning/uncertainty/bayesian_correlation.py` | Feature extraction, `score_pair()` with explanation, and `crisp_correlated()` reproducing the frozen rule for comparison. |
| `reasoning/uncertainty/scenarios/` | Builder and the 40 labelled scenarios. |
| `reasoning/uncertainty/evaluate.py` | Evaluation; writes `results/evaluation_report.md` and `results/evaluation_results.json`. |
| `reasoning/uncertainty/test_uncertainty_reasoning.py` | 15 contract tests, included in `check_all.py`. |

### Knowledge acquisition

Every number in the model is traceable to a stated source, which the knowledge base records next to it.

| Knowledge | Source |
|---|---|
| Evidence strength per domain | Each detector's frozen evaluation: SSH two-of-three consensus precision 1.000 vs. single-vote candidates; maintenance probability ≥ 0.70 (operating threshold 0.45, holdout precision 3.4 %); dedicated sensors vs. hardware telemetry (existing Reasoning independence rule); graph-derived `UNAUTHORIZED` vs. `UNKNOWN_PERSON`; PPE confidence ≥ 0.75 (recall 0.524). |
| Domain mechanisms | Data-center operations practice: heat → drive wear, unauthorized access → console attack, intruder → missing PPE (known); engineer visit, alarm response, tampering (possible); cyber with environmental, maintenance or safety (unlikely). |
| Time and topology tables | "Related" rows: expert estimates. "Unrelated" rows: chance rates, following bin widths in a 120-minute window and the three-zone layout. |
| Cooling dependency | Synthetic assumption: CHILLER-C1 in ZONE-C cools ZONE-A and ZONE-B. Declared in the knowledge base because the frozen DC-01 topology has no cooling-service relationship. |

The network uses a naive-Bayes structure: the four factors are conditionally independent given "Related". This keeps every score explainable as a product of likelihood ratios:

```latex
\frac{P(R \mid f)}{P(\neg R \mid f)} = \frac{P(R)}{P(\neg R)} \prod_{i} \frac{P(f_i \mid R)}{P(f_i \mid \neg R)}
```

Example: a dedicated Hall A heat sensor and a high-risk drive in the same hall nine minutes apart score 0.90. Same zone (×1.6), ≤ 15 minutes (×3.75), known mechanism (×2.17) and both strong (×2.75) outweigh the 0.2 prior.

### Boundaries

The probability is the plausibility of a shared incident under an expert model. It does not establish causation, identity, presence or compromise, and it never changes detector Evidence, correlation records or Decision severity.

## Labelled scenarios

40 scenarios of the synthetic DC-01 data center, each a 120-minute window with 2–4 abnormal events (102 events, 85 cross-domain candidate pairs, 44 truly related). Every event carries a `ground_truth_incident` label written from the scenario narrative; `null` marks unrelated background abnormalities. The model never reads the label, and a test enforces that.

Scenarios cover true incidents (cooling cascades, intrusions followed by console attacks, tailgaters without PPE, engineers dispatched to failing drives, fire and leak responses), coincidences (internet scanners, seasonal humidity, worn drives next to unrelated visitors), two simultaneous incidents in one hall, and hard cases where either method should fail.

- **dev (16):** written first and used while writing the model code. While writing them, the author worked out the Bayesian score by hand for seven of them (D06, D07, D08, D12, D13, D15, D16) to check that they were informative cases. Dev results are therefore not independent of the model.
- **test (24):** written afterwards without scoring them. **Cite the test split.**

The knowledge base, scenarios and model code were committed (`c0b9dc3`) before the evaluation script and results (`22119f2`), and the knowledge base has not changed since. Both commits come from one working session three minutes apart, so the commit order shows only that the knowledge base was not changed after it was committed; it cannot show that no scenario was scored before that commit. Independent labelling (see Limitations) is the stronger safeguard.

## Results

Regenerate with `python reasoning/uncertainty/evaluate.py`; the full per-pair table is in `reasoning/uncertainty/results/evaluation_report.md`.

**Pair-level correlation, test split (59 pairs, 28 related):**

| Method | Precision | Recall | F1 | False positives | Missed |
|---|---:|---:|---:|---:|---:|
| Crisp rule (frozen) | 0.615 | 0.571 | 0.593 | 10 | 12 |
| Bayesian, P ≥ 0.5 | **0.792** | **0.679** | **0.731** | 5 | 9 |

On the dev split the Bayesian model also leads (F1 0.706 vs 0.647), but some dev scenarios were scored by hand while being written, so that figure is not independent evidence. Across all 85 pairs: 0.721 vs 0.614. The Bayesian probability ranks pairs well without any threshold: test average precision 0.829, ROC-AUC 0.838.

**Operator view, test split (18 incidents):**

| Method | Alerts shown | Incidents fully linked | Linked cleanly |
|---|---:|---:|---:|
| Single-domain alerts | 65 | – | – |
| Crisp rule | 44 | 11 | 10 |
| Bayesian | 43 | 12 | 10 |

Correlation of either kind cuts alerts by about a third against single-domain alerting. The Bayesian gain at operator level is small (one fewer alert, one more incident linked); its main benefit is fewer wrong links.

**Robustness (test split):**

- Removing any one factor drops F1 to 0.588–0.605, roughly the crisp level, so all four factors contribute.
- Perturbing every probability with log-normal noise (σ 0.3, 200 draws) gives F1 median 0.704, 5th–95th percentile 0.578–0.815; 87 % of perturbed models still beat the crisp rule. The result does not hinge on the exact expert numbers.

## What the errors show

- **Long cooling cascades are still missed.** Chiller-to-drive links 33–55 minutes apart score 0.18–0.41 (T02, T09, T19, D03). The time table treats all long gaps alike, but cascades are slow by nature. A better structure would make TimeGap depend on Topology, which is a natural next step but was not tuned in, to keep the evaluation honest.
- **Strong coincidences fool both methods.** An internet break-in and an unrelated worn drive on the same server two minutes apart score 0.92 (T13). Same-server, tight-time evidence outweighs the "unlikely" mechanism.
- **Weak mechanisms can hide real links.** An intruder's missing PPE and their console attack score 0.49 (D16) because the safety–cyber pair is "unlikely". The incident is still linked as one group through the face event, which is why the group-level view matters.
- **Two strong concurrent incidents in one hall fool both methods.** In D09 every cross-incident pair scores 0.69–0.90, because the events are strong, close in time and in the same hall.
- **The Bayesian model removes crisp false positives** where weak or implausible pairs share a zone (D06, D15, T05, T23 and most of T08). One weak pair still passes: a visitor and a scanner three minutes apart score 0.71 (T18) because their mechanism is "known". It also recovers incidents that unfold over 16–40 minutes in one hall (D08, D14, T10, T15).

## Limitations

- **Author-labelled scenarios.** The same author wrote the knowledge base and the scenarios, so there is a risk of shared assumptions. Seven dev scenarios were also scored by hand while being written. Unscored test scenarios, the unchanged knowledge base and the sensitivity analysis reduce but do not remove this risk. Independent labelling by a classmate or practitioner would strengthen the result.
- **Small sample.** 59 test pairs; a difference of a few pairs moves F1 by several points. No confidence intervals are claimed.
- **Synthetic setting.** One three-zone topology and an assumed cooling dependency; no real multi-domain data exists for the project.
- **Naive structure.** Conditional independence of the four factors is a simplification (time and topology interact in cascades, as shown above).
- **Fixed threshold.** 0.5 was set in the knowledge base in advance; a deployment would choose it from the cost of a missed incident versus a false link.
- **Offline only.** Not yet connected to Neo4j, the presentation backend or the Decision rules.

## Integration path (not implemented)

1. Score live pairs in `presentation/backend/app/correlation_pairs.py` and show P(Related) and the factor explanation beside each crisp candidate.
2. Keep the crisp rule as the authoritative candidate filter until the probabilistic score has been validated on independently labelled data.
3. Never feed P(Related) into Decision severity without a new, versioned Decision policy.
