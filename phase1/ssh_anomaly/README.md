# DC-Guardian --- SSH Anomaly Detection

## Overview

This repository contains the Phase 1 SSH anomaly-detection component of
**DC-Guardian**.

SSH Detector v1 processes OpenSSH server logs and produces structured
behavioral security assessments. The final v1 detector combines:

-   a rule-based detector,
-   a persisted Isolation Forest,
-   a persisted Autoencoder, and
-   explicit OpenSSH security signals.

The component operates on **source-IP / 5-minute behavioral windows**.
Phase 1 ends with a frozen, independently callable inference pipeline.
Cross-domain correlation, Neo4j, RAG, Agentic AI, topology reasoning,
and dashboard integration belong to Phase 2.

## Final v1 Architecture

``` text
Raw OpenSSH logs
        |
        v
     parser.py
        |
        v
Parsed SSH events
        |
        v
feature_engineering.py
        |
        v
Source IP + 5-minute windows
        |
        v
+-----------------------------------+
|       SSHAnomalyDetector v1       |
|                                   |
|  Rules                            |
|  Isolation Forest                 |
|  Autoencoder                      |
|  Explicit OpenSSH security signal |
+----------------+------------------+
                 |
                 v
          Evidence state
                 |
        +--------+---------+------------------+
        |                  |                  |
        v                  v                  v
EXPLICIT_SECURITY   HIGH_CONFIDENCE     ANOMALY_CANDIDATE
_EVENT              _ANOMALY
                 |
                 v
          Structured JSON output
```

`ssh_pipeline.py` provides the end-to-end runtime interface. Normal
inference does **not** fit models, refit scalers, recalculate
thresholds, or retrain the detector.

------------------------------------------------------------------------

## Repository Structure

A typical project layout is:

``` text
ssh_anomaly/
|
|-- README.md
|-- requirements.txt
|
|-- data/
|   |-- raw/
|   |   |-- SSH.log
|   |   `-- OpenSSH_2k.log
|   |
|   |-- processed/
|   |   |-- ssh_events_full.csv
|   |   |-- ssh_features_full_5min.csv
|   |   `-- ssh_pipeline_assessments.json
|   |
|   `-- external/
|       `-- ssh_honeypot_dataset.csv
|
|-- models/
|   |-- isolation_forest.joblib
|   |-- isolation_forest_scaler.joblib
|   |-- autoencoder_log.keras
|   |-- autoencoder_log_scaler.joblib
|   `-- autoencoder_log_config.json
|
|-- src/
|   |-- parser.py
|   |-- feature_engineering.py
|   |-- ssh_detector.py
|   |-- ssh_pipeline.py
|   `-- verify_models.py
|
|-- evaluation/
|   |-- scenarios/
|   |-- final_test/
|   |   |-- openssh_final_test.log
|   |   |-- final_test_manifest.csv
|   |   `-- results/
|   |-- generate_final_test.py
|   `-- evaluate_final_test.py
|
`-- external_validation/
    |-- analyze_honeypot.py
    `-- results/
```

Some development/training scripts may also exist outside this minimal
runtime structure. Keep training code separate from inference code.

------------------------------------------------------------------------

## Python Environment

The tested Windows environment uses **Python 3.13**.

Python 3.14 was not used for the TensorFlow-based Autoencoder
environment because TensorFlow installation was not available in the
project environment when v1 was developed.

Check Python 3.13:

``` powershell
py -3.13 --version
```

Create the virtual environment from the project root:

``` powershell
py -3.13 -m venv .venv
```

PowerShell script activation may be blocked by Windows execution policy.
Activation is not required. The commands in this README call the
virtual-environment interpreter directly:

``` powershell
.\.venv\Scripts\python.exe
```

Upgrade pip:

``` powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
```

Install the main dependencies:

``` powershell
.\.venv\Scripts\python.exe -m pip install numpy pandas scikit-learn matplotlib tensorflow joblib
```

For reproducibility, save the exact installed package versions after the
environment is working:

``` powershell
.\.venv\Scripts\python.exe -m pip freeze > requirements.txt
```

