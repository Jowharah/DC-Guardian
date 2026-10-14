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

## Limitations

- one training seed per candidate;
- small helmet and vest samples (78 and 49 test instances);
- the SH17 images are not data-centre scenes;
- compliance-level accuracy was measured only at image level on validation, where 748 of 810 images are non-compliant and only 8 fully compliant, so false alarms on compliant staff are barely tested;
- the runtime model (YOLOv8m) was chosen after seeing the locked test, so its test figures are optimistic until a fresh held-out set confirms them.
