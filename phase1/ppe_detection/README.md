# PPE Detection

## Purpose

DC-GUARDIAN PPE-v1 provides person-level safety evidence for Phase 2. The frozen baseline uses YOLOv8n trained on SH17 and a project-defined compliance policy.

## Frozen baseline

- Architecture: YOLOv8n
- Dataset: SH17
- Classes: 17
- Training images: 6,479
- Validation images: 810
- Locked test images: 810
- Epochs: 50
- Image size: 640
- Batch size: 16
- Seed: 42
- Frozen model: `models/ppe_yolov8_best.pt`

The project baseline policy requires:

- `helmet`
- `safety-vest`

A `NON_COMPLIANT` assessment means required PPE was not detected for at least one detected person. It does **not** prove that the PPE item is physically absent.

## Locked final test

| Metric | Result |
|---|---:|
| Precision | 0.6889 |
| Recall | 0.5241 |
| mAP@0.5 | 0.5447 |
| mAP@0.5:0.95 | 0.3363 |

Required-class results:

| Class | Precision | Recall | mAP@0.5 | mAP@0.5:0.95 |
|---|---:|---:|---:|---:|
| Helmet | 0.7321 | 0.6026 | 0.6761 | 0.4557 |
| Safety vest | 0.6213 | 0.4490 | 0.3719 | 0.2195 |

The safety-vest result is retained transparently as part of the frozen Phase 1 baseline and is a future robustness/optimization target.

## Runtime flow

```text
image -> YOLOv8n detections -> person/PPE association
      -> frozen PPE policy -> COMPLIANT / NON_COMPLIANT / NO_PERSON
      -> Phase 2 adapter
```

## Repository artifacts

```text
models/
  ppe_yolov8_best.pt
  ppe_config.json
  ppe_training_metadata.json

results/
  training/ppe_yolov8n_full/
  final_test/

src/
  ppe_pipeline.py
  ppe_association.py
  ppe_policy.py
```

Raw SH17 data and generated training checkpoints are intentionally excluded from Git.

## Phase 2 contract

Phase 2 preserves the PPE assessment, maps the observation into the controlled topology, persists it in Neo4j, and supports deterministic PPE + Face correlation and persistence.

## Limitations

The current results characterize the documented SH17 evaluation boundary. Domain shift, camera placement, occlusion, small PPE objects, association errors, and site-specific PPE policy require additional evaluation before production use.