------------------------------------------------------------------------

## Dataset Placement

### Model-development dataset

Place the Loghub OpenSSH dataset at:

``` text
data/raw/SSH.log
```

The final run processed:

-   **655,147 raw log lines**
-   **655,147 parsed lines**
-   **0 unparsed lines**
-   **542,381 events with a source IP**
-   **8,256 source-IP / 5-minute behavioral windows**

The Loghub data is not treated as a ready-made benign/attack labeled
classification dataset. It was used for parser development, feature
engineering, anomaly-model development, and full-data behavioral
analysis.

### External behavioral-validation dataset

The independent SSH honeypot CSV is kept separately at:

``` text
data/external/ssh_honeypot_dataset.csv
```

It is not used to train SSH Detector v1.

------------------------------------------------------------------------

## Parsing

`src/parser.py` parses OpenSSH/syslog records and extracts fields
including:

-   timestamp,
-   hostname,
-   PID,
-   event type,
-   username,
-   source IP,
-   source port,
-   invalid-user status,
-   successful-authentication status,
-   repeated-event count, and
-   original message.

Recognized security-relevant events include failed login, successful
login, invalid user, PAM authentication failure, possible break-in
warning, connection/disconnect events, missing SSH identification
strings, and related authentication conditions.

Run the parser directly:

``` powershell
.\.venv\Scripts\python.exe src\parser.py
```

For the full dataset it writes the parsed event table under
`data/processed/`.

------------------------------------------------------------------------

## Five-Minute Behavioral Features

`src/feature_engineering.py` groups events by:

``` text
source_ip + 5-minute window
```

The final feature table includes contextual and model features such as:

  -----------------------------------------------------------------------
  Feature                             Meaning
  ----------------------------------- -----------------------------------
  `failed_login_count`                Failed authentication occurrences

  `successful_login_count`            Successful authentication
                                      occurrences

  `invalid_user_count`                Invalid-user events

  `unique_users`                      Distinct usernames in
                                      authentication-result events

  `failure_ratio`                     Failed attempts / total
                                      authentication attempts

  `attempt_rate`                      Authentication attempts per minute

  `root_attempt_count`                Authentication attempts targeting
                                      root

  `root_attempt_ratio`                Root targeting relative to
                                      failed-login activity

  `breakin_warning_count`             Explicit OpenSSH possible-break-in
                                      warnings

  `disconnect_count`                  Disconnect events

  `no_identification_count`           Missing SSH identification-string
                                      events

  `success_after_failures`            Successful authentication after
                                      failure in the same window
  -----------------------------------------------------------------------

Run feature engineering:

``` powershell
.\.venv\Scripts\python.exe src\feature_engineering.py
```

The full feature table is:

``` text
data/processed/ssh_features_full_5min.csv
```

------------------------------------------------------------------------

## Frozen Detection Models

SSH Detector v1 combines three detector votes plus explicit OpenSSH
security context.

### Rule detector

The frozen rule baseline evaluates:

-   repeated authentication failures,
-   username enumeration, and
-   root targeting.

An OpenSSH `POSSIBLE BREAK-IN ATTEMPT` warning is preserved as explicit
security evidence rather than being added as an artificial fourth model
vote.

### Isolation Forest

The Isolation Forest is an unsupervised anomaly detector persisted after
development. Its scaler and model are loaded from disk during inference.

The Isolation Forest is retained as a statistical novelty signal.
Controlled evaluation showed that it should **not** be interpreted as a
reliable standalone attack classifier.

### Autoencoder

The Autoencoder learns the reference-normal behavioral feature
representation.

Its inference preprocessing reproduces training preprocessing:

``` text
count features -> log1p
ratio features -> unchanged
all model features -> persisted RobustScaler
```

The reconstruction-error threshold is loaded from the persisted
configuration rather than recalculated during inference.

------------------------------------------------------------------------

## Persisted Artifacts

The frozen v1 artifacts are:

