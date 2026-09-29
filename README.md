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

### Regression baseline

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

## Key Shared Contracts

- `shared/schemas/event_schema.json` - common event representation used before graph ingestion and correlation.
- `shared/topology/data_center_topology.json` - controlled synthetic `DC-01` topology.
- `shared/topology/mappings/` - controlled mappings used to place model-derived evidence into the synthetic evaluation topology.

Synthetic mappings are evaluation constructs. They are not presented as observations from a real data center.

## Model Evaluation Notes

### Face Recognition

The Face Recognition results are controlled proof-of-concept results from a small curated dataset. They should not be generalized as production biometric accuracy. The frozen Phase 1 configuration uses ArcFace embeddings, RetinaFace detection, cosine distance, and a validation-selected recognition threshold.

### PPE Detection

The frozen PPE-v1 detector uses YOLOv8n trained on SH17. The locked final test contains 810 images.

Overall locked-test metrics:

| Metric | Result |
|---|---:|
| Precision | 0.6889 |
| Recall | 0.5241 |
| mAP@0.5 | 0.5447 |
| mAP@0.5:0.95 | 0.3363 |

The project-defined baseline compliance policy requires `helmet` and `safety-vest`. A `NON_COMPLIANT` result means required PPE was not detected for at least one detected person; it does **not** prove physical absence.

### Predictive Maintenance

The selected Phase 1 model is Temporal Random Forest v2. Development uses chronological train/validation/final-test separation and a seven-day forward failure horizon. See `phase1/predictive_maintenance/README.md` for the detailed evaluation methodology and frozen-model artifacts.

### SSH Anomaly Detection

SSH Detector v1 operates on source-IP / five-minute behavioral windows and preserves different evidence strengths rather than treating every anomaly as a confirmed attack. See `phase1/ssh_anomaly/README.md` for the detector architecture, evaluation methodology, and frozen artifacts.

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
