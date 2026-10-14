"""
DC-Guardian Evidence
PPE-v3: selection on validation, then one final test (protocol in train_v3.py)

    --stage validation   PPE-v1, PPE-v2m and the v3m1024 candidate on
                         (a) SH17 validation, original images, all classes;
                         (b) Kaggle validation, dataset labels only (helmet,
                             vest), near-duplicates removed as for training.
                         Criterion: mean of the two sets' mean helmet/vest
                         mAP@0.5. Accept v3 only if it beats PPE-v2m by >= 0.01
                         and its SH17-validation person mAP@0.5 is no more than
                         0.02 below PPE-v2m's. An accepted model is copied to
                         models/ppe_yolov8_v3m_best.pt with its metadata.
    --stage final        Only after acceptance; refuses a second run. All three
                         models on the Kaggle test (same-source held-out data,
                         SH17 near-duplicates removed) and on the SH17 locked
                         test (already used for PPE-v2 decisions).

Same Ultralytics settings as the earlier PPE evaluations (batch 16, workers 0,
default confidence and IoU), each model at its own image size.

    .venv-ppe\\Scripts\\python.exe evidence\\ppe_detection\\src\\evaluate_v3.py --stage validation
    .venv-ppe\\Scripts\\python.exe evidence\\ppe_detection\\src\\evaluate_v3.py --stage final
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import torch
import yaml
from ultralytics import YOLO

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PPE = PROJECT_ROOT / "evidence" / "ppe_detection"
MODELS = PPE / "models"
V3_DATA = PPE / "data" / "processed" / "ppe_v3"
KAGGLE = PPE / "data" / "raw" / "helmet_jacket"
SH17_VALIDATION = PPE / "data" / "processed" / "sh17_yolo_v2" / "validation_original.yaml"
SH17_LOCKED = PPE / "results" / "final_test_v2" / "locked_test_dataset.yaml"
CANDIDATE_RUN = PPE / "results" / "training_v3" / "v3m1024"
SELECTION_DIR = PPE / "results" / "selection_v3"
FINAL_DIR = PPE / "results" / "final_test_v3"
V3_WEIGHTS = MODELS / "ppe_yolov8_v3m_best.pt"
REQUIRED = ("helmet", "safety-vest")
MARGIN = 0.01
PERSON_GUARD = 0.02


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def models(stage: str) -> dict[str, tuple[Path, int]]:
    v3 = CANDIDATE_RUN / "weights" / "best.pt" if stage == "validation" else V3_WEIGHTS
    return {"PPE-v1": (MODELS / "ppe_yolov8_best.pt", 640),
            "PPE-v2m (runtime)": (MODELS / "ppe_yolov8_v2m_best.pt", 1024),
            "PPE-v3m (v3m1024)": (v3, 1024)}


def ground_truth_yaml(split: str) -> Path:
    """Kaggle split with the dataset's own helmet/vest labels only (no pseudo-labels), kept images only."""
    names = yaml.safe_load((V3_DATA / "dataset.yaml").read_text(encoding="utf-8"))["names"]
    root = V3_DATA / f"kaggle_{split}_gt"
    if root.exists():
        shutil.rmtree(root)
    (root / "images").mkdir(parents=True)
    (root / "labels").mkdir(parents=True)
    if split == "valid":
        kept = [Path(p) for p in (V3_DATA / "val.txt").read_text(encoding="utf-8").split() if "kaggle" in p]
    else:  # the external-test build: Kaggle test minus SH17 near-duplicates
        kept = [Path(p) for p in (PPE / "data" / "processed" / "helmet_jacket_external" / "test_images.txt")
                .read_text(encoding="utf-8").split()]
    images = []
    for path in kept:
        (root / "images" / path.name).hardlink_to(KAGGLE / split / "images" / path.name)
        lines = [" ".join([str({0: 10, 1: 16}[int(p[0])]), *p[1:]])
                 for p in (line.split() for line in (KAGGLE / split / "labels" / (path.stem + ".txt"))
                           .read_text(encoding="utf-8").splitlines()) if p]
        (root / "labels" / (path.stem + ".txt")).write_text("\n".join(lines) + "\n", encoding="utf-8")
        images.append(str((root / "images" / path.name).resolve()))
    (root / "images.txt").write_text("\n".join(images) + "\n", encoding="utf-8")
    data = root / "dataset.yaml"
    data.write_text(yaml.safe_dump({"train": str((root / "images.txt").resolve()), "val": str((root / "images.txt").resolve()),
                                    "test": str((root / "images.txt").resolve()), "nc": len(names), "names": names},
                                   sort_keys=False), encoding="utf-8")
    return data