``` text
models/
|-- isolation_forest.joblib
|-- isolation_forest_scaler.joblib
|-- autoencoder_log.keras
|-- autoencoder_log_scaler.joblib
`-- autoencoder_log_config.json
```

Do not replace or refit these files when performing normal v1 inference.

------------------------------------------------------------------------

## Verify Model Persistence

Run:

``` powershell
.\.venv\Scripts\python.exe src\verify_models.py
```

The expected successful result is:

``` text
============================================
MODEL PERSISTENCE VERIFICATION PASSED
============================================

Both trained models were loaded from disk and performed inference successfully.
No model or scaler was fitted or retrained during this verification.
```

------------------------------------------------------------------------

## Verify the Frozen Detector

Run:

``` powershell
.\.venv\Scripts\python.exe src\ssh_detector.py
```

The expected final line is:

``` text
============================================
SSH DETECTOR INFERENCE PASSED
============================================
```

This test loads the persisted artifacts and performs inference only.

------------------------------------------------------------------------

## Evidence-State Contract

The v1 integration output distinguishes the strength/type of evidence
instead of treating every anomaly as a confirmed attack.

### `EXPLICIT_SECURITY_EVENT`

An explicit high-value OpenSSH security signal is present, such as:

``` text
POSSIBLE BREAK-IN ATTEMPT
```

This state can occur even when the Rule, Isolation Forest, and
Autoencoder contribute zero anomaly votes.

### `HIGH_CONFIDENCE_ANOMALY`

At least two of the three detectors agree:

``` text
detector_votes >= 2
```

The locked controlled final test showed that the two-of-three consensus
was the cleanest high-confidence model operating point.

### `ANOMALY_CANDIDATE`

Exactly one detector votes anomalous:

``` text
detector_votes == 1
```

This is useful evidence for later correlation, but it should not
automatically be treated as a confirmed attack.

### `NO_ANOMALY_EVIDENCE`

No detector votes anomalous and there is no explicit OpenSSH security
signal.

------------------------------------------------------------------------

## End-to-End Runtime Pipeline

The primary Phase 2-facing wrapper is:

``` text
src/ssh_pipeline.py
```

Run the full Loghub pipeline:

``` powershell
.\.venv\Scripts\python.exe src\ssh_pipeline.py
```

The verified end-to-end run produced:

``` text
Parsed SSH events: 655147
Behavior windows: 8256
Assessments: 8256
Security-relevant assessments: 4909
High-priority assessments: 4769
```

Evidence-state distribution:

``` text
HIGH_CONFIDENCE_ANOMALY    3569
NO_ANOMALY_EVIDENCE        3347
EXPLICIT_SECURITY_EVENT    1200
ANOMALY_CANDIDATE           140
```

These counts describe detector evidence on the **unlabeled** Loghub
dataset. They must not be presented as the percentage of traffic that is
ground-truth malicious.

The pipeline writes:

``` text
data/processed/ssh_pipeline_assessments.json
```

------------------------------------------------------------------------

## Programmatic Integration

A caller can run a raw OpenSSH log file through the frozen v1 pipeline:

``` python
from ssh_pipeline import SSHPipeline

pipeline = SSHPipeline(year=2000)

