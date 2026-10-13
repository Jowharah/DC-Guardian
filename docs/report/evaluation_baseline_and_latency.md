# Evaluation against single-domain monitoring, and pipeline latency

*Draft report section (2026-10-13). Generated results: `presentation/backend/validation/results/baseline_comparison.md` (v1), `baseline_comparison_v2.md` and `baseline_comparison_v2_chatgpt.md` (scenario set v2), and `latency_benchmark.md`; reproduce with the scripts of the same name.*

## 1. Does correlation improve on isolated single-domain monitoring?

The proposal asks whether combining multi-domain Evidence with graph context and deterministic rules improves incident correlation and prioritisation compared with isolated single-domain monitoring. We compared the two on the 40 labelled scenarios of the uncertainty study (DC-01 topology, 102 abnormal events, 31 labelled incidents; 32 events belong to no incident).

**Design.** The protocol was fixed before any result was computed.
- **Isolated monitoring:** each abnormal event is its own alert.
- **DC-GUARDIAN:** correlated events form one alert per group, with the DCG-DECISION-v2 group severity.
- **Same single-event policy:** both systems use the same v2 single-event severities, so the comparison isolates the effect of correlation and group severity.
- **Queue:** each system's alerts are sorted by severity. Ties are broken at random, averaged over 500 orders.
- **Relevance:** an alert is relevant when it contains an event of a labelled incident.
- **Primary result:** the held-out test split (24 scenarios, 18 incidents). The dev split was used to select the v2 linkage rule.

**Results on the held-out test split.** The difference is DC-GUARDIAN minus isolated, with a 95% bootstrap interval over scenarios.

| Measure | Isolated | DC-GUARDIAN | Difference (95% CI) |
|---|---:|---:|---|
| Alerts shown | 65 | 44 | −21 (−29 to −14) |
| Alerts with no incident event | 23 | 16 | |
| Incidents shown whole in one alert | 0 of 18 | 11 of 18 | |
| Mean alerts per incident | 2.33 | 1.56 | |
| Share of top-severity alerts that are incidents | 64% (MEDIUM) | 86% (HIGH) | |
| Average precision of the review queue | 0.66 | 0.74 | +0.08 (+0.02 to +0.18) |
| Alerts reviewed until every incident event has been seen | 64.5 | 43.4 | −21 (−29 to −14) |
| Mean queue position where an incident is first seen | 22.5 | 15.4 | |

**Interpretation.**
- **Correlation reduces workload:** 32% fewer alerts.
- **Incidents arrive whole:** 11 of the 18 multi-event incidents reach the operator as one alert instead of fragments.
- **Real incidents come first:** linked groups are the only alerts that reach HIGH, and 86% of HIGH alerts are real incidents.
- **Every interval excludes zero.**
- **The dev split points the same way** (16 scenarios):
  - 37 alerts become 23;
  - average precision rises from 0.67 to 0.71;
  - 9 of 13 incidents appear whole.

**Scenario set.** The figures above use scenario set v1. Eight of its 40 scenarios (five in the test split) include leak, smoke, airflow or cooling alerts that the prototype's environmental detector cannot produce. Scenario set v2 replaces them with the temperature or humidity readings the detector would give. All 40 v2 scenarios were relabelled blind from events alone, by the same author (so the labels are still not independent) and, as a sensitivity check, by ChatGPT on the same pack. The 8 original scenarios are kept apart as evidence of what extra sensors would add.

**The same comparison on v2 (held-out test split).** Reproduce with `baseline_comparison.py --set v2` and `--set v2-chatgpt`.

