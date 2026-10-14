# External test: Safety Helmet and Reflective Jacket (Kaggle), test split

EXTERNAL TEST (independent of SH17; nothing trained, selected or tuned on it). 1571 of 1575 test images (4 near-duplicates of SH17 images excluded); 3080 helmets, 2343 reflective jackets scored as SH17 helmet / safety-vest. Images are 640 x 640.

| Model | Class | Precision | Recall | mAP@0.5 | mAP@0.5:0.95 | Recall at conf 0.25 (95% CI) |
|---|---|---:|---:|---:|---:|---|
| PPE-v1 | helmet | 0.728 | 0.433 | 0.495 | 0.235 | 0.361 (0.344–0.378) |
| PPE-v1 | safety-vest | 0.528 | 0.359 | 0.368 | 0.172 | 0.269 (0.251–0.287) |
| PPE-v2 official (v2s1024) | helmet | 0.752 | 0.372 | 0.428 | 0.218 | 0.306 (0.290–0.323) |
| PPE-v2 official (v2s1024) | safety-vest | 0.450 | 0.361 | 0.325 | 0.151 | 0.274 (0.256–0.292) |
| PPE-v2m (runtime) | helmet | 0.742 | 0.360 | 0.401 | 0.200 | 0.278 (0.263–0.294) |
| PPE-v2m (runtime) | safety-vest | 0.644 | 0.377 | 0.418 | 0.209 | 0.257 (0.239–0.275) |

Caveats: reflective jacket is not identical to SH17's safety vest; the images were pre-resized to 640 x 640; the dataset has no person labels, so compliance (person + helmet + vest) cannot be measured here.
