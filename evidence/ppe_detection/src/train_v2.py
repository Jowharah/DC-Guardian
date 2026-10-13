"""
DC-Guardian Evidence
PPE Detection v2 â€” candidate training

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
LABEL_DIR = PPE_ROOT / "data" / "raw" / "SH17" / "labels"
TRAIN_LONG_SIDE = 1024
PRETRAINED = PPE_ROOT / "models" / "pretrained"
RESULTS_DIR = PPE_ROOT / "results" / "training_v2"
FROZEN_V1 = ("ppe_yolov8_best.pt", "ppe_config.json", "ppe_training_metadata.json")

CANDIDATES = {
    "v2n1024": {"architecture": "yolov8n", "imgsz": 1024, "batch": 16},
    "v2s1024": {"architecture": "yolov8s", "imgsz": 1024, "batch": 8},
    "v2m1024": {"architecture": "yolov8m", "imgsz": 1024, "batch": 8},  # smoke test: 5.8 GB at batch 6
}
EPOCHS = 60    # revised 2026-10-13 after the first epoch's timing, before any candidate result
PATIENCE = 20
SEED = 42


def _names(manifest: str) -> list[str]:
    text = (PROCESSED / manifest).read_text(encoding="utf-8-sig")
    return [Path(line.strip()).name for line in text.splitlines() if line.strip()]


def _resize_one(job: tuple[str, str, str]) -> None:
    import cv2  # local import: worker processes
    source, image_out, label_out = map(Path, job)
    if image_out.exists() and label_out.exists():
        return
    image = cv2.imread(str(source))  # same decoder as Ultralytics, so orientation handling is identical
    h, w = image.shape[:2]
    scale = TRAIN_LONG_SIDE / max(h, w)
    if scale < 1:
        image = cv2.resize(image, (round(w * scale), round(h * scale)), interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(image_out), image, [cv2.IMWRITE_JPEG_QUALITY, 95])
    # YOLO labels are normalised to image size, so they stay valid after resizing.
    label_out.write_bytes((LABEL_DIR / (source.stem + ".txt")).read_bytes())


def development_dataset() -> tuple[Path, Path]:
    """Dataset YAMLs with the PPE-v1 train/validation split.

    The v1 manifests hold absolute paths from an earlier folder layout; only the
    file names are reused, so the split is identical. Training reads copies
    resized once to the 1024-px training size (decoding the 2-6k px originals
    every epoch made one YOLOv8s epoch take 7 minutes); selection and the final
    test read the original images, as PPE-v1 did. Returns (training YAML,
    original-validation YAML).
    """
    from concurrent.futures import ProcessPoolExecutor

    train, val, test = _names("train_images.txt"), _names("validation_images.txt"), _names("test_files.txt")
    if (len(train), len(val), len(test)) != (6479, 810, 810):
        raise AssertionError("SH17 split sizes differ from PPE-v1")
    if set(train) & set(val) or (set(train) | set(val)) & set(test):
        raise AssertionError("Development and locked-test populations overlap")
    images, labels = V2_DATA / "images", V2_DATA / "labels"
    images.mkdir(parents=True, exist_ok=True)
    labels.mkdir(parents=True, exist_ok=True)
    missing = [n for n in train + val if not (IMAGE_DIR / n).exists()]
    if missing:
        raise FileNotFoundError(f"{len(missing)} development images missing, e.g. {missing[0]}")
    jobs = [(str(IMAGE_DIR / n), str(images / (Path(n).stem + ".jpg")), str(labels / (Path(n).stem + ".txt")))
            for n in train + val]
    with ProcessPoolExecutor(max_workers=8) as pool:
        list(pool.map(_resize_one, jobs, chunksize=32))
    resized = {n: (images / (Path(n).stem + ".jpg")).resolve() for n in train + val}
    for name, items in (("train_images.txt", train), ("validation_images.txt", val)):
        (V2_DATA / name).write_text("\n".join(str(resized[n]) for n in items) + "\n", encoding="utf-8")
    (V2_DATA / "validation_original.txt").write_text(
        "\n".join(str((IMAGE_DIR / n).resolve()) for n in val) + "\n", encoding="utf-8")
    v1_yaml = yaml.safe_load((PROCESSED / "dataset.yaml").read_text(encoding="utf-8"))
    common = {"nc": v1_yaml["nc"], "names": v1_yaml["names"]}
    training = V2_DATA / "dataset.yaml"
    training.write_text(yaml.safe_dump({"train": str((V2_DATA / "train_images.txt").resolve()),
                                        "val": str((V2_DATA / "validation_images.txt").resolve()), **common},
                                       sort_keys=False), encoding="utf-8")
    original = V2_DATA / "validation_original.yaml"
    original.write_text(yaml.safe_dump({"train": str((V2_DATA / "validation_original.txt").resolve()),
                                        "val": str((V2_DATA / "validation_original.txt").resolve()), **common},
                                       sort_keys=False), encoding="utf-8")
    for path in (training, original):
        if "test_files" in path.read_text(encoding="utf-8"):
            raise AssertionError("Locked test population leaked into a v2 dataset YAML")
    return training, original


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
    dataset, _ = development_dataset()
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
