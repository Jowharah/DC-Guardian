# Model enhancement: PPE detector v2

*Draft report section (2026-10-13). Detailed tables: `evidence/ppe_detection/README.md`; generated results in `evidence/ppe_detection/results/selection_v2/`, `final_test_v2/` and `posthoc_v2/`.*

## Motivation

The frozen PPE detector (PPE-v1: YOLOv8n trained at 640 px) had the lowest recall of the project's detectors. On its locked test (810 SH17 images) it found 52% of objects, 60% of helmets and 45% of safety vests. The SH17 photos are 2,000–6,000 px wide, so at 640 px a helmet or vest is only a few pixels across. A larger model at a higher input resolution was the most direct improvement.

## Method

- **Protocol fixed first:** the protocol was committed to the repository before training. It was revised once, before any result existed, to reduce training time.
- **Same data split:** all candidates use PPE-v1's training and validation split. The locked test images are kept apart, and the frozen v1 model is hash-checked and never modified.
- **Candidates:** three, all at 1024 px for 60 epochs: YOLOv8n (the effect of resolution alone), YOLOv8s and YOLOv8m.
- **Selection rule, declared in advance:**
  - Measure: mean mAP@0.5 of the two classes the compliance policy requires (helmet and safety vest), on validation only.
  - Tie-break: within 0.01 of the best, the smaller model wins.
  - Floor: the winner must beat PPE-v1.
- **Locked test:** the selected model is evaluated once, by a script that refuses a second run.

## Results

**Selection (validation):**
- scores: PPE-v1 0.569; YOLOv8n 0.616; YOLOv8s 0.648; YOLOv8m 0.648;
- YOLOv8s and YOLOv8m tie (0.6480 against 0.6479), so **YOLOv8s became PPE-v2**.

**Official locked test (PPE-v1 → PPE-v2):**

| | Recall | mAP@0.5 |
|---|---|---|
| All classes | 0.524 → 0.535 | 0.545 → 0.595 |
| Helmet | 0.603 → 0.654 | 0.676 → 0.708 |
| Safety vest | 0.449 → **0.245** | 0.372 → 0.317 |

- **Improved:** overall detection and helmet recall.
- **Regressed:** safety-vest recall, the opposite of what validation showed.

**Post-hoc analysis (after selection; not used to choose):** the two unselected candidates were then scored on the same locked test.

| Locked test, post-hoc | All-class mAP@0.5 | Helmet recall | Vest recall | Vest mAP@0.5 |
|---|---:|---:|---:|---:|
| PPE-v1 | 0.545 | 0.603 | 0.449 | 0.372 |
| YOLOv8n | 0.578 | 0.592 | 0.367 | 0.383 |
| YOLOv8s (official) | 0.595 | 0.654 | 0.245 | 0.317 |
| YOLOv8m | 0.625 | 0.664 | 0.449 | 0.416 |

YOLOv8m matches v1's vest recall and improves every other figure shown. A combined detector (v2 for helmet and person, v1 for vests) had been planned for the case where every v2 candidate was worse on vests. That condition did not hold, so it was not built.

## Discussion

- **Larger models at higher resolution improve PPE detection overall.** All three candidates beat v1 on all-class mAP on both validation and the locked test.
- **Vests remain the weak class, and the small sample makes its result unstable.** Validation and test each hold fewer than 50 vests in about 23 images, so a difference of 10 vests reverses a conclusion. Validation favoured the selected YOLOv8s on vests; the locked test did not.
- **The pre-declared tie-break cost vest performance in hindsight.** YOLOv8m does better on the test, but choosing it now would be selection on the test. Using it at runtime would be an operator decision informed by the test, and an independent claim would need a fresh held-out set.
- **Runtime choice (operator, 2026-10-14):** the deployed pipeline now uses YOLOv8m (PPE-v2m), described as a test-informed choice. Before switching, the frozen compliance policy was re-checked with it on the validation images: the dashboard status agrees with ground truth on 95.3% of images (PPE-v1 94.8%), violations caught 99.2% (98.8%), the same 2 violations reported compliant, and an upload takes 4.06 s against 3.90 s. PPE-v1 remains selectable with one setting (`DCG_PPE_DETECTOR=v1`).

## External test on a second dataset (2026-10-14)

To get beyond SH17's 49 test vests, the three detectors were scored on the test split of a second public dataset, *Safety Helmet and Reflective Jacket* (Naik, 2023; Apache 2.0).
- **Protocol:** nothing was trained or tuned on it, and the protocol was committed before running.
- **Data:** 4 near-duplicates of SH17 images were removed, leaving 1,571 images with 3,080 helmets and 2,343 reflective jackets. The jackets were scored as SH17 safety vests.

