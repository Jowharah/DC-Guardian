# PPE-v1 vs PPE-v2 on the locked final test (810 images)

PPE-v2 = v2s1024 (yolov8s, 1024 px), selected on validation only and evaluated once. PPE-v1 figures are the frozen v1 result.

| Classes | Precision | Recall | mAP@0.5 | mAP@0.5:0.95 |
|---|---|---|---|---|
| All classes | 0.689 → 0.709 | 0.524 → 0.535 | 0.545 → 0.595 | 0.336 → 0.385 |
| helmet | 0.732 → 0.761 | 0.603 → 0.654 | 0.676 → 0.708 | 0.456 → 0.493 |
| safety-vest | 0.621 → 0.582 | 0.449 → 0.245 | 0.372 → 0.317 | 0.220 → 0.175 |
| person | 0.836 → 0.861 | 0.854 → 0.856 | 0.869 → 0.893 | 0.691 → 0.692 |
