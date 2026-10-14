# External test — input-size sensitivity

SENSITIVITY (explanatory; v2 models at 640 px instead of 1024 px; not used to choose).

| Model | Input size | Helmet mAP@0.5 | Helmet recall at 0.25 | Vest mAP@0.5 | Vest recall at 0.25 |
|---|---:|---:|---:|---:|---:|
| PPE-v1 | 640 | 0.495 | 0.361 | 0.368 | 0.269 |
| PPE-v2 official (v2s1024) | 1024 | 0.428 | 0.306 | 0.325 | 0.274 |
| PPE-v2 official (v2s1024) | 640 | 0.458 | 0.332 | 0.416 | 0.286 |
| PPE-v2m (runtime) | 1024 | 0.401 | 0.278 | 0.418 | 0.257 |
| PPE-v2m (runtime) | 640 | 0.466 | 0.335 | 0.495 | 0.312 |