def score(weights: Path, imgsz: int, data: Path, split: str, out: Path, name: str, classes) -> dict:
    model = YOLO(str(weights))
    m = model.val(data=str(data), split=split, imgsz=imgsz, batch=16, device=0, workers=0, plots=False,
                  project=str(out / "ultralytics"), name=name, exist_ok=True, verbose=False)
    result = {"overall": {"precision": round(float(m.box.mp), 4), "recall": round(float(m.box.mr), 4),
                          "map50": round(float(m.box.map50), 4), "map50_95": round(float(m.box.map), 4)}}
    for row, class_id in enumerate(m.box.ap_class_index):
        cls = model.names[int(class_id)]
        if classes is None or cls in classes:
            p, r, ap50, ap = m.box.class_result(row)
            result[cls] = {"precision": round(float(p), 4), "recall": round(float(r), 4),
                           "map50": round(float(ap50), 4), "map50_95": round(float(ap), 4)}
    return result


def required_mean(result: dict) -> float:
    return sum(result[c]["map50"] for c in REQUIRED) / len(REQUIRED)


def validation() -> None:
    if not (CANDIDATE_RUN / "weights" / "best.pt").exists():
        raise SystemExit("v3m1024 has not been trained.")
    kaggle_valid = ground_truth_yaml("valid")
    rows = {}
    for name, (weights, imgsz) in models("validation").items():
        tag = name.split()[0]
        sh17 = score(weights, imgsz, SH17_VALIDATION, "val", SELECTION_DIR, f"{tag}_sh17", None)
        kaggle = score(weights, imgsz, kaggle_valid, "val", SELECTION_DIR, f"{tag}_kaggle", REQUIRED)
        rows[name] = {"sha256": sha256(weights), "image_size": imgsz, "sh17_validation": sh17,
                      "kaggle_validation": kaggle,
                      "criterion": round((required_mean(sh17) + required_mean(kaggle)) / 2, 4)}
    v2m, v3 = rows["PPE-v2m (runtime)"], rows["PPE-v3m (v3m1024)"]
    gain = round(v3["criterion"] - v2m["criterion"], 4)
    person_drop = round(v2m["sh17_validation"]["person"]["map50"] - v3["sh17_validation"]["person"]["map50"], 4)
    accepted = gain >= MARGIN and person_drop <= PERSON_GUARD
    report = {"rule": f"accept if criterion gain over PPE-v2m >= {MARGIN} and SH17 person mAP@0.5 drop <= {PERSON_GUARD}",
              "locked_test_accessed": False, "kaggle_test_accessed": False, "results": rows,
              "criterion_gain_over_v2m": gain, "person_map50_drop_vs_v2m": person_drop, "accepted": accepted}
    if accepted:
        shutil.copy2(CANDIDATE_RUN / "weights" / "best.pt", V3_WEIGHTS)
        meta = json.loads((CANDIDATE_RUN / "candidate_metadata.json").read_text(encoding="utf-8"))
        meta.update({"selected_by": "evaluate_v3.py --stage validation", "weights_file": V3_WEIGHTS.name,
                     "weights_sha256": sha256(V3_WEIGHTS), "validation": v3})
        (MODELS / "ppe_v3m_metadata.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        report["selected_sha256"] = sha256(V3_WEIGHTS)
    SELECTION_DIR.mkdir(parents=True, exist_ok=True)
    (SELECTION_DIR / "selection_v3.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = ["# PPE-v3 selection (validation only)", "",
             f"Rule: {report['rule']}. Criterion = mean of [helmet/vest mAP@0.5 on SH17 validation (810 original "
             "images), helmet/vest mAP@0.5 on Kaggle validation (dataset labels, near-duplicates removed)].", "",
             "| Model | Criterion | SH17 helmet / vest / person mAP@0.5 | Kaggle helmet / vest mAP@0.5 | SH17 all-class mAP@0.5 |",
             "|---|---:|---|---|---:|"]
    for name, r in rows.items():
        s, k = r["sh17_validation"], r["kaggle_validation"]
        lines.append(f"| {name} | {r['criterion']:.4f} | {s['helmet']['map50']:.3f} / {s['safety-vest']['map50']:.3f} / "
                     f"{s['person']['map50']:.3f} | {k['helmet']['map50']:.3f} / {k['safety-vest']['map50']:.3f} | "
                     f"{s['overall']['map50']:.3f} |")
    lines += ["", f"Gain over PPE-v2m: {gain:+.4f}; person mAP@0.5 drop: {person_drop:+.4f}. "
              f"**{'Accepted' if accepted else 'Not accepted'}.**", ""]
    (SELECTION_DIR / "selection_v3.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


def final() -> None:
    summary = FINAL_DIR / "final_test_v3.json"
    if summary.exists():
        raise SystemExit("final_test_v3.json exists: the PPE-v3 final test has already been run.")
    selection = json.loads((SELECTION_DIR / "selection_v3.json").read_text(encoding="utf-8"))
    if not selection["accepted"]:
        raise SystemExit("PPE-v3 was not accepted on validation; nothing to test.")
    if sha256(V3_WEIGHTS) != selection["selected_sha256"]:
        raise AssertionError("PPE-v3 weights changed after selection.")
    kaggle_test = ground_truth_yaml("test")
    rows = {}
    for name, (weights, imgsz) in models("final").items():
        tag = name.split()[0]
        rows[name] = {"sha256": sha256(weights), "image_size": imgsz,
                      "kaggle_test": score(weights, imgsz, kaggle_test, "test", FINAL_DIR, f"{tag}_kaggle", REQUIRED),
                      "sh17_locked_test": score(weights, imgsz, SH17_LOCKED, "test", FINAL_DIR, f"{tag}_sh17",
                                                ("helmet", "safety-vest", "person"))}
    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    report = {"label": "PPE-v3 final test, run once after validation acceptance",
              "kaggle_test": "same-source held-out (Kaggle train/valid were used in v3 training); SH17 near-duplicates removed",
              "sh17_locked_test": "already used for PPE-v2 decisions; comparison only", "results": rows}
    summary.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = ["# PPE-v1 vs PPE-v2m vs PPE-v3m: final test (run once)", "",
             "Kaggle test: same-source held-out data (Kaggle train and validation were used to train v3), SH17 "
             "near-duplicates removed. SH17 locked test: already used for PPE-v2 decisions, comparison only.", "",
             "| Model | Kaggle helmet P / R / mAP@0.5 | Kaggle vest P / R / mAP@0.5 | SH17 helmet R / mAP@0.5 | "
             "SH17 vest R / mAP@0.5 | SH17 person mAP@0.5 | SH17 all mAP@0.5 |", "|---|---|---|---|---|---:|---:|"]
    for name, r in rows.items():
        k, s = r["kaggle_test"], r["sh17_locked_test"]
        lines.append(f"| {name} | {k['helmet']['precision']:.3f} / {k['helmet']['recall']:.3f} / {k['helmet']['map50']:.3f} | "
                     f"{k['safety-vest']['precision']:.3f} / {k['safety-vest']['recall']:.3f} / {k['safety-vest']['map50']:.3f} | "
                     f"{s['helmet']['recall']:.3f} / {s['helmet']['map50']:.3f} | "
                     f"{s['safety-vest']['recall']:.3f} / {s['safety-vest']['map50']:.3f} | "
                     f"{s['person']['map50']:.3f} | {s['overall']['map50']:.3f} |")
    (FINAL_DIR / "final_test_v3.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("validation", "final"), required=True)
    args = parser.parse_args()
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable.")
    validation() if args.stage == "validation" else final()


if __name__ == "__main__":
    main()
