# PPE-v1 vs PPE-v2m vs PPE-v3m: final test (run once)

Kaggle test: same-source held-out data (Kaggle train and validation were used to train v3), SH17 near-duplicates removed. SH17 locked test: already used for PPE-v2 decisions, comparison only.

| Model | Kaggle helmet P / R / mAP@0.5 | Kaggle vest P / R / mAP@0.5 | SH17 helmet R / mAP@0.5 | SH17 vest R / mAP@0.5 | SH17 person mAP@0.5 | SH17 all mAP@0.5 |
|---|---|---|---|---|---:|---:|
| PPE-v1 | 0.728 / 0.433 / 0.495 | 0.528 / 0.359 / 0.368 | 0.603 / 0.676 | 0.449 / 0.372 | 0.869 | 0.545 |
| PPE-v2m (runtime) | 0.742 / 0.360 / 0.401 | 0.644 / 0.377 / 0.418 | 0.664 / 0.739 | 0.449 / 0.416 | 0.900 | 0.625 |
| PPE-v3m (v3m1024) | 0.946 / 0.903 / 0.962 | 0.925 / 0.879 / 0.958 | 0.654 / 0.727 | 0.388 / 0.442 | 0.900 | 0.619 |
