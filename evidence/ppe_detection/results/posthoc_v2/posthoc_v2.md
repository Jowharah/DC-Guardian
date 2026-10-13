# PPE-v2 post-hoc analysis

**POST-HOC (evaluated after selection; not used to choose).** v2s1024 (selected on validation, evaluated once) remains the official PPE-v2 result. Same 810 locked images and settings as the official evaluations. Re-scored official models match their official results: {'PPE-v1': {'official_map50': 0.5447, 'rescored_map50': 0.5447}, 'v2s1024': {'official_map50': 0.5951, 'rescored_map50': 0.5951}}.

## Locked test (post-hoc)

**All classes**

| Model | Precision | Recall | mAP@0.5 | mAP@0.5:0.95 |
|---|---:|---:|---:|---:|
| PPE-v1 (frozen baseline) | 0.689 | 0.524 | 0.545 | 0.336 |
| v2n1024 (unselected candidate) | 0.712 | 0.532 | 0.578 | 0.369 |
| v2s1024 (official PPE-v2 (selected)) | 0.709 | 0.535 | 0.595 | 0.385 |
| v2m1024 (unselected candidate) | 0.669 | 0.612 | 0.625 | 0.416 |

**helmet**

| Model | Precision | Recall | mAP@0.5 | mAP@0.5:0.95 |
|---|---:|---:|---:|---:|
| PPE-v1 (frozen baseline) | 0.732 | 0.603 | 0.676 | 0.456 |
| v2n1024 (unselected candidate) | 0.755 | 0.592 | 0.744 | 0.513 |
| v2s1024 (official PPE-v2 (selected)) | 0.761 | 0.654 | 0.708 | 0.493 |
| v2m1024 (unselected candidate) | 0.753 | 0.664 | 0.739 | 0.547 |

**safety-vest**

| Model | Precision | Recall | mAP@0.5 | mAP@0.5:0.95 |
|---|---:|---:|---:|---:|
| PPE-v1 (frozen baseline) | 0.621 | 0.449 | 0.372 | 0.220 |
| v2n1024 (unselected candidate) | 0.560 | 0.367 | 0.383 | 0.245 |
| v2s1024 (official PPE-v2 (selected)) | 0.582 | 0.245 | 0.317 | 0.175 |
| v2m1024 (unselected candidate) | 0.540 | 0.449 | 0.416 | 0.263 |

**person**

| Model | Precision | Recall | mAP@0.5 | mAP@0.5:0.95 |
|---|---:|---:|---:|---:|
| PPE-v1 (frozen baseline) | 0.836 | 0.854 | 0.869 | 0.691 |
| v2n1024 (unselected candidate) | 0.841 | 0.855 | 0.884 | 0.676 |
| v2s1024 (official PPE-v2 (selected)) | 0.861 | 0.856 | 0.893 | 0.692 |
| v2m1024 (unselected candidate) | 0.807 | 0.894 | 0.900 | 0.736 |

## Validation (810 original images)

**All classes**

| Model | Precision | Recall | mAP@0.5 | mAP@0.5:0.95 |
|---|---:|---:|---:|---:|
| PPE-v1 (frozen baseline) | 0.679 | 0.520 | 0.567 | 0.352 |
| v2n1024 (unselected candidate) | 0.634 | 0.574 | 0.612 | 0.383 |
| v2s1024 (official PPE-v2 (selected)) | 0.716 | 0.612 | 0.658 | 0.429 |
| v2m1024 (unselected candidate) | 0.797 | 0.621 | 0.691 | 0.462 |

**helmet**

| Model | Precision | Recall | mAP@0.5 | mAP@0.5:0.95 |
|---|---:|---:|---:|---:|
| PPE-v1 (frozen baseline) | 0.768 | 0.539 | 0.656 | 0.432 |
| v2n1024 (unselected candidate) | 0.766 | 0.566 | 0.711 | 0.478 |
| v2s1024 (official PPE-v2 (selected)) | 0.773 | 0.566 | 0.713 | 0.484 |
| v2m1024 (unselected candidate) | 0.750 | 0.579 | 0.713 | 0.496 |

**safety-vest**

| Model | Precision | Recall | mAP@0.5 | mAP@0.5:0.95 |
|---|---:|---:|---:|---:|
| PPE-v1 (frozen baseline) | 0.566 | 0.438 | 0.472 | 0.285 |
| v2n1024 (unselected candidate) | 0.543 | 0.479 | 0.518 | 0.307 |
| v2s1024 (official PPE-v2 (selected)) | 0.682 | 0.396 | 0.562 | 0.345 |
| v2m1024 (unselected candidate) | 0.799 | 0.396 | 0.577 | 0.374 |

**person**

| Model | Precision | Recall | mAP@0.5 | mAP@0.5:0.95 |
|---|---:|---:|---:|---:|
| PPE-v1 (frozen baseline) | 0.850 | 0.877 | 0.903 | 0.710 |
| v2n1024 (unselected candidate) | 0.818 | 0.888 | 0.913 | 0.684 |
| v2s1024 (official PPE-v2 (selected)) | 0.840 | 0.898 | 0.922 | 0.707 |
| v2m1024 (unselected candidate) | 0.887 | 0.885 | 0.917 | 0.731 |

## At the runtime confidence threshold (0.25), locked test

| Model | Helmet precision / recall | Vest precision / recall |
|---|---|---|
| PPE-v1 | 0.704 / 0.611 | 0.580 / 0.449 |
| v2n1024 | 0.720 / 0.654 | 0.501 / 0.367 |
| v2s1024 | 0.705 / 0.674 | 0.465 / 0.327 |
| v2m1024 | 0.749 / 0.650 | 0.546 / 0.449 |

Every v2 candidate worse than PPE-v1 on vests (locked test, mAP@0.5 and recall): **False**.
