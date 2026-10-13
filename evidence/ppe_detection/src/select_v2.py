"""
DC-Guardian Evidence
PPE Detection v2 — candidate selection on validation only

Rule (declared 2026-10-13, committed before any v2 candidate was trained):
1. Every trained candidate and the frozen PPE-v1 model are scored on the same
   810 validation images, each at its own training image size.
2. Criterion: mean mAP@0.5 of the two classes the compliance policy requires
   (helmet, safety-vest). Overall mAP@0.5 and recall are reported, not used.
3. A candidate within 0.01 of the best score loses to a smaller (faster) one.
4. The winner is copied to models/ppe_yolov8_v2_best.pt with its metadata.
   Only then is the locked test run, once (evaluate_final_test_v2.py).
   If no candidate beats PPE-v1 on the criterion, nothing is selected.

The locked final-test images are never read here.

    .venv-ppe\\Scripts\\python.exe evidence\\ppe_detection\\src\\select_v2.py
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import torch
from ultralytics import YOLO

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PPE_ROOT = PROJECT_ROOT / "evidence" / "ppe_detection"
MODELS = PPE_ROOT / "models"
TRAINING = PPE_ROOT / "results" / "training_v2"
DATASET = PPE_ROOT / "data" / "processed" / "sh17_yolo_v2" / "validation_original.yaml"  # original images, as for PPE-v1
OUT = PPE_ROOT / "results" / "selection_v2"
REQUIRED = ("helmet", "safety-vest")
SIZE_ORDER = ("yolov8n", "yolov8s", "yolov8m")  # smaller first
TIE_MARGIN = 0.01


def score(weights: Path, imgsz: int, name: str) -> dict:
    model = YOLO(str(weights))
    metrics = model.val(data=str(DATASET), split="val", imgsz=imgsz, batch=8, device=0, workers=0,
                        plots=False, project=str(OUT / "ultralytics"), name=name, exist_ok=True, verbose=False)
    ids = {n: i for i, n in model.names.items()}
    per_class = {}
    for cls in REQUIRED:
        p, r, ap50, ap = metrics.box.class_result(list(metrics.box.ap_class_index).index(ids[cls]))
        per_class[cls] = {"precision": round(float(p), 4), "recall": round(float(r), 4),
                          "map50": round(float(ap50), 4), "map50_95": round(float(ap), 4)}
    return {"image_size": imgsz, "criterion_required_map50": round(sum(c["map50"] for c in per_class.values()) / 2, 4),
            "overall": {"precision": round(float(metrics.box.mp), 4), "recall": round(float(metrics.box.mr), 4),
                        "map50": round(float(metrics.box.map50), 4), "map50_95": round(float(metrics.box.map), 4)},
            "required_classes": per_class,
            "inference_ms_per_image": round(float(metrics.speed["inference"]), 2)}


def main() -> None:
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable.")
    rows = {"PPE-v1 (frozen)": {"architecture": "yolov8n",
                                **score(MODELS / "ppe_yolov8_best.pt", 640, "v1")}}
    metas = {}
    for meta_path in sorted(TRAINING.glob("v2*1024/candidate_metadata.json")):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if meta["smoke_test"]:
            continue
        best = PROJECT_ROOT / meta["best_checkpoint"]
        metas[meta["candidate"]] = meta
        rows[meta["candidate"]] = {"architecture": meta["architecture"],
                                   **score(best, meta["image_size"], meta["candidate"])}
        print(meta["candidate"], rows[meta["candidate"]]["criterion_required_map50"])

    v1_score = rows["PPE-v1 (frozen)"]["criterion_required_map50"]
    candidates = {k: v for k, v in rows.items() if k in metas}
    top = max((v["criterion_required_map50"] for v in candidates.values()), default=None)
    eligible = [k for k, v in candidates.items() if top is not None and v["criterion_required_map50"] >= top - TIE_MARGIN]
    selected = min(eligible, key=lambda k: SIZE_ORDER.index(candidates[k]["architecture"])) if eligible else None
    if selected and candidates[selected]["criterion_required_map50"] <= v1_score:
        selected = None

    OUT.mkdir(parents=True, exist_ok=True)
    report = {"rule": __doc__.split("Rule")[1].split("The locked")[0].strip(), "validation_images": 810,
              "results": rows, "selected": selected, "locked_test_accessed": False}
    if selected:
        meta = metas[selected]
        target = MODELS / "ppe_yolov8_v2_best.pt"
        shutil.copy2(PROJECT_ROOT / meta["best_checkpoint"], target)
        report["selected_weights"] = target.name
        report["selected_sha256"] = hashlib.sha256(target.read_bytes()).hexdigest()
        (MODELS / "ppe_v2_training_metadata.json").write_text(
            json.dumps({**meta, "selected_by": "select_v2.py", "validation": rows[selected],
                        "weights": target.name, "weights_sha256": report["selected_sha256"]}, indent=2) + "\n",
            encoding="utf-8")
    (OUT / "selection_v2.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    lines = ["# PPE-v2 candidate selection (validation, 810 images)", "",
             "Criterion: mean mAP@0.5 of helmet and safety-vest; within 0.01 of the best, the smaller model wins; "
             "must beat PPE-v1. The locked test was not used.", "",
             "| Model | Size | Criterion | Helmet mAP@0.5 / recall | Vest mAP@0.5 / recall | Overall mAP@0.5 | Overall recall | ms/image |",
             "|---|---:|---:|---|---|---:|---:|---:|"]
    for name, r in rows.items():
        h, v = r["required_classes"]["helmet"], r["required_classes"]["safety-vest"]
        mark = " **(selected)**" if name == selected else ""
        lines.append(f"| {name} ({r['architecture']}){mark} | {r['image_size']} | {r['criterion_required_map50']:.4f} | "
                     f"{h['map50']:.3f} / {h['recall']:.3f} | {v['map50']:.3f} / {v['recall']:.3f} | "
                     f"{r['overall']['map50']:.4f} | {r['overall']['recall']:.4f} | {r['inference_ms_per_image']} |")
    lines += ["", f"Selected: **{selected or 'none (no candidate beats PPE-v1)'}**.", ""]
    (OUT / "selection_v2.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
