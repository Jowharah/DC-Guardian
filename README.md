# DC-GUARDIAN

DC-GUARDIAN is a research prototype for multi-domain data-center monitoring and incident reasoning. The project combines independently developed Phase 1 detectors with a Phase 2 integration layer built around a common event schema, a controlled synthetic data-center topology, Neo4j, and deterministic cross-domain correlation.

> **Current baseline:** Phase 1 model baselines are frozen for integration. Phase 2 currently passes **24/24 integration contracts**, including Face Recognition and PPE cross-domain integration. RAG, agent reasoning, severity/decision rules, and the final incident-output layer are the next major workstreams.

## Architecture

```text
Phase 1 domain models
        |
        v
Common Event Schema
        |
        v
Synthetic topology mapping
        |
        v
Neo4j knowledge graph
        |
        v
Deterministic cross-domain correlation
        |
        v
Persistent Correlation objects
        |
        +--> Operational RAG          (planned)
        +--> Agent reasoning          (planned)
        +--> Severity/decision rules  (planned)
        +--> Incident/dashboard       (planned)
```

The current design deliberately performs graph and rule-based correlation before future LLM reasoning. Source-model assessments and provenance are preserved rather than silently rewritten by later layers.

## Phase 1 Components

| Component | Current baseline | Purpose |
|---|---|---|
| Face Recognition | ArcFace + RetinaFace | Controlled identity recognition for physical-security evidence |
| PPE Detection | YOLOv8n / PPE-v1 | Person-level PPE evidence using the frozen project compliance policy |
| Predictive Maintenance | Temporal Random Forest v2 | Seven-day hard-drive failure-risk assessment from SMART telemetry |
| SSH Anomaly Detection | SSH Detector v1 | Rules + Isolation Forest + Autoencoder + explicit OpenSSH security signals |
| Environmental Monitoring | Deterministic monitoring contract | Environmental sensor and hardware-telemetry assessment |

Phase 1 datasets that are large, private, biometric, or externally sourced are intentionally excluded from Git. Small configuration, evaluation, and reproducibility artifacts are retained where appropriate.

## Phase 2 Integration

Phase 2 normalizes Phase 1 outputs into a shared event contract and maps controlled evaluation events into the synthetic `DC-01` topology.

Implemented integration currently includes:

- Common Event Schema validation
- SSH adapter, topology mapping, Neo4j ingestion, and correlation context
- Predictive-maintenance adapter, topology mapping, and graph ingestion
- Environmental adapter and graph integration
- Face Recognition adapter, camera topology, graph-derived authorization, and Face + Cyber correlation
- PPE adapter, topology mapping, graph ingestion, PPE + Face correlation, and persistence
- Deterministic pairwise and three-domain correlation
- Deterministic/idempotent correlation persistence

### Runtime and regression verification

The verified integrated runtime uses Python 3.12 and the repository-level
`requirements.txt`. After installing dependencies, verify that the public/frozen
Phase 1 runtime stacks initialize:

```powershell
python verify_runtime.py
```

The smoke test checks Predictive Maintenance, SSH, PPE, and the Face ML stack.
It deliberately does not require the private Face enrollment embedding artifact.

Run the Phase 2 contract suite from the repository root:

```powershell
python phase2\run_contract_tests.py
```

Neo4j must be running for graph and correlation contracts.

The current accepted integration baseline is:

```text
24 / 24 contracts passing
```

A cleanup or refactor that changes executable Phase 2 code should not be accepted unless the full contract suite still passes, or the contract suite is intentionally versioned to reflect a documented interface change.

## Repository Structure

```text
DC-Guardian/
|-- phase1/
|   |-- environmental_monitoring/
|   |-- face_recognition/
|   |-- ppe_detection/
|   |-- predictive_maintenance/
|   `-- ssh_anomaly/
|
|-- phase2/
|   |-- adapters/
|   |-- correlation/
|   |-- graph/
|   |-- topology/
|   |-- run_contract_tests.py
|   |-- validate_event_schema.py
|   `-- validate_topology.py
|
|-- shared/
|   |-- schemas/
|   `-- topology/
|
|-- .gitignore
`-- .gitattributes
```

## Component Documentation

Detailed Phase 1 documentation is available in each component directory:

- `phase1/face_recognition/README.md`
- `phase1/ppe_detection/README.md`
- `phase1/predictive_maintenance/README.md`
- `phase1/ssh_anomaly/README.md`
- `phase1/environmental_monitoring/README.md`

The repository-level `requirements.txt` lists the direct Python dependencies for the integrated project. It is intentionally not a full `pip freeze` snapshot; exact environment locking will be finalized after dependency compatibility is verified across the integrated runtime.

## Key Shared Contracts

- `shared/schemas/event_schema.json` - common event representation used before graph ingestion and correlation.
- `shared/topology/data_center_topology.json` - controlled synthetic `DC-01` topology.
- `shared/topology/mappings/` - controlled mappings used to place model-derived evidence into the synthetic evaluation topology.

Synthetic mappings are evaluation constructs. They are not presented as observations from a real data center.

## Model Evaluation Notes

The Phase 1 components solve different tasks and were evaluated with different protocols. Their metrics should not be compared directly as if they came from one benchmark.

### Face Recognition

The frozen Face Recognition baseline uses ArcFace embeddings, RetinaFace detection, cosine distance, and a validation-selected recognition threshold of `0.50`.

The locked controlled final test contained 15 images: 6 known-person images and 9 unknown-person images.

