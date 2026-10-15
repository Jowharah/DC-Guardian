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

## PPE-v2 candidates (2026-10-13)

PPE-v1 stays frozen and selectable; since 2026-10-14 the runtime uses PPE-v2m (see [Runtime detector](#runtime-detector-ppe-v2m-2026-10-14)). PPE-v2 was trained beside it to address the low recall. The photos are 2,000–6,000 px wide, so helmets and vests are only a few pixels across at 640 px.

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
- **Runtime:** the operator chose PPE-v2m (YOLOv8m) on 2026-10-14, after the post-hoc analysis below; `ppe_config.json` (PPE-v1) is unchanged and still selectable.

### Post-hoc: all candidates on the locked test (after selection; not used to choose)

At the operator's request, after the vest regression, the two unselected candidates were scored on the same 810 locked images with the same settings (`src/evaluate_posthoc_v2.py`, `results/posthoc_v2/`). Re-scoring v1 and v2s1024 reproduced their official results exactly (mAP@0.5 0.5447 and 0.5951). **v2s1024 remains the official PPE-v2 result.**

| Locked test, post-hoc | All mAP@0.5 / recall | Helmet recall / mAP@0.5 | Vest recall / mAP@0.5 | Person mAP@0.5 |
|---|---|---|---|---|
| PPE-v1 (baseline) | 0.545 / 0.524 | 0.603 / 0.676 | 0.449 / 0.372 | 0.869 |
| v2n1024 | 0.578 / 0.532 | 0.592 / 0.744 | 0.367 / 0.383 | 0.884 |
| **v2s1024 (official)** | 0.595 / 0.535 | 0.654 / 0.708 | 0.245 / 0.317 | 0.893 |
| v2m1024 | **0.625 / 0.612** | **0.664** / 0.739 | **0.449 / 0.416** | **0.900** |

At the runtime confidence threshold (0.25), vest recall on the locked test is v1 0.449, v2n 0.367, v2s 0.327 and v2m 0.449.

**Reading:**
- **Not every v2 model is worse on vests.** YOLOv8m matches v1's vest recall and has a higher vest mAP, so the planned combined detector (v2 for helmet and person, v1 for vests) was **not built**; its condition was not met.
- **The tie-break cost vest performance.** The selection rule broke the YOLOv8s/YOLOv8m validation tie (0.6480 vs 0.6479) in favour of the smaller model. On the locked test YOLOv8m is better on every class shown, so in hindsight the tie-break cost vest performance.
- **YOLOv8m cannot be claimed as "the" PPE-v2.** That would be choosing on the locked test. Using YOLOv8m would be an operator decision informed by the test, and a clean claim would need a fresh held-out set.
- **Batch-size note:** the post-hoc validation table uses batch 16, matching the test settings, while selection used batch 8. Validation figures therefore differ by about 0.01, and YOLOv8s and YOLOv8m still tie within 0.01 (0.638 vs 0.645).

**Artifacts:**
- `models/ppe_yolov8_v2_best.pt` and `models/ppe_v2_training_metadata.json`;
- `results/selection_v2/`;
- `results/final_test_v2/`;
- `results/posthoc_v2/` (post-hoc);
- `results/training_v2/<candidate>/results.csv`.

`tests/test_ppe_v2_artifacts.py` checks that the v1 weights and config are unchanged and that the recorded selection follows the declared rule.

## Runtime detector: PPE-v2m (2026-10-14)

**Operator decision (2026-10-14):** the runtime uses **PPE-v2m** (YOLOv8m at 1024 px, the post-hoc candidate `v2m1024`). It was chosen *after* the post-hoc locked-test evaluation because it avoids the official v2s1024 vest regression, so it is a **test-informed choice**: its locked-test figures (overall mAP@0.5 0.625, vest recall 0.449) are optimistic until confirmed on a fresh held-out set. The official, validation-selected PPE-v2 result remains v2s1024.

- **Frozen configuration:** `models/ppe_config_v2m.json` (configuration `PPE-v2m`). The policy, thresholds and association are identical to PPE-v1 (PPE-POLICY-v1: helmet and safety vest, confidence 0.25, IoU 0.7, containment 0.5); only the detector and its 1024 px input differ. Weights `models/ppe_yolov8_v2m_best.pt` (SHA-256 `ae2e58d5…`, the exact model scored post-hoc); provenance and the test-informed status in `models/ppe_v2m_metadata.json`.
- **Selection:** the backend reads `DCG_PPE_DETECTOR` (`v2m` default; `v1` returns to the frozen PPE-v1 without a code change) and passes it to the worker; unknown values are refused (503). `PPECompliancePipeline()` called directly still defaults to PPE-v1.
- **Runtime check before switching** (`src/evaluate_runtime_compliance.py`, `results/runtime_v2m/`; validation split only, locked test not read):

| | PPE-v1 | PPE-v2m |
|---|---:|---:|
| Image status agrees with ground truth (810 images) | 94.8% | 95.3% |
| Truly non-compliant images flagged NON_COMPLIANT (748) | 98.8% | 99.2% |
| Truly non-compliant images reported COMPLIANT | 0.3% (2) | 0.3% (2) |
| Truly compliant images flagged NON_COMPLIANT (of 8) | 5 | 5 |
| Upload worker (new process, model load, one 2493 × 1662 image), median | 3.90 s | 4.06 s |
| Inference per image when loaded, median | 59 ms | 68 ms |

- **Reading:** the frozen policy behaves at least as well with PPE-v2m, and an upload takes about 0.16 s longer, dominated by process start-up rather than the model. SH17 is a poor test of false alarms: only 8 of 810 validation images are fully compliant, so that figure rests on 8 images. Data-centre images with compliant staff would test it properly.
- **Tests:** `tests/test_ppe_v2m_runtime.py` (weights hash, same policy as v1, test-informed status recorded, v1 still selectable); `presentation/backend/tests/test_ppe_image_validation.py` (setting default, pass-through, unknown value refused).

## External test: Safety Helmet and Reflective Jacket (2026-10-14)

This is an independent check on far more helmets and vests than SH17 offers. It uses the **test split** of Naik (2023), a Kaggle dataset under Apache 2.0 (`src/evaluate_external_helmet_jacket.py`, `results/external_helmet_jacket/`).
- **Protocol** (committed before running in `63b94b8`): nothing is trained, selected or tuned on it, and no model is changed.
- **Overlap removed:** test images that are near-duplicates of any SH17 image (difference hash, Hamming distance ≤ 6) are excluded. 4 of 1,575 were, leaving 1,571.
- **Class mapping:** Safety-Helmet → helmet, Reflective-Jacket → safety-vest, giving **3,080 helmets and 2,343 vests**.
- **Settings:** the same as the SH17 locked evaluations.

| Model (input size) | Helmet mAP@0.5 | Helmet recall at conf 0.25 (95% CI) | Vest mAP@0.5 | Vest recall at conf 0.25 (95% CI) |
|---|---:|---|---:|---|
| PPE-v1 (640) | **0.495** | **0.361** (0.344–0.378) | 0.368 | 0.269 (0.251–0.287) |
| PPE-v2 official, v2s (1024) | 0.428 | 0.306 (0.290–0.323) | 0.325 | 0.274 (0.256–0.292) |
| PPE-v2m runtime (1024) | 0.401 | 0.278 (0.263–0.294) | 0.418 | 0.257 (0.239–0.275) |

**Input-size sensitivity** (explanatory, not used to choose; `src/evaluate_external_sensitivity.py`): these images are only 640 × 640, so at 1024 px the v2 models see upscaled, blurred input. At 640 px:
- **v2s:** helmet 0.458 / 0.332, vest 0.416 / 0.286.
- **v2m:** helmet 0.466 / 0.335, vest **0.495 / 0.312**.

**Reading:**
- **All models generalise poorly to this dataset.** Helmet mAP is 0.40–0.50 here against about 0.70 on SH17. The likely reasons are a different image source, pre-resized low-resolution images, many small objects and a looser "reflective jacket" label.
- **Helmets:** PPE-v1 is the best of the three here, which reverses the SH17 result. Part of the v2 gap is the upscaling (it narrows at 640 px), but v1 still leads.
- **Vests:** PPE-v2m has the best vest mAP. At 640 px it also has the best vest recall (0.312 against v1's 0.269), with intervals that barely touch. At its runtime size of 1024 px, vest recall is level with v1.
- **What is not measured:** compliance, because the dataset has no person labels. Camera images are usually larger than 1024 px, so the 640-px images favour v1 in a way runtime images would not.
- **Conclusion:** no model dominates across both datasets. The improvement claimed for v2 holds on SH17-like images; on other sources, helmets favour v1 and vests favour v2m. PPE-v2m as the runtime choice is supported for vests and not for helmets. Data-centre images, or training on more varied PPE data, are the way to settle this.

## PPE-v3: SH17 plus the Kaggle helmet/jacket training data (2026-10-15)

**Why:** vests stayed the weak class (SH17 has a few hundred). The Kaggle *Safety Helmet and Reflective Jacket* dataset (Naik 2023, Apache 2.0), already used for the external test, has a training split with about 14,000 helmets and 11,000 jackets.

**Protocol** (committed and pushed before training, `f23f01e`; `src/train_v3.py`, `src/evaluate_v3.py`):
- **Data:** the SH17 PPE-v1 development split plus Kaggle train/valid, minus near-duplicates (difference hash, Hamming ≤ 6) of any SH17 or Kaggle-test image: 377 training and 87 validation images were dropped, a real leak in the source dataset. Result: 13,452 training images (6,479 SH17 + 6,973 Kaggle; 13,376 Kaggle helmets and 10,863 vests) and 2,298 validation images.
- **Pseudo-labels:** the Kaggle images label only helmets and jackets, so PPE-v2m added its own detections (confidence ≥ 0.5, 640 px) for every other class, chiefly 9,626 people, so that people are not learned as background. Helmet and vest labels came only from the dataset.
- **One candidate:** YOLOv8m at 1024 px, initialised from PPE-v2m, 30 epochs (paused by the operator after 4 epochs and resumed from the checkpoint; recorded in the metadata).
- **Acceptance on validation only:** mean helmet/vest mAP@0.5 over SH17 validation and Kaggle validation must beat PPE-v2m by ≥ 0.01, with SH17 person mAP@0.5 at most 0.02 lower.
- **Test once:** Kaggle test (now same-source data) and the SH17 locked test (already used for PPE-v2 decisions; comparison only).

**Validation (selection):**

| Model | Criterion | SH17 helmet / vest / person mAP@0.5 | Kaggle helmet / vest mAP@0.5 |
|---|---:|---|---|
| PPE-v1 | 0.492 | 0.656 / 0.472 / 0.903 | 0.498 / 0.344 |
| PPE-v2m (runtime) | 0.526 | 0.713 / 0.577 / 0.917 | 0.406 / 0.409 |
| **PPE-v3m** | **0.790** | 0.636 / 0.596 / 0.913 | **0.970 / 0.958** |

Accepted (gain +0.264; person −0.004). Note that the gain comes from the Kaggle half: on SH17 validation v3 is lower on helmets (0.636 vs 0.713).

**Final test (run once):**

| Model | Kaggle helmet mAP@0.5 (R) | Kaggle vest mAP@0.5 (R) | SH17 helmet mAP@0.5 (R) | SH17 vest mAP@0.5 (R) | SH17 person mAP@0.5 | SH17 all mAP@0.5 |
|---|---|---|---|---|---:|---:|
| PPE-v1 | 0.495 (0.433) | 0.368 (0.359) | 0.676 (0.603) | 0.372 (0.449) | 0.869 | 0.545 |
| PPE-v2m (runtime) | 0.401 (0.360) | 0.418 (0.377) | **0.739** (0.664) | 0.416 (**0.449**) | 0.900 | **0.625** |
| **PPE-v3m** | **0.962 (0.903)** | **0.958 (0.879)** | 0.727 (0.654) | **0.442** (0.388) | 0.900 | 0.619 |

**Reading:**
- **On images like its new training data, v3 is far better:** helmet and vest mAP rise from about 0.4 to 0.96. This test is same-source (different images, same collection and labelling style), so it shows learning of that domain, not general improvement.
- **On SH17 it is not better than PPE-v2m:** helmet mAP 0.727 vs 0.739, all-class 0.619 vs 0.625, vest mAP higher (0.442 vs 0.416) but vest recall lower (0.388 vs 0.449). Person detection is unchanged (0.900), so the pseudo-labels did not damage it.
- **Detection quality depends strongly on the image domain.** Which model suits a data centre depends on whether its cameras look more like SH17 or like the Kaggle images, so the deciding evidence is fresh data-centre-like images.
- **Runtime unchanged:** PPE-v2m stays the live detector. v3 is stored (`models/ppe_yolov8_v3m_best.pt`, `models/ppe_v3m_metadata.json`) but not selectable at runtime until the operator decides; switching would also need the compliance and latency check run for PPE-v2m.
- **Artifacts:** `results/training_v3/` (training curves, `prepare_summary.json`), `results/selection_v3/`, `results/final_test_v3/`; `tests/test_ppe_v3_artifacts.py`.

## Runtime flow

```text
image -> YOLOv8 detections (PPE-v2m by default, PPE-v1 selectable) -> person/PPE association
      -> frozen PPE policy -> COMPLIANT / NON_COMPLIANT / NO_PERSON
      -> Reasoning layer adapter
```

## Repository artifacts

```text
models/
  ppe_yolov8_best.pt
  ppe_config.json
  ppe_training_metadata.json
  ppe_yolov8_v2_best.pt, ppe_v2_training_metadata.json      (official PPE-v2, v2s1024)
  ppe_yolov8_v2m_best.pt, ppe_config_v2m.json, ppe_v2m_metadata.json   (runtime PPE-v2m)

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