| Measure | v1, author labels | v2, author blind relabel | v2, ChatGPT labels |
|---|---|---|---|
| Labelled incidents | 18 | 18 | 9 |
| Alerts shown, isolated → DC-GUARDIAN | 65 → 44 | 65 → 44 | 65 → 44 |
| Alerts with no incident event | 23 → 16 | 25 → 21 | 45 → 34 |
| Incidents shown whole in one alert | 0 → 11 | 0 → 14 | 0 → 8 |
| Share of top-severity alerts that are incidents | 64% → 86% | 77% → 100% | 50% → 86% |
| Average precision of the review queue | 0.66 → 0.74 | 0.73 → 0.81 | 0.48 → 0.75 |
| Difference in average precision (95% CI) | +0.02 to +0.18 | +0.02 to +0.19 | +0.10 to +0.50 |
| Alerts reviewed until every incident event seen | 64.5 → 43.4 | 64.2 → 42.2 | 61.5 → 32.8 |

- **The conclusion holds under all three labellings:** fewer alerts, more incidents shown whole, a cleaner top severity level, and an average-precision gain whose interval excludes zero.
- **The size of the gain depends on who labels.** The two v2 labellings agree on 73% of pairs (Cohen's kappa 0.46). ChatGPT marks half as many pairs related, mainly because it does not count heat or humidity followed by a drive at risk as one incident, so many more isolated alerts become noise and the gain looks larger.
- **Not independent:** the v2 author labels were written after discussing how the system links events, and ChatGPT is a language model's second opinion. Independent human labels are still the main missing evidence.
- **Correlation method:** under the v2 labels the Bayesian model's advantage over the crisp rule is no longer statistically clear (see `docs/UNCERTAINTY_REASONING.md`). The comparison here uses the crisp rule, as the live system does.

**Limits.**
- **Synthetic data:** the scenarios and topology are synthetic.
- **Author labels:** the relatedness labels, the scenarios and the known-mechanism list all come from the same author. ChatGPT's labels on v2 are a second opinion, not independent validation; an independent human labelling round is pending.
- **No severity labels:** the scenarios have no severity labels, so this tests ranking, not whether each level is right.
- **The baseline is DC-GUARDIAN's own single-event policy, not a commercial tool:** the result measures the value added by correlation.
- **Response recommendations are not covered:** they need a user evaluation.

## 2. Pipeline latency

Measured on the operator workstation (Windows 11, RTX 3080 Ti, single user). The controlled benchmark ran 10 timed runs per stage. The observed figures come from the backend access logs: about 75,000 requests over three days of development use. The benchmark itself makes no language-model calls.

| Stage | Median | Note |
|---|---:|---|
| SSH log inference (2,000 lines) | 4.1 s | New worker process per upload |
| PPE image inference (YOLOv8n) | 4.2 s | GPU environment, model loaded per upload |
| Face image inference (ArcFace) | 10.1 s | Model loaded per upload |
| Drive history inference (Temporal RF v2) | 0.06 s | In process |
| Sensor threshold assessment (60 readings) | 0.01 s | In process |
| Neo4j ingestion of two events + correlation | 0.05 s | Controlled SSH and drive-risk events |
| DCG-DECISION-v2 group decision | 8 µs | Deterministic rule |
| Unified correlation feed (observed) | 0.10 s | p95 0.16 s |
| Single-event specialist, OpenAI + RAG (observed, n = 3) | 12.5 s | Operator-initiated |
| Three specialists for a group (observed, n = 3) | 23.9 s | Operator-initiated |
| Investigator question (observed, n = 86) | 3.2 s | p95 4.5 s |

**Upload to dashboard:** an SSH upload is processed in about 4.3 s, and the dashboard refreshes every 5 s, so the operator sees the result within about 9 s.

**Where the time goes:** detector start-up and inference dominate. Each upload starts a new worker process that loads its model, which keeps the component environments isolated. Graph reasoning, correlation and Decision rules add well under a second. The language-model steps take several seconds, but they run only when the operator asks.

**Limits:**
- one machine and one user;
- no load or concurrency test;
- few observed specialist calls;
- language-model latency depends on the provider at the time.

Production hosting would change these figures (see the industrial deployment section).