assessments = pipeline.assess_log_file(
    "path/to/ssh.log"
)
```

To keep all assessments containing security evidence:

``` python
security_events = pipeline.security_relevant(
    assessments
)
```

To keep only the strongest states:

``` python
high_priority = pipeline.high_priority(
    assessments
)
```

The high-priority helper returns:

``` text
EXPLICIT_SECURITY_EVENT
HIGH_CONFIDENCE_ANOMALY
```

The full assessment retains source IP, time window, detector votes,
detector combination, confidence, explicit security signals, Rule
output, Isolation Forest output, Autoencoder output, and behavioral
evidence.

------------------------------------------------------------------------

## Evaluation Methodology

SSH Detector v1 uses three distinct evaluation/data roles.

### 1. Loghub OpenSSH --- model development

The real OpenSSH dataset was used for:

-   parser development,
-   feature engineering,
-   rule analysis,
-   unsupervised model development,
-   normal-reference selection, and
-   full-data behavioral analysis.

Because the original dataset is not used as a ready-made attack/benign
labeled benchmark, full-data anomaly percentages are not reported as
classification accuracy.

### 2. Controlled Development Set A

A controlled labeled OpenSSH scenario set was used during development.

It contained:

``` text
330 scenarios
120 NORMAL
210 ATTACK
```

Set A exposed an explicit break-in-warning handling gap. The operational
policy was corrected before the final locked evaluation.

For that reason, Set A is a **development/diagnostic set**, not the
final independent test.

### 3. Locked Final Evaluation Set B

A separate controlled set was generated and locked before final
evaluation:

``` text
280 scenarios
120 NORMAL
160 ATTACK
14 scenario families
20 repetitions per family
```

The frozen detector was evaluated without tuning against the resulting
metrics.

------------------------------------------------------------------------

## Final Controlled Test Results

Final Set B results:

  ------------------------------------------------------------------------------------
  Detector          Accuracy     Precision        Recall           F1   False-Positive
                                                                                  Rate
  ------------- ------------ ------------- ------------- ------------ ----------------
  Rule                76.43%       100.00%        58.75%       74.02%            0.00%

  Isolation           35.71%        33.33%        12.50%       18.18%           33.33%
  Forest                                                              

  Autoencoder         80.00%        79.55%        87.50%       83.33%           30.00%

  Hybrid              65.71%        64.81%        87.50%       74.47%           63.33%
  Sensitive                                                           
  (\>=1 vote)                                                         

  Hybrid          **83.57%**   **100.00%**    **71.25%**   **83.21%**        **0.00%**
  Consensus                                                           
  (\>=2 votes)                                                        

  Operational         72.86%        67.80%   **100.00%**       80.81%           63.33%
  Detector                                                            
  ------------------------------------------------------------------------------------

### Interpretation

The two-of-three model consensus produced the strongest high-confidence
operating point:

``` text
Accuracy   83.57%
Precision 100.00%
Recall     71.25%
F1         83.21%
FPR         0.00%
```

The broader operational detector detected all 160 controlled attacks:

``` text
Recall = 100%
False-negative rate = 0%
```

but also produced a high false-positive rate:

``` text
FPR = 63.33%
```

Therefore, v1 does not equate every single-model anomaly with a
confirmed attack. The evidence-state contract preserves lower-confidence
candidates for later DC-Guardian correlation.

These metrics apply to the **controlled Final Set B scenarios**. They
are not universal real-world SSH attack-detection accuracy.

------------------------------------------------------------------------

## Reproduce the Locked Final Evaluation

The locked test data is under:

``` text
evaluation/final_test/
```

Run:

``` powershell
.\.venv\Scripts\python.exe evaluation\evaluate_final_test.py
```

The integrity check should confirm:

``` text
Manifest scenarios: 280
Feature windows:    280
Matched windows:    280
Manifest only:      0
Feature only:       0
```

Do not tune SSH Detector v1 against Final Set B and then present a rerun
on the same set as an independent final test.

------------------------------------------------------------------------

## External Behavioral Validation

An independent SSH honeypot dataset was analyzed separately from
training.

Observed dataset scale:

``` text
145,425 events
13,897 unique source IPs
137,506 sessions
59,089 source-IP / 5-minute windows
```

Observed behaviors included:

-   4,797 SSH login events,
-   316 extracted unique usernames,
-   1,618 root login events,
-   root accounting for 33.73% of login events,
-   substantial username diversity from some sources,
-   short-window connection bursts,
-   up to 765 connections from one source IP in a five-minute window,
    and
-   command execution in a small number of sessions.

This provides independent behavioral evidence that source-IP
aggregation, temporal windows, root targeting, username diversity, and
burst behavior are relevant dimensions of hostile SSH activity.

The honeypot dataset does **not** provide direct equivalents for every
OpenSSH v1 feature, including `failed_login_count`, `failure_ratio`,
`invalid_user_count`, `breakin_warning_count`, and
`no_identification_count`. Missing semantics are not fabricated.
Therefore this dataset is used for **external behavioral validation**,
not for reporting frozen-detector accuracy, precision, recall, or F1.

------------------------------------------------------------------------

## Known v1 Limitations

SSH Detector v1 is primarily an **SSH authentication-behavior anomaly
detector**.

The external honeypot analysis highlighted real hostile behavior that is
not fully represented by the frozen v1 feature space, particularly:

-   high-rate SSH connection scanning/probing without authentication,
-   connection/session intensity,
-   unique-session behavior, and
-   post-authentication command execution.

Potential v2 features include:

``` text
connection_count
connection_rate
unique_sessions
session_success_behavior
command_execution_count
post_authentication_activity
```

These are future extensions. They are not added to v1 because doing so
would require a new training and evaluation cycle.

------------------------------------------------------------------------

## Development vs Inference

Keep these activities separate.

### Development/training

Training scripts may:

``` text
fit scalers
fit Isolation Forest
train Autoencoder
select thresholds using validation data
save model artifacts
```

### Frozen v1 inference

The runtime path may only:

``` text
load persisted models
load persisted scalers
load persisted threshold/configuration
transform incoming features
perform inference
return structured assessments
```

Do not call `fit()`, `fit_transform()`, retrain the Autoencoder, or
select a new threshold inside runtime inference.

------------------------------------------------------------------------

## Data and Security Notes

-   Keep raw datasets read-only.
-   Keep processed outputs separate from raw data.
-   Do not commit SSH credentials, passwords, secrets, or sensitive
    infrastructure information.
-   Do not commit large raw datasets to a public repository unless the
    dataset license and repository policy explicitly permit it.
-   Document dataset sources and usage conditions.
-   Keep controlled/synthetic evaluation data clearly separated from
    original real logs.
-   Do not interpret unsupervised anomaly labels as automatically
    equivalent to malicious ground truth.

------------------------------------------------------------------------

## Phase 2 Handover

SSH Detector v1 is ready to hand over as an independently callable Phase
1 component.

The downstream DC-Guardian layer should consume the structured
assessment rather than only a Boolean anomaly flag. Important fields
include:

``` text
event_type
source_ip
window_start
window_end
anomaly_detected
evidence_state
detector_votes
detector_combination
confidence
explicit_security_signal
security_signals
rule
isolation_forest
autoencoder
evidence
```

Phase 2 can then map this output to the shared event schema, simulated
data-center topology, Knowledge Graph, operational RAG, Agentic AI,
correlation/risk reasoning, decision engine, and dashboard.

Infrastructure-specific fields such as `zone_id`, `rack_id`,
`server_id`, `asset_id`, and final severity policy should be added
during Phase 2 rather than hard-coded into SSH Detector v1.

------------------------------------------------------------------------

## Phase 1 SSH Status

Completed for SSH Detector v1:

-   [x] Data documented
-   [x] Reproducible preprocessing
-   [x] Model training completed
-   [x] Source-IP leakage check performed for Autoencoder
    reference-normal splits
-   [x] Persisted model/scaler artifacts
-   [x] Model-persistence verification
-   [x] Frozen inference detector
-   [x] Controlled development evaluation
-   [x] Locked final controlled evaluation
-   [x] Metrics recorded
-   [x] External behavioral validation
-   [x] End-to-end raw-log inference pipeline
-   [x] Structured Phase 2 output contract
-   [x] README / run instructions

Still a shared/team activity:

-   [ ] Four-model integration test
-   [ ] Peer review

------------------------------------------------------------------------

## Important Result-Reporting Language

Use language such as:

> SSH Detector v1 was developed using real Loghub OpenSSH records and
> quantitatively evaluated on a separately locked controlled test set.
> On the 280-scenario Final Set B, the two-of-three model consensus
> achieved 83.57% accuracy, 100% precision, 71.25% recall, and 83.21% F1
> with a 0% false-positive rate. A broader operational policy achieved
> 100% recall but a 63.33% false-positive rate, motivating the use of
> evidence levels rather than treating every anomaly as a confirmed
> attack.

Also state:

> These metrics characterize performance on the controlled labeled
> evaluation scenarios and must not be interpreted as universal
> real-world SSH intrusion-detection accuracy.
