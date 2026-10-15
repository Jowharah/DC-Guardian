# PPE-v3 selection (validation only)

Rule: accept if criterion gain over PPE-v2m >= 0.01 and SH17 person mAP@0.5 drop <= 0.02. Criterion = mean of [helmet/vest mAP@0.5 on SH17 validation (810 original images), helmet/vest mAP@0.5 on Kaggle validation (dataset labels, near-duplicates removed)].

| Model | Criterion | SH17 helmet / vest / person mAP@0.5 | Kaggle helmet / vest mAP@0.5 | SH17 all-class mAP@0.5 |
|---|---:|---|---|---:|
| PPE-v1 | 0.4924 | 0.656 / 0.472 / 0.903 | 0.498 / 0.344 | 0.567 |
| PPE-v2m (runtime) | 0.5260 | 0.713 / 0.577 / 0.917 | 0.406 / 0.409 | 0.691 |
| PPE-v3m (v3m1024) | 0.7900 | 0.636 / 0.596 / 0.913 | 0.970 / 0.958 | 0.662 |

Gain over PPE-v2m: +0.2640; person mAP@0.5 drop: +0.0036. **Accepted.**
