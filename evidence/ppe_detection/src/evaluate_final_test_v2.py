"""
DC-Guardian Evidence
PPE Detection v2 — locked final evaluation

Runs the PPE-v2 model chosen by select_v2.py (validation only) exactly once
against the same locked 810-image SH17 final-test population as PPE-v1, with
the same evaluation settings as evaluate_final_test.py. No training,
selection or threshold tuning happens here. Refuses to run twice: an existing
result is never overwritten.

PPE-v1's result (results/final_test/ppe_final_test.json) is read for the
side-by-side report, never rewritten.

    .venv-ppe\\Scripts\\python.exe evidence\\ppe_detection\\src\\evaluate_final_test_v2.py
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import torch
import yaml
from ultralytics import YOLO

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PPE_ROOT = PROJECT_ROOT / "evidence" / "ppe_detection"
MODELS = PPE_ROOT / "models"
RAW_ROOT = PPE_ROOT / "data" / "raw" / "SH17"
TEST_MANIFEST = PPE_ROOT / "data" / "processed" / "sh17_yolo" / "test_files.txt"
SELECTION = PPE_ROOT / "results" / "selection_v2" / "selection_v2.json"
V1_RESULT = PPE_ROOT / "results" / "final_test" / "ppe_final_test.json"
OUT = PPE_ROOT / "results" / "final_test_v2"
SUMMARY = OUT / "ppe_final_test_v2.json"


def main() -> None:
    if SUMMARY.exists():
        raise SystemExit(f"{SUMMARY.name} exists: the locked test has already been run for PPE-v2.")
    selection = json.loads(SELECTION.read_text(encoding="utf-8"))
    if not selection.get("selected") or selection.get("locked_test_accessed") is not False:
        raise SystemExit("No PPE-v2 model was selected on validation; nothing to evaluate.")
    weights = MODELS / selection["selected_weights"]
    if hashlib.sha256(weights.read_bytes()).hexdigest() != selection["selected_sha256"]:
        raise AssertionError("Selected weights changed after selection.")
    meta = json.loads((MODELS / "ppe_v2_training_metadata.json").read_text(encoding="utf-8"))
    v1 = json.loads(V1_RESULT.read_text(encoding="utf-8"))
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable.")

    names = [line.strip() for line in TEST_MANIFEST.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(names) != 810:
        raise AssertionError(f"Locked test population mismatch: {len(names)}")
    paths = [(RAW_ROOT / "images" / n).resolve() for n in names]
    missing = [p for p in paths if not p.exists()]
    if missing:
        raise FileNotFoundError(f"Locked test image missing: {missing[0]}")
    OUT.mkdir(parents=True, exist_ok=True)
    image_list = OUT / "locked_test_images.txt"
    image_list.write_text("\n".join(str(p) for p in paths) + "\n", encoding="utf-8")
    model = YOLO(str(weights))
    test_yaml = OUT / "locked_test_dataset.yaml"
    test_yaml.write_text(yaml.safe_dump({"path": str(RAW_ROOT.resolve()), "train": str(image_list),
                                         "val": str(image_list), "test": str(image_list),
                                         "nc": len(model.names), "names": [model.names[i] for i in range(len(model.names))]},
                                        sort_keys=False), encoding="utf-8")

    start = time.perf_counter()
    # Same settings as the PPE-v1 locked evaluation, at the selected model's training size.
    metrics = model.val(data=str(test_yaml), split="test", imgsz=meta["image_size"], batch=16, device=0, workers=0,
                        plots=True, project=str(OUT), name="ultralytics_eval", exist_ok=True, verbose=True)
    elapsed = time.perf_counter() - start

    per_class = {}
    for position, class_id in enumerate(metrics.box.ap_class_index):
        p, r, ap50, ap = metrics.box.class_result(position)
        per_class[model.names[int(class_id)]] = {"class_id": int(class_id), "precision": float(p), "recall": float(r),
                                                 "map50": float(ap50), "map50_95": float(ap)}
    result = {"evaluation": "LOCKED_FINAL_TEST", "configuration_version": "PPE-v2", "candidate": meta["candidate"],
              "architecture": meta["architecture"], "weights": weights.name, "weights_sha256": selection["selected_sha256"],
              "image_size": meta["image_size"], "final_test_images": len(paths), "selected_on": "validation only",
              "training_performed": False, "model_selection_performed": False, "threshold_selection_performed": False,
              "overall": {"precision": float(metrics.box.mp), "recall": float(metrics.box.mr),
                          "map50": float(metrics.box.map50), "map50_95": float(metrics.box.map)},
              "per_class": per_class, "speed_ms_per_image": metrics.speed, "elapsed_seconds": round(elapsed, 1)}
    SUMMARY.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    def line(label, key):
        a, b = v1[key] if key == "overall" else v1["per_class"][label], result[key] if key == "overall" else per_class[label]
        return (f"| {label} | {a['precision']:.3f} → {b['precision']:.3f} | {a['recall']:.3f} → {b['recall']:.3f} | "
                f"{a['map50']:.3f} → {b['map50']:.3f} | {a['map50_95']:.3f} → {b['map50_95']:.3f} |")

    lines = ["# PPE-v1 vs PPE-v2 on the locked final test (810 images)", "",
             f"PPE-v2 = {meta['candidate']} ({meta['architecture']}, {meta['image_size']} px), selected on validation "
             "only and evaluated once. PPE-v1 figures are the frozen v1 result.", "",
             "| Classes | Precision | Recall | mAP@0.5 | mAP@0.5:0.95 |", "|---|---|---|---|---|",
             line("All classes", "overall"), line("helmet", "per_class"), line("safety-vest", "per_class"),
             line("person", "per_class"), ""]
    (OUT / "ppe_v1_vs_v2.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
