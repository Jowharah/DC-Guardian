# PPE-v2 candidate selection (validation, 810 images)

Criterion: mean mAP@0.5 of helmet and safety-vest; within 0.01 of the best, the smaller model wins; must beat PPE-v1. The locked test was not used.

| Model | Size | Criterion | Helmet mAP@0.5 / recall | Vest mAP@0.5 / recall | Overall mAP@0.5 | Overall recall | ms/image |
|---|---:|---:|---|---|---:|---:|---:|
| PPE-v1 (frozen) (yolov8n) | 640 | 0.5687 | 0.670 / 0.539 | 0.468 / 0.438 | 0.5696 | 0.5212 | 10.65 |
| v2m1024 (yolov8m) | 1024 | 0.6479 | 0.713 / 0.579 | 0.583 / 0.417 | 0.6914 | 0.6223 | 13.43 |
| v2n1024 (yolov8n) | 1024 | 0.6161 | 0.711 / 0.566 | 0.521 / 0.458 | 0.6109 | 0.5706 | 10.92 |
| v2s1024 (yolov8s) **(selected)** | 1024 | 0.6480 | 0.713 / 0.566 | 0.583 / 0.396 | 0.6594 | 0.6117 | 13.01 |

Selected: **v2s1024**.
