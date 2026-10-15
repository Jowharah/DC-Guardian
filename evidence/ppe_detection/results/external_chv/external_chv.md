# Third-dataset test: CHV (Color Helmet and Vest)

THIRD-DATASET TEST (CHV; nothing trained, selected or tuned on it; SH17 and Kaggle near-duplicates excluded). 1155 of 1330 images (175 near-duplicates of SH17 or Kaggle images excluded); 3531 people, 3192 helmets, 1505 vests.

## Detection

| Model | Class | Precision | Recall | mAP@0.5 | mAP@0.5:0.95 | Recall at conf 0.25 (95% CI) |
|---|---|---:|---:|---:|---:|---|
| PPE-v1 | helmet | 0.897 | 0.590 | 0.754 | 0.393 | 0.609 (0.592–0.625) |
| PPE-v1 | safety-vest | 0.745 | 0.621 | 0.687 | 0.323 | 0.655 (0.631–0.679) |
| PPE-v1 | person | 0.823 | 0.835 | 0.837 | 0.413 | 0.842 (0.830–0.854) |
| PPE-v2 official (v2s1024) | helmet | 0.919 | 0.768 | 0.866 | 0.460 | 0.773 (0.758–0.787) |
| PPE-v2 official (v2s1024) | safety-vest | 0.758 | 0.639 | 0.707 | 0.335 | 0.645 (0.620–0.669) |
| PPE-v2 official (v2s1024) | person | 0.828 | 0.871 | 0.862 | 0.423 | 0.872 (0.860–0.882) |
| PPE-v2m (runtime) | helmet | 0.916 | 0.779 | 0.863 | 0.467 | 0.759 (0.744–0.774) |
| PPE-v2m (runtime) | safety-vest | 0.806 | 0.659 | 0.731 | 0.346 | 0.632 (0.608–0.656) |
| PPE-v2m (runtime) | person | 0.820 | 0.880 | 0.867 | 0.432 | 0.877 (0.865–0.887) |
| PPE-v3m (PR #31) | helmet | 0.922 | 0.826 | 0.882 | 0.459 | 0.851 (0.838–0.863) |
| PPE-v3m (PR #31) | safety-vest | 0.813 | 0.813 | 0.836 | 0.426 | 0.838 (0.818–0.856) |
| PPE-v3m (PR #31) | person | 0.880 | 0.860 | 0.870 | 0.439 | 0.870 (0.859–0.881) |

## Compliance (image status shown on the dashboard)

Ground truth (frozen policy on the labelled boxes): {'NON_COMPLIANT': 821, 'COMPLIANT': 327, 'NO_PERSON': 7}.

| Model | Agreement with truth | Violations caught | False alarms | Missed violations (reported COMPLIANT) |
|---|---:|---:|---:|---:|
| PPE-v1 | 81.0% | 95.6% | 54.1% | 4.4% |
| PPE-v2 official (v2s1024) | 79.3% | 95.6% | 59.9% | 3.8% |
| PPE-v2m (runtime) | 80.1% | 96.7% | 59.9% | 3.2% |
| PPE-v3m (PR #31) | 84.0% | 90.7% | 31.5% | 9.3% |

Caveats: CHV images come from online sources and existing open datasets (overlaps with SH17 and the Kaggle set were removed by difference hash); construction scenes, not data-centre ones; PPE-v3m is PR #31's model, not yet merged or selectable at runtime.
