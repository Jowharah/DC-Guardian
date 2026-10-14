"""
DC-Guardian Evidence
PPE — external test on the "Safety Helmet and Reflective Jacket" dataset

An independent check of PPE-v1, the official PPE-v2 (v2s1024) and the runtime
PPE-v2m on helmets and vests, with far more instances than the SH17 locked
test (49 vests). Protocol, fixed before any result (2026-10-14):

1. Only the dataset's TEST split is used; nothing is trained, selected or
   tuned on it, and no model is changed.
2. Images that are near-duplicates of any SH17 image (difference hash,
   Hamming distance <= HAMMING_MAX) are excluded, so the test is independent
   of SH17 training, validation and test images.
3. Classes are mapped into the SH17 label space: Safety-Helmet -> helmet,
   Reflective-Jacket -> safety-vest. "Reflective jacket" is close to but not
   the same as SH17's "safety vest". Only helmet and vest are scored; the
   dataset has no person labels, so person and the other classes are not.
4. Same settings as the SH17 locked evaluations (batch 16, workers 0, default
   confidence and IoU), each model at its own image size; recall is also
   reported at the runtime confidence 0.25 with a 95% Wilson interval.

Dataset: Nirav B. Naik (2023), Kaggle, Apache 2.0. Images are 640 x 640.

    .venv-ppe\\Scripts\\python.exe evidence\\ppe_detection\\src\\evaluate_external_helmet_jacket.py
"""

from __future__ import annotations

import hashlib
import json
import math
import shutil
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import torch
import yaml
from PIL import Image
from ultralytics import YOLO

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PPE = PROJECT_ROOT / "evidence" / "ppe_detection"
SOURCE = PPE / "data" / "raw" / "helmet_jacket" / "test"
SH17_IMAGES = PPE / "data" / "raw" / "SH17" / "images"
WORK = PPE / "data" / "processed" / "helmet_jacket_external"
OUT = PPE / "results" / "external_helmet_jacket"
MODELS = {
    "PPE-v1": (PPE / "models" / "ppe_yolov8_best.pt", 640),
    "PPE-v2 official (v2s1024)": (PPE / "models" / "ppe_yolov8_v2_best.pt", 1024),
    "PPE-v2m (runtime)": (PPE / "models" / "ppe_yolov8_v2m_best.pt", 1024),
}
CLASS_MAP = {0: 10, 1: 16}  # Safety-Helmet -> helmet, Reflective-Jacket -> safety-vest
SCORED = ("helmet", "safety-vest")
HAMMING_MAX = 6
RUNTIME_CONF = 0.25


def dhash(path: str) -> int:
    with Image.open(path) as image:
        image.draft("L", (64, 64))  # fast JPEG decode at reduced size
        small = image.convert("L").resize((9, 8), Image.LANCZOS)
    px = np.asarray(small, dtype=np.int16)
    bits = (px[:, 1:] > px[:, :-1]).flatten()
    return int("".join("1" if b else "0" for b in bits), 2)


def hashes(paths: list[Path]) -> list[int]:
    with ProcessPoolExecutor(max_workers=8) as pool:
        return list(pool.map(dhash, [str(p) for p in paths], chunksize=64))


def wilson(successes: float, n: int) -> list[float]:
    if n == 0:
        return [0.0, 0.0]
    z, p = 1.96, successes / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [round(centre - half, 4), round(centre + half, 4)]


