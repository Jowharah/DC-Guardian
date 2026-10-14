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

## PPE-v3: adding the second dataset to training (2026-10-15)

The external test showed both a domain gap and the vest weakness, so the Kaggle training split (about 14,000 helmets and 11,000 jackets) was added to SH17. Its images label only helmets and jackets, so people and the other classes were pseudo-labelled by PPE-v2m; near-duplicates of any test image (377 in the Kaggle training split) were removed first. The protocol was committed before training: one YOLOv8m candidate from the PPE-v2m weights, accepted on validation only if it beat PPE-v2m by 0.01 on a helmet/vest criterion averaged over both datasets without losing more than 0.02 person mAP.

| Final test (run once) | Kaggle helmet / vest mAP@0.5 | SH17 helmet / vest mAP@0.5 | SH17 vest recall | SH17 all mAP@0.5 |
|---|---|---|---:|---:|
| PPE-v1 | 0.495 / 0.368 | 0.676 / 0.372 | 0.449 | 0.545 |
| PPE-v2m (runtime) | 0.401 / 0.418 | 0.739 / 0.416 | 0.449 | 0.625 |
| PPE-v3m | **0.962 / 0.958** | 0.727 / **0.442** | 0.388 | 0.619 |

- **More data of one kind transfers to that kind only.** v3 is excellent on held-out Kaggle images (same source as its new training data) but no better than PPE-v2m on SH17: a little lower on helmets and overall, a little higher on vest mAP, lower on vest recall.
- **The person class was protected:** SH17 person mAP is unchanged (0.900), so pseudo-labelling avoided the expected failure.
- **Implication:** PPE accuracy is domain-dependent, and the right model for a data centre can only be chosen on images from that setting. PPE-v2m stays at runtime.

## Limitations

- one training seed per candidate;
- small helmet and vest samples (78 and 49 test instances);
- the SH17 images are not data-centre scenes;
- compliance-level accuracy was measured only at image level on validation, where 748 of 810 images are non-compliant and only 8 fully compliant, so false alarms on compliant staff are barely tested;
- the runtime model (YOLOv8m) was chosen after seeing the locked test, so its test figures are optimistic until a fresh held-out set confirms them; the external test confirms it for vests but not for helmets;
- the external dataset maps "reflective jacket" onto "safety vest", is pre-resized to 640 px and has no person labels, so compliance is not measured there;
- PPE-v3's Kaggle test is same-source, and its training used pseudo-labels from PPE-v2m, which carry PPE-v2m's errors into the non-PPE classes.
