"""
DC-Guardian Phase 1
PPE Detection Training

Trains YOLOv8n on the frozen SH17 development boundary.

The locked final-test population is never accessed here.
"""

from pathlib import Path
import argparse
import json
import shutil

import torch
from ultralytics import YOLO


PROJECT_ROOT = Path(__file__).resolve().parents[3]

PPE_ROOT = PROJECT_ROOT / "evidence" / "ppe_detection"

DATASET_YAML = (
    PPE_ROOT
    / "data"
    / "processed"
    / "sh17_yolo"
    / "dataset.yaml"
)

LOCKED_TEST_MANIFEST = (
    PPE_ROOT
    / "data"
    / "processed"
    / "sh17_yolo"
    / "test_files.txt"
)

MODEL_DIR = PPE_ROOT / "models"
RESULTS_DIR = PPE_ROOT / "results" / "training"


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--epochs",
        type=int,
        default=50,
    )

    parser.add_argument(
        "--batch",
        type=int,
        default=16,
    )

    parser.add_argument(
        "--imgsz",
        type=int,
        default=640,
    )

    parser.add_argument(
        "--smoke-test",
        action="store_true",
    )

    args = parser.parse_args()


    print("\n============================================")
    print("DC-GUARDIAN PPE YOLO TRAINING")
    print("============================================")


    if not DATASET_YAML.exists():
        raise FileNotFoundError(
            f"Dataset YAML not found: {DATASET_YAML}"
        )


    # Ensure the locked test exists, but never read its contents.
    if not LOCKED_TEST_MANIFEST.exists():
        raise FileNotFoundError(
            "Locked PPE test manifest missing."
        )


    yaml_text = DATASET_YAML.read_text(
        encoding="utf-8"
    )


    if "test_files.txt" in yaml_text:
        raise AssertionError(
            "Locked test population leaked into dataset.yaml."
        )


    if not torch.cuda.is_available():
        raise RuntimeError(
            "CUDA is unavailable. PPE training is configured "
            "for the project NVIDIA GPU."
        )


    gpu_name = torch.cuda.get_device_name(0)


    print("PASS: Frozen development dataset found.")
    print("PASS: Locked final test excluded.")
    print("PyTorch:", torch.__version__)
    print("CUDA:", torch.version.cuda)
    print("GPU:", gpu_name)
    print("Epochs:", args.epochs)
    print("Batch:", args.batch)
    print("Image size:", args.imgsz)


    run_name = (
        "ppe_yolov8n_smoke"
        if args.smoke_test
        else "ppe_yolov8n_full"
    )


    MODEL_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


    # Pretrained COCO YOLOv8n starting point.
    model = YOLO(
        "yolov8n.pt"
    )


    results = model.train(
        data=str(DATASET_YAML),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=0,
        seed=42,
        deterministic=True,
        pretrained=True,
        project=str(RESULTS_DIR),
        name=run_name,
        exist_ok=True,
        workers=4,
        plots=True,
        verbose=True,
    )


    save_dir = Path(
        results.save_dir
    )


    best_weights = (
        save_dir
        / "weights"
        / "best.pt"
    )


    last_weights = (
        save_dir
        / "weights"
        / "last.pt"
    )


    if not best_weights.exists():
        raise FileNotFoundError(
            f"YOLO best checkpoint not found: {best_weights}"
        )


    if args.smoke_test:

        target_weights = (
            MODEL_DIR
            / "ppe_yolov8n_smoke.pt"
        )

    else:

        target_weights = (
            MODEL_DIR
            / "ppe_yolov8_best.pt"
        )


    shutil.copy2(
        best_weights,
        target_weights,
    )


    metadata = {
        "model_family": "YOLOv8",
        "architecture": "YOLOv8n",
        "pretrained_initialization": "yolov8n.pt",
        "dataset": "SH17",
        "class_count": 17,
        "train_images": 6479,
        "validation_images": 810,
        "locked_test_images": 810,
        "locked_test_accessed": False,
        "epochs": args.epochs,
        "image_size": args.imgsz,
        "batch_size": args.batch,
        "seed": 42,
        "device": "cuda:0",
        "gpu": gpu_name,
        "pytorch": torch.__version__,
        "cuda": torch.version.cuda,
        "smoke_test": args.smoke_test,
        "training_run": str(save_dir),
        "best_checkpoint": str(target_weights),
        "last_training_checkpoint": (
            str(last_weights)
            if last_weights.exists()
            else None
        ),
    }


    metadata_name = (
        "ppe_smoke_metadata.json"
        if args.smoke_test
        else "ppe_training_metadata.json"
    )


    metadata_path = (
        MODEL_DIR
        / metadata_name
    )


    metadata_path.write_text(
        json.dumps(
            metadata,
            indent=2,
        ),
        encoding="utf-8",
    )


    print("\n============================================")
    print("PPE TRAINING SUMMARY")
    print("============================================")

    print("Run:", save_dir)
    print("Best checkpoint:", target_weights)
    print("Metadata:", metadata_path)
    print("Locked final test accessed: NO")

    print("\n============================================")
    print("DC-GUARDIAN PPE TRAINING PASSED")
    print("============================================")


if __name__ == "__main__":
    main()
