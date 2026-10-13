"""
DC-Guardian Evidence
PPE Detection v2 — POST-HOC analysis (after selection; not used to choose)

Operator request (2026-10-13), after the official PPE-v2 locked test showed
safety-vest recall falling from 0.449 (v1) to 0.245 (v2s1024):

1. Evaluate the two unselected candidates (v2n1024, v2m1024) on the same 810
   locked images with the same settings as the official evaluations. v1 and
   v2s1024 are re-scored the same way as a consistency check against their
   official results. This is POST-HOC: it happens after selection and can
   never change it. v2s1024 stays the official PPE-v2 result.
2. If every v2 candidate is still worse than v1 on safety vests on the locked
   test, describe a combined detector: v2s1024 for every class except
   safety-vest, v1 for safety-vest. The class assignment is the operator's,
   made AFTER seeing the locked test (validation favoured v2s1024 on vests), so
   it is test-informed. Only the per-class confidence thresholds are chosen on
   validation (maximum F1 per class). The combination's locked-test figures are
   therefore "consistent with", never an independent confirmation; a clean
   claim needs a fresh held-out set.

evaluate_final_test_v2.py and its run-once guard are not touched. Frozen
PPE-v1 artifacts are hash-checked before and after.

    .venv-ppe\\Scripts\\python.exe evidence\\ppe_detection\\src\\evaluate_posthoc_v2.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import torch
from ultralytics import YOLO

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PPE = PROJECT_ROOT / "evidence" / "ppe_detection"
MODELS = PPE / "models"
TRAINING = PPE / "results" / "training_v2"
VALIDATION_YAML = PPE / "data" / "processed" / "sh17_yolo_v2" / "validation_original.yaml"
TEST_YAML = PPE / "results" / "final_test_v2" / "locked_test_dataset.yaml"
OFFICIAL_V1 = PPE / "results" / "final_test" / "ppe_final_test.json"
OFFICIAL_V2 = PPE / "results" / "final_test_v2" / "ppe_final_test_v2.json"
OUT = PPE / "results" / "posthoc_v2"
FROZEN_V1 = ("ppe_yolov8_best.pt", "ppe_config.json", "ppe_training_metadata.json")
SHOWN = ("helmet", "safety-vest", "person")
RUNTIME_CONF = 0.25  # PPE-v1 runtime confidence threshold (ppe_config.json)
LABEL = "POST-HOC (evaluated after selection; not used to choose)"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def models() -> dict[str, dict]:
    found = {"PPE-v1": {"weights": MODELS / "ppe_yolov8_best.pt", "imgsz": 640, "role": "frozen baseline"}}
    for candidate in ("v2n1024", "v2s1024", "v2m1024"):
        meta = json.loads((TRAINING / candidate / "candidate_metadata.json").read_text(encoding="utf-8"))
        found[candidate] = {"weights": PROJECT_ROOT / meta["best_checkpoint"], "imgsz": meta["image_size"],
                            "role": "official PPE-v2 (selected)" if candidate == "v2s1024" else "unselected candidate"}
    return found


def evaluate(spec: dict, data: Path, split: str, name: str) -> dict:
    """Same settings as the official locked evaluations (batch 16, workers 0, default conf/IoU)."""
    model = YOLO(str(spec["weights"]))
    m = model.val(data=str(data), split=split, imgsz=spec["imgsz"], batch=16, device=0, workers=0, plots=False,
                  project=str(OUT / "ultralytics"), name=name, exist_ok=True, verbose=False)
    box = m.box
    per_class = {}
    for row, class_id in enumerate(box.ap_class_index):
        p, r, ap50, ap = box.class_result(row)
        per_class[model.names[int(class_id)]] = {
            "precision": float(p), "recall": float(r), "map50": float(ap50), "map50_95": float(ap),
            "curve": {"precision": box.p_curve[row].tolist(), "recall": box.r_curve[row].tolist(),
                      "f1": box.f1_curve[row].tolist()}}
    return {"overall": {"precision": float(box.mp), "recall": float(box.mr), "map50": float(box.map50),
                        "map50_95": float(box.map)},
            "per_class": per_class, "conf_grid": box.px.tolist()}


def at(result: dict, cls: str, conf: float) -> dict:
    grid = np.asarray(result["conf_grid"])
    i = int(np.argmin(np.abs(grid - conf)))
    c = result["per_class"][cls]["curve"]
    return {"conf": round(float(grid[i]), 3), "precision": round(c["precision"][i], 4), "recall": round(c["recall"][i], 4)}


def best_f1_conf(result: dict, cls: str) -> float:
    f1 = np.asarray(result["per_class"][cls]["curve"]["f1"])
    return float(np.asarray(result["conf_grid"])[int(np.argmax(f1))])


def strip(result: dict) -> dict:
    return {"overall": result["overall"],
            "per_class": {k: {m: v[m] for m in ("precision", "recall", "map50", "map50_95")}
                          for k, v in result["per_class"].items()}}


def main() -> None:
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable.")
    frozen = {n: sha256(MODELS / n) for n in FROZEN_V1}
    specs = models()
    validation, test = {}, {}
    for name, spec in specs.items():
        validation[name] = evaluate(spec, VALIDATION_YAML, "val", f"{name}_val")
        test[name] = evaluate(spec, TEST_YAML, "test", f"{name}_test")
        print(name, "test vest recall", round(test[name]["per_class"]["safety-vest"]["recall"], 3))
    if {n: sha256(MODELS / n) for n in FROZEN_V1} != frozen:
        raise AssertionError("A frozen PPE-v1 artifact changed")

    # Consistency with the official results (same model, same images, same settings).
    official = {"PPE-v1": json.loads(OFFICIAL_V1.read_text(encoding="utf-8")),
                "v2s1024": json.loads(OFFICIAL_V2.read_text(encoding="utf-8"))}
    consistency = {k: {"official_map50": round(v["overall"]["map50"], 4),
                       "rescored_map50": round(test[k]["overall"]["map50"], 4)} for k, v in official.items()}

    v1_vest = test["PPE-v1"]["per_class"]["safety-vest"]
    all_v2_worse = all(test[k]["per_class"]["safety-vest"]["map50"] < v1_vest["map50"]
                       and test[k]["per_class"]["safety-vest"]["recall"] < v1_vest["recall"]
                       for k in ("v2n1024", "v2s1024", "v2m1024"))

    combined = None
    if all_v2_worse:
        assignment = {"safety-vest": "PPE-v1", "default": "v2s1024"}
        thresholds = {"helmet": best_f1_conf(validation["v2s1024"], "helmet"),
                      "safety-vest": best_f1_conf(validation["PPE-v1"], "safety-vest")}
        source = lambda cls: assignment.get(cls, assignment["default"])
        classes = sorted(test["v2s1024"]["per_class"])

        def combined_view(results: dict) -> dict:
            per_class = {c: {m: results[source(c)]["per_class"][c][m] for m in ("map50", "map50_95")} for c in classes}
            return {"map50": float(np.mean([v["map50"] for v in per_class.values()])),
                    "map50_95": float(np.mean([v["map50_95"] for v in per_class.values()])),
                    "required": {c: {"source": source(c), **at(results[source(c)], c, thresholds[c]),
                                     "map50": round(results[source(c)]["per_class"][c]["map50"], 4)}
                                 for c in ("helmet", "safety-vest")}}

        combined = {"label": "POST-HOC, test-informed class assignment",
                    "class_assignment": "safety-vest from PPE-v1; every other class from v2s1024 (operator, after "
                                        "seeing the locked test; validation favoured v2s1024 on vests)",
                    "thresholds_from": "validation only: maximum-F1 confidence per class",
                    "thresholds": {k: round(v, 3) for k, v in thresholds.items()},
                    "validation": combined_view(validation), "test": combined_view(test),
                    "caveat": "Both components were already seen on the locked test; consistent with, not an "
                              "independent confirmation. A clean claim needs a fresh held-out set."}

    runtime_point = {name: {c: at(test[name], c, RUNTIME_CONF) for c in ("helmet", "safety-vest")} for name in specs}
    OUT.mkdir(parents=True, exist_ok=True)
    report = {"label": LABEL, "official_ppe_v2": "v2s1024", "locked_test_images": 810,
              "weights_sha256": {k: sha256(v["weights"]) for k, v in specs.items()},
              "consistency_with_official": consistency, "all_v2_worse_than_v1_on_vests": all_v2_worse,
              "validation": {k: strip(v) for k, v in validation.items()},
              "test": {k: strip(v) for k, v in test.items()},
              "test_at_runtime_conf_0.25": runtime_point, "combined": combined}
    (OUT / "posthoc_v2.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    def row(name: str, r: dict, cls: str | None) -> str:
        x = r["overall"] if cls is None else r["per_class"][cls]
        return f"| {name} | {x['precision']:.3f} | {x['recall']:.3f} | {x['map50']:.3f} | {x['map50_95']:.3f} |"

    lines = ["# PPE-v2 post-hoc analysis", "",
             f"**{LABEL}.** v2s1024 (selected on validation, evaluated once) remains the official PPE-v2 result. "
             "Same 810 locked images and settings as the official evaluations. Re-scored official models match "
             f"their official results: {consistency}.", ""]
    for split, results in (("Locked test (post-hoc)", test), ("Validation (810 original images)", validation)):
        lines += [f"## {split}", ""]
        for title, cls in (("All classes", None), *((c, c) for c in SHOWN)):
            lines += [f"**{title}**", "", "| Model | Precision | Recall | mAP@0.5 | mAP@0.5:0.95 |", "|---|---:|---:|---:|---:|"]
            lines += [row(f"{n} ({specs[n]['role']})", results[n], cls) for n in specs] + [""]
    lines += ["## At the runtime confidence threshold (0.25), locked test", "",
              "| Model | Helmet precision / recall | Vest precision / recall |", "|---|---|---|"]
    lines += [f"| {n} | {p['helmet']['precision']:.3f} / {p['helmet']['recall']:.3f} | "
              f"{p['safety-vest']['precision']:.3f} / {p['safety-vest']['recall']:.3f} |" for n, p in runtime_point.items()]
    lines += ["", f"Every v2 candidate worse than PPE-v1 on vests (locked test, mAP@0.5 and recall): **{all_v2_worse}**.", ""]
    if combined:
        lines += ["## Combined detector (post-hoc, test-informed)", "", combined["class_assignment"] + ".",
                  f"Thresholds ({combined['thresholds_from']}): {combined['thresholds']}.", "",
                  "| Split | All-class mAP@0.5 | mAP@0.5:0.95 | Helmet P / R (mAP@0.5) | Vest P / R (mAP@0.5) |",
                  "|---|---:|---:|---|---|"]
        for split in ("validation", "test"):
            v = combined[split]
            h, s = v["required"]["helmet"], v["required"]["safety-vest"]
            lines.append(f"| {split} | {v['map50']:.3f} | {v['map50_95']:.3f} | {h['precision']:.3f} / {h['recall']:.3f} "
                         f"({h['map50']:.3f}) | {s['precision']:.3f} / {s['recall']:.3f} ({s['map50']:.3f}) |")
        lines += ["", combined["caveat"], ""]
    (OUT / "posthoc_v2.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