| Model (input size) | Helmet mAP@0.5 | Helmet recall* | Vest mAP@0.5 | Vest recall* |
|---|---:|---:|---:|---:|
| PPE-v1 (640) | **0.495** | **0.361** | 0.368 | 0.269 |
| PPE-v2 official, YOLOv8s (1024) | 0.428 | 0.306 | 0.325 | 0.274 |
| PPE-v2m runtime, YOLOv8m (1024) | 0.401 | 0.278 | 0.418 | 0.257 |
| PPE-v2m at 640 (sensitivity) | 0.466 | 0.335 | **0.495** | **0.312** |

\*Recall at the runtime confidence threshold 0.25. The 95% intervals are about ±0.02.

- **Every model scores well below its SH17 figures** (helmet mAP about 0.70 on SH17).
- **Helmets: v1 is best here,** the reverse of SH17.
- **Vests: v2m is best,** most clearly when run at the images' native 640 px.
- **Image size explains part of the v2 helmet gap:** these images are 640 × 640, so the 1024-px v2 models see upscaled input.
- **No single model wins on both datasets,** so the v2 improvement should be stated as dataset-dependent. The deployed v2m is supported by independent data for vests, not for helmets.

## Third-dataset test: CHV (2026-10-15)

After the PPE-v3 model (trained on SH17 plus the Kaggle data, PR #31), both earlier test sets had informed decisions. The four detectors were therefore scored on a third public dataset, CHV (Wang et al., 2021), which labels people, vests and helmets and was never used for training or selection.
- **Data:** 1,155 of its 1,330 images, after removing 175 near-duplicates of SH17 or Kaggle images.
- **Protocol:** committed before running.

| Model | Helmet mAP@0.5 | Helmet recall at 0.25 | Vest mAP@0.5 | Vest recall at 0.25 | Person mAP@0.5 |
|---|---:|---:|---:|---:|---:|
| PPE-v1 | 0.754 | 0.609 | 0.687 | 0.655 | 0.837 |
| PPE-v2 official (v2s) | 0.866 | 0.773 | 0.707 | 0.645 | 0.862 |
| PPE-v2m (runtime) | 0.863 | 0.759 | 0.731 | 0.632 | 0.867 |
| **PPE-v3m (PR #31)** | **0.882** | **0.851** | **0.836** | **0.838** | 0.870 |

The 95% intervals on recall are about ±0.015 for helmets and ±0.025 for vests; v3m's helmet and vest recall intervals do not overlap any other model's.

**Compliance** (the dashboard's image status against the frozen policy applied to the labelled boxes; 821 non-compliant, 327 compliant images):

| Model | Agreement | Violations caught | False alarms | Missed violations |
|---|---:|---:|---:|---:|
| PPE-v1 | 81.0% | 95.6% | 54.1% | 4.4% |
| PPE-v2 official (v2s) | 79.3% | 95.6% | 59.9% | 3.8% |
| PPE-v2m (runtime) | 80.1% | 96.7% | 59.9% | 3.2% |
| **PPE-v3m** | **84.0%** | 90.7% | **31.5%** | 9.3% |

**Reading:**
- **On truly unseen images, PPE-v3m detects helmets and vests clearly better than all earlier models.** This is the clean, independent evidence that the PPE work improved the detector.
- **For compliance, it trades fewer false alarms (31.5% against 60%) for more missed violations (9.3% against 3.2%).** Because a missed violation is the safety-critical error, deploying v3m is a policy decision rather than an automatic upgrade.

### Deployment decision

The deployed detector stays PPE-v2m, although PPE-v3m detects better. The deciding figure is the missed-violation rate. On CHV:
- **PPE-v3m:** reported 76 of 821 non-compliant images as compliant, and wrongly flagged 103 of 327 compliant images.
- **PPE-v2m:** reported 26 as compliant and wrongly flagged 196.

A false alarm reaches a human reviewer and is dismissed. A missed violation raises no alert and is never reviewed, so the system is tuned to minimise the error that escapes human oversight. This follows the project's principle that every alert goes to human review: false alarms are tolerable, silent misses are not. PPE-v3m could replace PPE-v2m once its vest threshold has been re-tuned on validation data to match PPE-v2m's miss rate and confirmed on fresh images.

## Limitations

- one training seed per candidate;
- small helmet and vest samples (78 and 49 test instances);
- the SH17 images are not data-centre scenes;
- compliance-level accuracy was measured only at image level on validation, where 748 of 810 images are non-compliant and only 8 fully compliant, so false alarms on compliant staff are barely tested;
- the runtime model (YOLOv8m) was chosen after seeing the locked test, so its test figures are optimistic until a fresh held-out set confirms them; the external test confirms it for vests but not for helmets;
- the external dataset maps "reflective jacket" onto "safety vest", is pre-resized to 640 px and has no person labels, so compliance is not measured there.
