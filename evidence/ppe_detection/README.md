# PPE Detection

## Purpose

DC-GUARDIAN PPE-v1 provides person-level safety evidence for Reasoning layer. The frozen baseline uses YOLOv8n trained on SH17 and a project-defined compliance policy.

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

The safety-vest result is retained transparently as part of the frozen Evidence layer baseline and is a future robustness/optimization target.

## PPE-v2 candidate (2026-10-13, not used at runtime)

PPE-v1 stays frozen and is still the runtime detector. PPE-v2 was trained beside it to address the low recall. The photos are 2,000–6,000 px wide, so helmets and vests are only a few pixels across at 640 px.

**Protocol** (committed before training in `de1a113`; revised before any result in `a448fef`):
- **Data:** the PPE-v1 development split (6,479 train / 810 validation).
- **Candidates:**
  - YOLOv8n, YOLOv8s and YOLOv8m at 1024 px (`src/train_v2.py`);
  - 60 epochs, seed 42;
  - training reads copies resized once to 1024 px.
- **Selection:** on the original validation images only (`src/select_v2.py`).
  - Criterion: the mean mAP@0.5 of helmet and safety vest.
  - Within 0.01 of the best, the smaller model wins.
  - The winner must beat PPE-v1.
- **Locked test:** run once on the selected model (`src/evaluate_final_test_v2.py`, which refuses a second run).

**Selection (validation, original images):**

| Model | Criterion | Helmet mAP@0.5 / recall | Vest mAP@0.5 / recall |
|---|---:|---|---|
| PPE-v1 (YOLOv8n, 640) | 0.569 | 0.670 / 0.539 | 0.468 / 0.438 |
| YOLOv8n, 1024 | 0.616 | 0.711 / 0.566 | 0.521 / 0.458 |
| **YOLOv8s, 1024 (selected)** | **0.648** | 0.713 / 0.566 | 0.583 / 0.396 |
| YOLOv8m, 1024 | 0.648 | 0.713 / 0.579 | 0.583 / 0.417 |

YOLOv8s and YOLOv8m tie (0.6480 vs 0.6479), so the smaller model was selected.

**Locked final test (810 images), PPE-v1 → PPE-v2:**

| Classes | Precision | Recall | mAP@0.5 | mAP@0.5:0.95 |
|---|---|---|---|---|
| All classes | 0.689 → 0.709 | 0.524 → 0.535 | 0.545 → **0.595** | 0.336 → 0.385 |
| Helmet (78) | 0.732 → 0.761 | 0.603 → **0.654** | 0.676 → 0.708 | 0.456 → 0.493 |
| Safety vest (49) | 0.621 → 0.582 | 0.449 → **0.245** | 0.372 → 0.317 | 0.220 → 0.175 |
| Person (1,351) | 0.836 → 0.861 | 0.854 → 0.856 | 0.869 → 0.893 | 0.691 → 0.692 |

**Reading:**
- **Improved:** overall detection and helmets.
- **Vest worse:** the vest result went the opposite way to validation. About 12 of 49 vests were found against about 22 for v1, while validation favoured v2 on mAP. Both sets hold under 50 vests in about 23 images, so a swing of about 10 vests reverses the conclusion and the size of the difference cannot be estimated reliably. v2 does not fix the vest weakness.
- **Effect on compliance:** compliance needs both items, so a missed vest makes a compliant person look NON_COMPLIANT. More vest data, or a vest-specific evaluation, is needed before relying on either model for vests.
- **Runtime:** switching to v2 is an operator decision. Until then `ppe_config.json` (PPE-v1) is unchanged.

**Artifacts:**
- `models/ppe_yolov8_v2_best.pt` and `models/ppe_v2_training_metadata.json`;
- `results/selection_v2/`;
- `results/final_test_v2/`;
- `results/training_v2/<candidate>/results.csv`.

`tests/test_ppe_v2_artifacts.py` checks that the v1 weights and config are unchanged and that the recorded selection follows the declared rule.

## Runtime flow

```text
image -> YOLOv8n detections -> person/PPE association
      -> frozen PPE policy -> COMPLIANT / NON_COMPLIANT / NO_PERSON
      -> Reasoning layer adapter
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

## Reasoning layer contract

Reasoning layer preserves the PPE assessment, maps the observation into the controlled topology, persists it in Neo4j, and supports deterministic PPE + Face correlation and persistence.

## Limitations

The current results characterize the documented SH17 evaluation boundary. Domain shift, camera placement, occlusion, small PPE objects, association errors, and site-specific PPE policy require additional evaluation before production use.
