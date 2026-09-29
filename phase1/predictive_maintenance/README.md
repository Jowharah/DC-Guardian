# DC-Guardian — Predictive Maintenance

## Overview

The DC-Guardian Predictive Maintenance model is a Phase 1 machine-learning component designed to identify hard drives at elevated risk of explicit failure within the next seven days.

The model uses historical SMART telemetry from the Backblaze Hard Drive Dataset and produces a structured drive-health assessment for downstream DC-Guardian components.

The final selected model is a Temporal Random Forest using current SMART measurements, health indicators, and historical change features.

---

## 1. Prediction Task

The prediction target is:

> Will this hard drive experience an explicit recorded failure within the next seven days?

Each drive-day observation is classified into one of the following labeling states during dataset construction:

- `NORMAL`
- `AT_RISK`
- `FAILURE_DAY`
- `POST_FAILURE`
- `CENSORED`

For predictive modeling:

- `NORMAL` → target `0`
- `AT_RISK` → target `1`
- `FAILURE_DAY` → excluded
- `POST_FAILURE` → excluded
- `CENSORED` → excluded

An observation is labeled `AT_RISK` when an explicit failure occurs between one and seven days after that observation.

This creates a forward-looking seven-day predictive-maintenance task rather than a same-day failure detector.

---

## 2. Dataset

The model was developed using Backblaze hard-drive SMART telemetry covering:

- 2025 Q2
- 2025 Q3
- 2025 Q4
- 2026 Q1

Multiple hard-drive models were retained rather than training on a single hardware model.

The development dataset contains hundreds of thousands of drives and tens of millions of drive-day observations.

---

## 3. Temporal Evaluation Design

A strict chronological split was used.

| Period | Role |
|---|---|
| 2025 Q2 | Training |
| 2025 Q3 | Training |
| 2025 Q4 | Validation / model development |
| 2026 Q1 | Final untouched holdout |

The 2026 Q1 period was not used for:

- feature selection,
- hyperparameter tuning,
- sampling-ratio selection,
- threshold selection,
- architecture selection,
- or comparison between the Random Forest and GRU.

The final model configuration was frozen before 2026 Q1 was evaluated.

---

## 4. SMART Telemetry

Eight common raw SMART signals were selected based on availability across the retained drive population:

- `smart_5_raw`
- `smart_9_raw`
- `smart_192_raw`
- `smart_193_raw`
- `smart_194_raw`
- `smart_198_raw`
- `smart_4_raw`
- `smart_12_raw`

These signals represent drive-health, lifetime, temperature, start/stop, reallocation, and error-related telemetry.

---

## 5. Temporal Feature Engineering

The final Random Forest uses 33 features.

The feature contract contains:

### Current SMART measurements

Eight current SMART raw values.

### Health indicators

Explicit indicators derived from important SMART failure signals, including:

- non-zero SMART 5,
- non-zero SMART 198,
- increases in SMART 5,
- increases in SMART 198.

### Temporal change features

For each selected SMART signal:

- one-observation change,
- seven-observation change.

### Temperature-history features

The model also uses:

- seven-observation temperature mean,
- seven-observation temperature minimum,
- seven-observation temperature maximum,
- seven-observation temperature range,
- current temperature relative to recent mean.

All temporal features use current or historical observations only.

Future SMART telemetry is never used as model input.

---

## 6. Class Imbalance

Drive failure is extremely rare relative to normal drive operation.

The final training strategy retains:

- all positive training observations,
- a deterministic sample of negative observations at a ratio of `50:1`.

The final training population contains:

| Class | Rows |
|---|---:|
| Class | Rows |
|---|---:|
| Positive | 10,676 |
| Negative | 533,800 |
| Total | 544,476 |
| Negative : Positive | 50 : 1 |

Overall accuracy is not used as the primary model-selection metric because a trivial majority-class classifier would achieve extremely high accuracy under this level of imbalance.

Primary evaluation focuses on:

