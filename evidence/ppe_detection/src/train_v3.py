"""
DC-Guardian Evidence
PPE Detection v3: SH17 plus the Safety Helmet and Reflective Jacket training data

PPE-v2m (runtime) still sees few safety vests: SH17 has a few hundred, and
vest results swing with a handful of images. The Kaggle dataset of Naik (2023,
Apache 2.0) adds 14,138 helmets and 11,376 reflective jackets in its training
split. Protocol, fixed 2026-10-14 before any v3 training (operator decision):

1. Data.
   - SH17: the same PPE-v1 development split (6,479 train / 810 validation),
     training from the 1024-px resized copies built for PPE-v2.
   - Kaggle train (7,350) and valid (1,575). Images that are near-duplicates
     (difference hash, Hamming distance <= 6, as in the external test) of any
     SH17 image or of any Kaggle test image are dropped, so neither test set
     leaks into training or selection.
   - Kaggle labels map Safety-Helmet -> helmet (10), Reflective-Jacket ->
     safety-vest (16).
2. Pseudo-labels (option A). Kaggle images label only helmets and jackets;
   unlabelled people would be learned as background and harm the person
   detection the compliance policy depends on. The frozen PPE-v2m adds its
   own detections for every other class (person, head, hands, ...) at
   confidence >= 0.5, at 640 px (the images' native size). Helmet and vest
   labels on Kaggle images come only from the dataset.
3. One candidate, declared now: v3m1024 = YOLOv8m at 1024 px, initialised from
   the PPE-v2m weights (trained on SH17 train only), 30 epochs, patience 10,
   batch 8, seed 42.
4. Selection on validation only (evaluate_v3.py --stage validation). Criterion:
   mean of [mean helmet/vest mAP@0.5 on SH17 validation, mean helmet/vest
   mAP@0.5 on Kaggle validation (dataset labels only)]. v3 is accepted only if
   it beats PPE-v2m by at least 0.01 AND its SH17-validation person mAP@0.5 is
   not more than 0.02 below PPE-v2m's (guard against pseudo-label damage).
5. Test once (evaluate_v3.py --stage final), refusing a second run:
   - Kaggle test split, near-duplicates of SH17 excluded: now same-source
     held-out data, no longer an external test;
   - SH17 locked test: already used for PPE-v2 decisions, reported for
     comparison only.
   PPE-v1 and PPE-v2m are scored alongside with the same settings.
6. Frozen artifacts (PPE-v1, PPE-v2 official, PPE-v2m) are hash-checked before
   and after; nothing switches at runtime without the operator.

Run with the PPE environment:
    .venv-ppe\\Scripts\\python.exe evidence\\ppe_detection\\src\\train_v3.py --prepare-only
    .venv-ppe\\Scripts\\python.exe evidence\\ppe_detection\\src\\train_v3.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import torch
import yaml
from PIL import Image
from ultralytics import YOLO

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PPE_ROOT = PROJECT_ROOT / "evidence" / "ppe_detection"
MODELS = PPE_ROOT / "models"
SH17_IMAGES = PPE_ROOT / "data" / "raw" / "SH17" / "images"
SH17_MANIFESTS = PPE_ROOT / "data" / "processed" / "sh17_yolo"
SH17_RESIZED = PPE_ROOT / "data" / "processed" / "sh17_yolo_v2"
KAGGLE = PPE_ROOT / "data" / "raw" / "helmet_jacket"
V3_DATA = PPE_ROOT / "data" / "processed" / "ppe_v3"
RESULTS_DIR = PPE_ROOT / "results" / "training_v3"

FROZEN = ("ppe_yolov8_best.pt", "ppe_config.json", "ppe_training_metadata.json",
          "ppe_yolov8_v2_best.pt", "ppe_yolov8_v2m_best.pt", "ppe_config_v2m.json")
PSEUDO_LABELLER = MODELS / "ppe_yolov8_v2m_best.pt"
CLASS_MAP = {0: 10, 1: 16}          # Safety-Helmet -> helmet, Reflective-Jacket -> safety-vest
GROUND_TRUTH_CLASSES = {10, 16}     # never pseudo-labelled on Kaggle images
PSEUDO_CONF = 0.5
PSEUDO_IMGSZ = 640
HAMMING_MAX = 6
CANDIDATE = {"name": "v3m1024", "architecture": "yolov8m", "imgsz": 1024, "batch": 8,
             "init": "ppe_yolov8_v2m_best.pt"}
EPOCHS = 30
PATIENCE = 10
SEED = 42


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dhash(path: str) -> int:
    with Image.open(path) as image:
        image.draft("L", (64, 64))
        small = image.convert("L").resize((9, 8), Image.LANCZOS)
    px = np.asarray(small, dtype=np.int16)
    return int("".join("1" if b else "0" for b in (px[:, 1:] > px[:, :-1]).flatten()), 2)


def hashes(paths: list[Path]) -> np.ndarray:
    with ProcessPoolExecutor(max_workers=8) as pool:
        return np.array(list(pool.map(dhash, [str(p) for p in paths], chunksize=64)), dtype=np.uint64)


def popcount(values: np.ndarray) -> np.ndarray:
    return np.unpackbits(values.view(np.uint8).reshape(-1, 8), axis=1).sum(axis=1)


def near_duplicates(candidates: list[Path], reference: np.ndarray) -> set[str]:
    found = set()
    for path, h in zip(candidates, hashes(candidates)):
        if popcount(reference ^ np.uint64(h)).min() <= HAMMING_MAX:
            found.add(path.name)
    return found


def sh17_names(manifest: str) -> list[str]:
    text = (SH17_MANIFESTS / manifest).read_text(encoding="utf-8-sig")
    return [Path(line.strip()).name for line in text.splitlines() if line.strip()]


def write_kaggle_split(split: str, excluded: set[str], labeller: YOLO) -> tuple[list[str], dict]:
    """Copy-free: list the kept Kaggle images and write merged labels next to them in V3_DATA."""
    out_labels = V3_DATA / "kaggle" / split / "labels"
    out_images = V3_DATA / "kaggle" / split / "images"
    out_labels.mkdir(parents=True, exist_ok=True)
    out_images.mkdir(parents=True, exist_ok=True)
    images = sorted((KAGGLE / split / "images").iterdir())
    kept, counts = [], {"ground_truth": {"helmet": 0, "safety-vest": 0}, "pseudo": {}}
    for start in range(0, len(images), 64):
        batch = [p for p in images[start:start + 64] if p.name not in excluded]
        if not batch:
            continue
        predictions = labeller.predict([str(p) for p in batch], imgsz=PSEUDO_IMGSZ, conf=PSEUDO_CONF,
                                       device=0, verbose=False)
        for path, result in zip(batch, predictions):
            lines = []
            for line in (KAGGLE / split / "labels" / (path.stem + ".txt")).read_text(encoding="utf-8").splitlines():
                parts = line.split()
                if parts:
                    cls = CLASS_MAP[int(parts[0])]
                    counts["ground_truth"]["helmet" if cls == 10 else "safety-vest"] += 1
                    lines.append(" ".join([str(cls), *parts[1:]]))
            for cls, box in zip(result.boxes.cls.tolist(), result.boxes.xywhn.tolist()):
                if int(cls) in GROUND_TRUTH_CLASSES:
                    continue
                name = labeller.names[int(cls)]
                counts["pseudo"][name] = counts["pseudo"].get(name, 0) + 1
                lines.append(" ".join([str(int(cls)), *(f"{v:.6f}" for v in box)]))
            # Ultralytics finds labels by swapping /images/ for /labels/, so the image is hard-linked beside them.
            target = out_images / path.name
            if not target.exists():
                target.hardlink_to(path)
            (out_labels / (path.stem + ".txt")).write_text("\n".join(lines) + "\n", encoding="utf-8")
            kept.append(str(target.resolve()))
    return kept, counts


def prepare() -> dict:
    train, val, test = sh17_names("train_images.txt"), sh17_names("validation_images.txt"), sh17_names("test_files.txt")
    if (len(train), len(val), len(test)) != (6479, 810, 810):
        raise AssertionError("SH17 split sizes differ from PPE-v1")
    sh17_all = sorted(p for p in SH17_IMAGES.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"})
    kaggle_test = sorted((KAGGLE / "test" / "images").iterdir())
    reference = np.concatenate([hashes(sh17_all), hashes(kaggle_test)])
    excluded = {split: near_duplicates(sorted((KAGGLE / split / "images").iterdir()), reference)
                for split in ("train", "valid")}

    labeller = YOLO(str(PSEUDO_LABELLER))
    kaggle_train, train_counts = write_kaggle_split("train", excluded["train"], labeller)
    kaggle_valid, valid_counts = write_kaggle_split("valid", excluded["valid"], labeller)

    resized = lambda n: str((SH17_RESIZED / "images" / (Path(n).stem + ".jpg")).resolve())
    missing = [n for n in train + val if not Path(resized(n)).exists()]
    if missing:
        raise FileNotFoundError(f"{len(missing)} resized SH17 images missing (they are built by train_v2.py)")
    lists = {"train.txt": [resized(n) for n in train] + kaggle_train,
             "val.txt": [resized(n) for n in val] + kaggle_valid}
    for name, items in lists.items():
        (V3_DATA / name).write_text("\n".join(items) + "\n", encoding="utf-8")
    names = yaml.safe_load((SH17_MANIFESTS / "dataset.yaml").read_text(encoding="utf-8"))["names"]
    dataset = V3_DATA / "dataset.yaml"
    dataset.write_text(yaml.safe_dump({"train": str((V3_DATA / "train.txt").resolve()),
                                       "val": str((V3_DATA / "val.txt").resolve()),
                                       "nc": len(names), "names": names}, sort_keys=False), encoding="utf-8")
    test_names = {Path(n).name for n in test} | {p.name for p in kaggle_test}
    if any(Path(p).name in test_names for items in lists.values() for p in items):
        raise AssertionError("A test image reached the v3 training or validation lists")
    summary = {"sh17_train": len(train), "sh17_validation": len(val),
               "kaggle_train_kept": len(kaggle_train), "kaggle_valid_kept": len(kaggle_valid),
               "kaggle_train_near_duplicates_dropped": len(excluded["train"]),
               "kaggle_valid_near_duplicates_dropped": len(excluded["valid"]),
               "labels_train": train_counts, "labels_valid": valid_counts,
               "pseudo_labeller": PSEUDO_LABELLER.name, "pseudo_labeller_sha256": sha256(PSEUDO_LABELLER),
               "pseudo_conf": PSEUDO_CONF, "pseudo_imgsz": PSEUDO_IMGSZ, "hamming_max": HAMMING_MAX}
    (V3_DATA / "prepare_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--smoke-test", action="store_true", help="1 epoch on 5%% of the data, to time training")
    args = parser.parse_args()
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable; PPE training needs the project GPU.")
    frozen_before = {n: sha256(MODELS / n) for n in FROZEN}
    summary = prepare()
    print(json.dumps(summary, indent=2))
    if args.prepare_only:
        return
    name = f"{CANDIDATE['name']}_smoke" if args.smoke_test else CANDIDATE["name"]
    init = MODELS / CANDIDATE["init"]
    results = YOLO(str(init)).train(
        data=str(V3_DATA / "dataset.yaml"), epochs=1 if args.smoke_test else EPOCHS, imgsz=CANDIDATE["imgsz"],
        batch=CANDIDATE["batch"], fraction=0.05 if args.smoke_test else 1.0, patience=PATIENCE, device=0,
        seed=SEED, deterministic=True, project=str(RESULTS_DIR), name=name, exist_ok=True, workers=4,
        plots=not args.smoke_test, verbose=True)
    save_dir = Path(results.save_dir)
    if {n: sha256(MODELS / n) for n in FROZEN} != frozen_before:
        raise AssertionError("A frozen PPE artifact changed during v3 training")
    metadata = {"candidate": CANDIDATE["name"], "model_family": "YOLOv8", "architecture": CANDIDATE["architecture"],
                "initialisation": init.name, "initialisation_sha256": frozen_before[init.name],
                "datasets": "SH17 PPE-v1 development split + Safety Helmet and Reflective Jacket train/valid "
                            "(Naik 2023), near-duplicates of SH17 and Kaggle test removed, persons and other "
                            "classes pseudo-labelled by PPE-v2m",
                "prepare": summary, "locked_test_accessed": False, "kaggle_test_accessed": False,
                "epochs_requested": 1 if args.smoke_test else EPOCHS, "patience": PATIENCE,
                "image_size": CANDIDATE["imgsz"], "batch_size": CANDIDATE["batch"], "seed": SEED,
                "smoke_test": args.smoke_test, "gpu": torch.cuda.get_device_name(0), "pytorch": torch.__version__,
                "training_run": str(save_dir.relative_to(PROJECT_ROOT)),
                "best_checkpoint": str((save_dir / "weights" / "best.pt").relative_to(PROJECT_ROOT))}
    (save_dir / "candidate_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Candidate {name} trained: {save_dir}")
    print("Frozen PPE artifacts unchanged. Locked SH17 test and Kaggle test accessed: NO")


if __name__ == "__main__":
    main()