| Measure | Locked-test result |
|---|---:|
| Known identifications | 6 / 6 |
| Known identification rate | 100% |
| Unknown rejections | 9 / 9 |
| Unknown rejection rate | 100% |
| False acceptances | 0 |
| False rejections | 0 |
| Misidentifications | 0 |
| Mean latency | 2741 ms/image |
| Median latency | 2455 ms/image |

The threshold and enrollment set were not changed during the final test. These are controlled proof-of-concept results from a small curated dataset and must not be generalized as production biometric accuracy.

### PPE Detection

The frozen PPE-v1 detector uses YOLOv8n trained on SH17. The locked final test contains 810 images.

| Metric | Locked-test result |
|---|---:|
| Precision | 0.6889 |
| Recall | 0.5241 |
| mAP@0.5 | 0.5447 |
| mAP@0.5:0.95 | 0.3363 |

For the two classes required by the project compliance policy:

| Required class | Precision | Recall | mAP@0.5 | mAP@0.5:0.95 |
|---|---:|---:|---:|---:|
| Helmet | 0.7321 | 0.6026 | 0.6761 | 0.4557 |
| Safety vest | 0.6213 | 0.4490 | 0.3719 | 0.2195 |

The project-defined baseline compliance policy requires `helmet` and `safety-vest`. A `NON_COMPLIANT` result means required PPE was not detected for at least one detected person; it does **not** prove physical absence.

### Predictive Maintenance

The selected baseline is `DC_Guardian_Temporal_RF_v2`, evaluated once on the untouched 2026 Q1 holdout after model and operating-threshold selection were frozen. The task predicts explicit hard-drive failure within the next seven days.

The final holdout contains 17,064,047 drive-day rows, including 4,285 positive rows and 667 failed drives.

| Metric | 2026 Q1 final holdout |
|---|---:|
| PR-AUC | 0.03347 |
| ROC-AUC | 0.87234 |
| PR lift | 133.30x |
| Precision | 0.03382 |
| Row recall | 0.33722 |
| Drive-level recall | 0.48426 |
| Alerts / 1,000 drive-days | 2.504 |
| Median first-warning lead time | 7 days |
| Mean first-warning lead time | 5.45 days |
| Failed drives detected | 323 / 667 |

The positive prevalence is approximately 0.025%, so accuracy alone is not an informative primary measure for this task. The model was not refit on the final test and the operating threshold was not selected on the final test.

### SSH Anomaly Detection

SSH Detector v1 combines rules, Isolation Forest, Autoencoder evidence, and explicit OpenSSH security signals. Its locked controlled final evaluation contains 280 scenarios/windows: 120 normal and 160 attack cases.

The detector intentionally preserves different evidence strengths instead of treating every anomaly signal as a confirmed attack.

| Detector / policy | Precision | Recall | F1 | Specificity |
|---|---:|---:|---:|---:|
| Rule baseline | 1.000 | 0.588 | 0.740 | 1.000 |
| Isolation Forest | 0.333 | 0.125 | 0.182 | 0.667 |
| Autoencoder | 0.795 | 0.875 | 0.833 | 0.700 |
| Hybrid consensus | 1.000 | 0.713 | 0.832 | 1.000 |
| Operational detector | 0.678 | 1.000 | 0.808 | 0.367 |

The operational detector obtains full recall on the controlled final set by preserving explicit security signals and broader anomaly evidence, at the cost of more false positives. The stricter hybrid-consensus state provides higher-confidence model evidence with zero false positives on this controlled set. These controlled scenario metrics are not presented as real-world SSH attack prevalence or production detection accuracy.

External honeypot data is used as separate behavioral validation rather than as training data for the frozen detector.

### Environmental Monitoring

Environmental Monitoring is **not a learned ML model** in the current baseline. It is a deterministic monitoring component that converts configured environmental or hardware-telemetry conditions into structured assessments.

Accordingly, DC-GUARDIAN does not report artificial precision, recall, or accuracy values for this component. Validation instead checks deterministic behavior and source contracts, including:

- configured threshold/condition handling,
- dedicated environmental-sensor observations,
- hardware-origin telemetry,
- source/provenance preservation, and
- compatibility with the Phase 2 common-event and graph contracts.

Production environmental thresholds should ultimately be aligned with the selected operational sensor and equipment specifications.

## Data and Privacy

The repository intentionally excludes:

- raw Backblaze datasets
- raw SH17 data
- raw/external SSH datasets
- controlled face photographs
- face enrollment embeddings
- Python virtual environments
- local Neo4j runtime databases
- credentials and `.env` files
- generated caches and temporary outputs

Do not commit biometric source data, enrollment embeddings, credentials, or private operational data.

## Git LFS

The frozen Temporal Random Forest artifact is stored with Git LFS:

```text
phase1/predictive_maintenance/models/rf/temporal_rf_v2.joblib
```

After cloning, ensure Git LFS is installed before relying on that artifact.

## Local Configuration

Local credentials belong in `.env`, which is excluded from Git. A sanitized `.env.example` will document the required local configuration without publishing credentials.

## Current Development Roadmap

1. Repository cleanup and reproducibility hardening
2. Operational knowledge manifest and approved-source definition
3. RAG ingestion, chunking, metadata, retrieval, and retrieval evaluation
4. Grounded agent interfaces over graph + retrieved evidence
5. Deterministic severity and decision rules
6. Broader controlled scenario evaluation
7. Final incident object and dashboard integration

## Research Scope

DC-GUARDIAN is currently a controlled research prototype. Cross-domain scenarios use synthetic topology placement and controlled timing where required because no synchronized real-world dataset spans all project domains. Model and correlation results should therefore be interpreted within their documented evaluation settings rather than as production data-center performance claims.