- PR-AUC,
- ROC-AUC,
- precision,
- recall,
- drive-level recall,
- alert burden,
- and first-warning lead time.

---

## 7. Model Development

Several increasingly capable configurations were evaluated on the 2025 Q4 validation period.

| Model | Q4 PR-AUC | Q4 ROC-AUC |
|---|---:|---:|
| Current SMART baseline | 0.017609 | 0.868802 |
| SMART + health indicators | 0.021600 | 0.870877 |
| Temporal Random Forest v2 | 0.025530 | 0.895347 |
| HistGradientBoosting | 0.023807 | 0.902652 |

Additional Random Forest experiments evaluated:

- alternative tree depth,
- alternative minimum leaf sizes,
- alternative feature sampling,
- hardware-model identity,
- and different negative-sampling ratios.

A `50:1` negative-to-positive training ratio improved validation PR-AUC.

The notebook experiment achieved:

- PR-AUC: `0.028492`
- ROC-AUC: `0.891983`

The independently packaged standalone model reproduced this closely:

- PR-AUC: `0.028004`
- ROC-AUC: `0.892056`

The small difference results from deterministic reconstruction of the standalone training sample.

---

## 8. Deep-Learning Challenger

A GRU sequence model was implemented as a controlled deep-learning challenger.

### GRU input

Each sequence contains:

- 30 consecutive daily observations,
- 8 SMART channels,
- a seven-day forward failure target.

The GRU contains 14,273 trainable parameters and was trained using an NVIDIA RTX 3080 Ti.

Training used 2025 Q2 and Q3, while model selection used Q4.

To ensure a fair comparison, the frozen Random Forest and GRU were evaluated on exactly the same GRU-eligible Q4 endpoints.

| Model | PR-AUC | ROC-AUC | PR Lift |
|---|---:|---:|---:|
| Temporal RF v2 | 0.022843 | 0.879989 | 133.57x |
| GRU v1 | 0.015752 | 0.869368 | 92.11x |

The GRU therefore did not improve predictive ranking on the common evaluation population.

It remains in the repository as an evaluated experimental challenger but was not promoted to the final predictive-maintenance model.

---

## 9. Final Selected Model

The final model is:

### DC-Guardian Temporal Random Forest v2

Configuration:

```text
RandomForestClassifier

n_estimators       = 300
max_depth          = None
min_samples_leaf   = 2
max_features       = sqrt
random_state       = 42
```

Training:

```text
Periods             2025 Q2 + Q3
Negative sampling   50 : 1
Features            33
Failure horizon     7 days
```

The complete preprocessing and classifier pipeline is stored at:

```text
models/rf/temporal_rf_v2.joblib
```

Training metadata is stored at:

```text
models/rf/temporal_rf_v2_metadata.json
```

---

## 10. Operating Threshold

The operating threshold was selected using 2025 Q4 validation data and frozen before final testing.

```text
Failure probability threshold = 0.45
```

The threshold represents an operational trade-off between:

- failed-drive detection,
- precision,
- warning volume,
- and warning lead time.

The threshold was not changed after viewing the 2026 Q1 holdout results.

---

## 11. Final Holdout Evaluation

The frozen model was evaluated once on the untouched 2026 Q1 holdout.

### Final population

| Metric | Value |
|---|---:|
| Predictive drive-days | 17,064,047 |
| Positive drive-days | 4,285 |
| Failed drives | 667 |
| Failure-window prevalence | 0.025111% |

### Ranking performance

| Metric | Result |
|---|---:|
| PR-AUC | **0.033474** |
| ROC-AUC | **0.872341** |
| PR lift vs prevalence | **133.30x** |

### Frozen-threshold performance

At threshold `0.45`:

| Metric | Result |
|---|---:|
| Accuracy | 99.7414% |
| Balanced accuracy | 66.7402% |
| Precision | 3.3820% |
| Row recall | 33.7223% |
| F1 | 0.061475 |

