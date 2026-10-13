"""
DC-Guardian Evidence
PPE Detection v2 — candidate training

Trains one PPE-v2 candidate on the frozen SH17 development boundary (the
same 6,479 training and 810 validation images as PPE-v1). PPE-v1 stays
frozen: this script never writes models/ppe_yolov8_best.pt, ppe_config.json
or ppe_training_metadata.json, and the locked final-test images are never
read (only checked to be disjoint from training and validation).

Candidates (declared 2026-10-13, before any v2 training):
    v2n1024   YOLOv8n at 1024 px (effect of resolution alone)
    v2s1024   YOLOv8s at 1024 px
    v2m1024   YOLOv8m at 1024 px
Selection happens afterwards on validation only (select_v2.py).

Run with the PPE environment:
    .venv-ppe\\Scripts\\python.exe evidence\\ppe_detection\\src\\train_v2.py --candidate v2s1024
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import torch
import yaml
from ultralytics import YOLO

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PPE_ROOT = PROJECT_ROOT / "evidence" / "ppe_detection"
PROCESSED = PPE_ROOT / "data" / "processed" / "sh17_yolo"
V2_DATA = PPE_ROOT / "data" / "processed" / "sh17_yolo_v2"
IMAGE_DIR = PPE_ROOT / "data" / "raw" / "SH17" / "images"
PRETRAINED = PPE_ROOT / "models" / "pretrained"
RESULTS_DIR = PPE_ROOT / "results" / "training_v2"
FROZEN_V1 = ("ppe_yolov8_best.pt", "ppe_config.json", "ppe_training_metadata.json")

CANDIDATES = {
    "v2n1024": {"architecture": "yolov8n", "imgsz": 1024, "batch": 16},
    "v2s1024": {"architecture": "yolov8s", "imgsz": 1024, "batch": 8},
    "v2m1024": {"architecture": "yolov8m", "imgsz": 1024, "batch": 8},  # smoke test: 5.8 GB at batch 6
}
EPOCHS = 100
PATIENCE = 30
SEED = 42


def _names(manifest: str) -> list[str]:
    text = (PROCESSED / manifest).read_text(encoding="utf-8-sig")
    return [Path(line.strip()).name for line in text.splitlines() if line.strip()]


def development_dataset() -> Path:
    """Dataset YAML with the v1 train/validation split, re-rooted at the current image folder.

    The v1 manifests hold absolute paths from an earlier folder layout; only the
    file names are reused, so the split is identical.
    """
    train, val, test = _names("train_images.txt"), _names("validation_images.txt"), _names("test_files.txt")
    if (len(train), len(val), len(test)) != (6479, 810, 810):
        raise AssertionError("SH17 split sizes differ from PPE-v1")
    if set(train) & set(val) or (set(train) | set(val)) & set(test):
        raise AssertionError("Development and locked-test populations overlap")
    V2_DATA.mkdir(parents=True, exist_ok=True)
    for name, items in (("train_images.txt", train), ("validation_images.txt", val)):
        missing = [n for n in items if not (IMAGE_DIR / n).exists()]
        if missing:
            raise FileNotFoundError(f"{len(missing)} development images missing, e.g. {missing[0]}")
        (V2_DATA / name).write_text("\n".join(str((IMAGE_DIR / n).resolve()) for n in items) + "\n",
                                    encoding="utf-8")
    v1_yaml = yaml.safe_load((PROCESSED / "dataset.yaml").read_text(encoding="utf-8"))
    config = {"train": str((V2_DATA / "train_images.txt").resolve()),
              "val": str((V2_DATA / "validation_images.txt").resolve()),
              "nc": v1_yaml["nc"], "names": v1_yaml["names"]}
    path = V2_DATA / "dataset.yaml"
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    if "test" in path.read_text(encoding="utf-8"):
        raise AssertionError("Locked test population leaked into the v2 dataset YAML")
    return path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", choices=sorted(CANDIDATES), required=True)
    parser.add_argument("--epochs", type=int, default=EPOCHS)
    parser.add_argument("--smoke-test", action="store_true", help="1 epoch on 5%% of the data, to time a candidate")
    args = parser.parse_args()
    spec = CANDIDATES[args.candidate]
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable; PPE training needs the project GPU.")

    frozen_before = {n: sha256(PPE_ROOT / "models" / n) for n in FROZEN_V1}
    dataset = development_dataset()
    weights = PRETRAINED / f"{spec['architecture']}.pt"
    name = f"{args.candidate}_smoke" if args.smoke_test else args.candidate

    model = YOLO(str(weights))
    results = model.train(
        data=str(dataset), epochs=1 if args.smoke_test else args.epochs, imgsz=spec["imgsz"],
        batch=spec["batch"], fraction=0.05 if args.smoke_test else 1.0, patience=PATIENCE,
        device=0, seed=SEED, deterministic=True, pretrained=True, project=str(RESULTS_DIR),
        name=name, exist_ok=True, workers=4, plots=not args.smoke_test, verbose=True)
    save_dir = Path(results.save_dir)

    if {n: sha256(PPE_ROOT / "models" / n) for n in FROZEN_V1} != frozen_before:
        raise AssertionError("A frozen PPE-v1 artifact changed during v2 training")
    metadata = {
        "candidate": args.candidate, "model_family": "YOLOv8", "architecture": spec["architecture"],
        "pretrained_initialization": weights.name, "pretrained_sha256": sha256(weights),
        "dataset": "SH17", "split": "PPE-v1 development split (6,479 train / 810 validation)",
        "locked_test_accessed": False, "epochs_requested": 1 if args.smoke_test else args.epochs,
        "patience": PATIENCE, "image_size": spec["imgsz"], "batch_size": spec["batch"], "seed": SEED,
        "smoke_test": args.smoke_test, "gpu": torch.cuda.get_device_name(0), "pytorch": torch.__version__,
        "cuda": torch.version.cuda, "training_run": str(save_dir.relative_to(PROJECT_ROOT)),
        "best_checkpoint": str((save_dir / "weights" / "best.pt").relative_to(PROJECT_ROOT)),
    }
    (save_dir / "candidate_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Candidate {name} trained: {save_dir}")
    print("Frozen PPE-v1 artifacts unchanged. Locked final test accessed: NO")


if __name__ == "__main__":
    main()