def build_eval_set() -> dict:
    images = sorted((SOURCE / "images").iterdir())
    sh17 = sorted(p for p in SH17_IMAGES.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"})
    ext_hash, sh17_hash = hashes(images), np.array(hashes(sh17), dtype=np.uint64)
    duplicates = {}
    for image, h in zip(images, ext_hash):
        distance = np.array([bin(int(x) ^ h).count("1") for x in sh17_hash])
        if distance.min() <= HAMMING_MAX:
            duplicates[image.name] = sh17[int(distance.argmin())].name
    if WORK.exists():
        shutil.rmtree(WORK)
    (WORK / "images").mkdir(parents=True)
    (WORK / "labels").mkdir(parents=True)
    counts = {"helmet": 0, "safety-vest": 0}
    kept = []
    for image in images:
        if image.name in duplicates:
            continue
        shutil.copy2(image, WORK / "images" / image.name)
        lines = []
        for line in (SOURCE / "labels" / (image.stem + ".txt")).read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if parts:
                cls = CLASS_MAP[int(parts[0])]
                counts["helmet" if cls == 10 else "safety-vest"] += 1
                lines.append(" ".join([str(cls), *parts[1:]]))
        (WORK / "labels" / (image.stem + ".txt")).write_text("\n".join(lines) + "\n", encoding="utf-8")
        kept.append(str((WORK / "images" / image.name).resolve()))
    (WORK / "test_images.txt").write_text("\n".join(kept) + "\n", encoding="utf-8")
    names = yaml.safe_load((PPE / "data" / "processed" / "sh17_yolo" / "dataset.yaml").read_text(encoding="utf-8"))["names"]
    (WORK / "dataset.yaml").write_text(yaml.safe_dump({
        "train": str((WORK / "test_images.txt").resolve()), "val": str((WORK / "test_images.txt").resolve()),
        "test": str((WORK / "test_images.txt").resolve()), "nc": len(names), "names": names}, sort_keys=False),
        encoding="utf-8")
    return {"source_images": len(images), "sh17_images_compared": len(sh17), "hamming_max": HAMMING_MAX,
            "near_duplicates_of_sh17_excluded": len(duplicates), "duplicate_examples": dict(list(duplicates.items())[:10]),
            "images_evaluated": len(kept), "instances": counts}


def evaluate(weights: Path, imgsz: int, name: str, instances: dict) -> dict:
    model = YOLO(str(weights))
    m = model.val(data=str(WORK / "dataset.yaml"), split="test", imgsz=imgsz, batch=16, device=0, workers=0,
                  plots=False, project=str(OUT / "ultralytics"), name=name, exist_ok=True, verbose=False)
    box, grid = m.box, np.asarray(m.box.px)
    i = int(np.argmin(np.abs(grid - RUNTIME_CONF)))
    out = {}
    for row, class_id in enumerate(box.ap_class_index):
        cls = model.names[int(class_id)]
        if cls not in SCORED:
            continue
        p, r, ap50, ap = box.class_result(row)
        recall_rt = float(box.r_curve[row][i])
        out[cls] = {"precision": round(float(p), 4), "recall": round(float(r), 4), "map50": round(float(ap50), 4),
                    "map50_95": round(float(ap), 4),
                    "at_runtime_conf": {"conf": RUNTIME_CONF, "precision": round(float(box.p_curve[row][i]), 4),
                                        "recall": round(recall_rt, 4),
                                        "recall_ci95": wilson(recall_rt * instances[cls], instances[cls])}}
    return out


def main() -> None:
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable.")
    frozen = {k: hashlib.sha256(w.read_bytes()).hexdigest() for k, (w, _) in MODELS.items()}
    dataset = build_eval_set()
    print(dataset)
    results = {name: evaluate(w, s, name.split()[0], dataset["instances"]) for name, (w, s) in MODELS.items()}
    if {k: hashlib.sha256(w.read_bytes()).hexdigest() for k, (w, _) in MODELS.items()} != frozen:
        raise AssertionError("A model file changed during evaluation")
    OUT.mkdir(parents=True, exist_ok=True)
    report = {"label": "EXTERNAL TEST (independent of SH17; nothing trained, selected or tuned on it)",
              "dataset": "Safety Helmet and Reflective Jacket (Naik, 2023, Kaggle, Apache 2.0), test split",
              "class_mapping": {"Safety-Helmet": "helmet", "Reflective-Jacket": "safety-vest"},
              "weights_sha256": frozen, **dataset, "results": results}
    (OUT / "external_helmet_jacket.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = ["# External test: Safety Helmet and Reflective Jacket (Kaggle), test split", "",
             f"{report['label']}. {dataset['images_evaluated']} of {dataset['source_images']} test images "
             f"({dataset['near_duplicates_of_sh17_excluded']} near-duplicates of SH17 images excluded); "
             f"{dataset['instances']['helmet']} helmets, {dataset['instances']['safety-vest']} reflective jackets "
             "scored as SH17 helmet / safety-vest. Images are 640 x 640.", "",
             "| Model | Class | Precision | Recall | mAP@0.5 | mAP@0.5:0.95 | Recall at conf 0.25 (95% CI) |",
             "|---|---|---:|---:|---:|---:|---|"]
    for name, per_class in results.items():
        for cls in SCORED:
            x = per_class[cls]
            rt = x["at_runtime_conf"]
            lines.append(f"| {name} | {cls} | {x['precision']:.3f} | {x['recall']:.3f} | {x['map50']:.3f} | "
                         f"{x['map50_95']:.3f} | {rt['recall']:.3f} ({rt['recall_ci95'][0]:.3f}–{rt['recall_ci95'][1]:.3f}) |")
    lines += ["", "Caveats: reflective jacket is not identical to SH17's safety vest; the images were pre-resized to "
                  "640 x 640; the dataset has no person labels, so compliance (person + helmet + vest) cannot be "
                  "measured here.", ""]
    (OUT / "external_helmet_jacket.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
