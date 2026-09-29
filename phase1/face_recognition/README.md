# Face Recognition

## Purpose

DC-GUARDIAN Face Recognition v1 provides controlled identity evidence for the physical-security domain. Recognition is **not** treated as authorization; Phase 2 derives authorization from the graph topology.

## Frozen baseline

- Embedding model: ArcFace
- Detector/alignment backend: RetinaFace
- Embedding dimension: 512
- Distance metric: cosine
- Recognition threshold: 0.50
- Threshold source: validation only

Runtime flow:

```text
image -> RetinaFace -> ArcFace embedding -> frozen enrollment matching
      -> RECOGNIZED / UNKNOWN -> Phase 2 adapter
```

## Locked final test

The controlled locked test contains 15 images: 6 known-person images and 9 unknown-person images.

| Measure | Result |
|---|---:|
| Known identifications | 6 / 6 |
| Known identification rate | 100% |
| Unknown rejections | 9 / 9 |
| Unknown rejection rate | 100% |
| False acceptances | 0 |
| False rejections | 0 |
| Misidentifications | 0 |
| Mean latency | 2741 ms/image |
| Median latency | 2455 ms/image |

The threshold and enrollment database were not changed during the final test.

These results are from a small controlled proof-of-concept dataset and must not be generalized as production biometric accuracy.

## Repository artifacts

```text
models/
  enrollment_metadata.json
  face_recognition_config.json

results/
  validation/
  final_test/

src/
  face_embedding.py
  face_recognizer.py
  face_pipeline.py
```

The private controlled face photographs and the enrollment embedding database are intentionally excluded from Git.

## Phase 2 contract

The Phase 1 output preserves recognition evidence only. Phase 2 adds camera/topology context and derives authorization from declared `Person -> AUTHORIZED_FOR -> Zone` relationships.

## Limitations

The controlled dataset is small. Production use would require broader identity, lighting, pose, camera, occlusion/PPE, fairness, privacy, and biometric-security evaluation.