Accuracy is reported for completeness but should not be interpreted as the primary performance measure because of extreme class imbalance.

### Operational performance

| Metric | Result |
|---|---:|
| Failed drives detected | **323 / 667** |
| Drive-level recall | **48.43%** |
| Alerts | 42,726 |
| Alert rate | 0.2504% |
| Alerts / 1,000 drive-days | **2.504** |

### Warning lead time

| First warning before failure | Failed drives |
|---:|---:|
| 7 days | 170 |
| 6 days | 31 |
| 5 days | 25 |
| 4 days | 31 |
| 3 days | 22 |
| 2 days | 25 |
| 1 day | 19 |

The model produced:

- median first-warning lead time: **7 days**
- mean first-warning lead time: **5.45 days**
- failures first detected at maximum seven-day horizon: **170**

Of the 323 detected failed drives, approximately 52.6% received their first warning at the maximum seven-day prediction horizon.

---

## 12. Validation vs Final Holdout

The final holdout remained broadly consistent with the development validation behavior.

| Metric | Q4 Validation | 2026 Q1 Final |
|---|---:|---:|
| PR-AUC | 0.028004 | 0.033474 |
| ROC-AUC | 0.892056 | 0.872341 |
| Precision | 3.14% | 3.38% |
| Row recall | 30.82% | 33.72% |
| Drive recall | 49.60% | 48.43% |
| Alerts / 1,000 | 1.913 | 2.504 |
| Median lead time | 6 days | 7 days |

The model therefore retained similar drive-level detection behavior on the chronologically later holdout population.

---

## 13. Inference Interface

Production-facing inference is exposed through:

```text
src/maintenance_detector.py
```

Example:

```python
from phase1.predictive_maintenance.src.maintenance_detector import (
    assess_drive_health,
)

assessment = assess_drive_health(
    drive_history
)
```

The detector returns a JSON-safe structure containing:

```json
{
  "domain": "MAINTENANCE",
  "event_type": "STORAGE_FAILURE_RISK_ASSESSMENT",
  "model_name": "DC_Guardian_Temporal_RF_v2",
  "asset_type": "HARD_DRIVE",
  "serial_number": "DRIVE_SERIAL",
  "observation_timestamp": "TIMESTAMP",
  "assessment": "NORMAL_OR_AT_RISK",
  "failure_probability": 0.0,
  "operating_threshold": 0.45,
  "failure_horizon_days": 7,
  "evidence": {}
}
```

Downstream DC-Guardian components should consume this interface rather than loading the Random Forest artifact directly.

---

## 14. Verification

The implementation includes standalone contract tests covering:

```text
Configuration contract
Seven-day labeling
Temporal feature engineering
Standalone RF training
Q4 validation reproduction
Detector inference
Invalid detector inputs
Frozen model artifact
GRU configuration
GRU sequence construction
GRU model execution
GRU dataset preprocessing
GRU artifact integrity
Final Q1 holdout artifact
```

The final holdout result is stored at:

```text
data/processed/results/temporal_rf_v2_final_test.json
```

The final-test artifact records that:

```text
model_refit_on_test        = false
threshold_selected_on_test = false
```

This protects the distinction between development validation and final holdout evaluation.

---

## 15. Phase Boundary

Predictive Maintenance is a Phase 1 detection component.

Its responsibility ends at producing a structured drive-health assessment.

```text
SMART telemetry
      ↓
Temporal feature engineering
      ↓
Frozen Temporal RF v2
      ↓
Maintenance assessment
      ↓
════════ PHASE BOUNDARY ════════
      ↓
Phase 2 maintenance adapter
      ↓
Common Event Schema
      ↓
DC-Guardian correlation / topology
```

Phase 2 should not depend on Random Forest implementation details, SMART feature engineering internals, Backblaze-specific files, or GRU experimentation.

The stable interface is the structured assessment returned by `maintenance_detector.py`.