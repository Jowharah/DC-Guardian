"""
DC-Guardian Evidence
PPE — third-dataset test on CHV (Color Helmet and Vest), TEST ONLY

The SH17 locked test and the Kaggle helmet/jacket test have both informed
decisions (PPE-v2m runtime choice, PPE-v3 training), so neither is an
independent check any more. CHV (Wang et al., Sensors 2021) is a third public
dataset that no model has trained or been selected on. Protocol, fixed before
any result (2026-10-15):

1. All 1,330 CHV images are used (nothing is trained, selected or tuned on
   CHV). Images that are near-duplicates (difference hash, Hamming <= 6) of any
   SH17 image or any Kaggle helmet/jacket image (train, valid or test) are
   excluded, because those images trained one or more of the models.
2. Classes mapped to SH17: person -> person, vest -> safety-vest, blue / red /
   white / yellow helmet -> helmet.
3. Models, each at its own image size: PPE-v1 (640), PPE-v2 official v2s1024,
   PPE-v2m (runtime) and PPE-v3m (PR #31 weights, hash checked; 1024).
4. Detection: helmet, vest and person P / R / mAP@0.5 / mAP@0.5:0.95 with the
   settings of the earlier locked evaluations, and recall at the runtime
   confidence 0.25 with a 95% Wilson interval.
5. Compliance (CHV labels people): the image status the dashboard shows,
   from each model in the frozen PPE-POLICY-v1 pipeline, against the status the
   same association and policy give on the labelled boxes. v2s and v3m run in
   the PPE-v2m pipeline configuration (same 1024 px, confidence 0.25, IoU 0.7,
   policy) with their own weights; no runtime setting changes.

Dataset: Wang Z., Wu Y., Yang L., Thirunavukarasu A., Evison C., Zhao Y.
(2021) Sensors 21(10):3478, doi:10.3390/s21103478; "can be used freely".

    .venv-ppe\\Scripts\\python.exe evidence\\ppe_detection\\src\\evaluate_external_chv.py
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import torch
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ultralytics import YOLO  # noqa: E402

from evidence.ppe_detection.src.evaluate_external_helmet_jacket import HAMMING_MAX, hashes, wilson  # noqa: E402
from evidence.ppe_detection.src.evaluate_runtime_compliance import rates, truth_status  # noqa: E402
from evidence.ppe_detection.src.ppe_pipeline import PPECompliancePipeline  # noqa: E402

PPE = PROJECT_ROOT / "evidence" / "ppe_detection"
CHV = PPE / "data" / "raw" / "chv_download" / "CHV_dataset"
SH17_IMAGES = PPE / "data" / "raw" / "SH17" / "images"
KAGGLE = PPE / "data" / "raw" / "helmet_jacket"
WORK = PPE / "data" / "processed" / "chv_external"
OUT = PPE / "results" / "external_chv"
V3_SHA256 = "92a0a00f94b5166b066f721e4004e46210c1cadcb5c182714952c38baca61471"  # PR #31 metadata
MODELS = {
    "PPE-v1": (PPE / "models" / "ppe_yolov8_best.pt", 640, "v1"),
    "PPE-v2 official (v2s1024)": (PPE / "models" / "ppe_yolov8_v2_best.pt", 1024, "v2m"),
    "PPE-v2m (runtime)": (PPE / "models" / "ppe_yolov8_v2m_best.pt", 1024, "v2m"),
    "PPE-v3m (PR #31)": (PPE / "models" / "pretrained" / "ppe_yolov8_v3m_best_pr31.pt", 1024, "v2m"),
}
CLASS_MAP = {0: 0, 1: 16, 2: 10, 3: 10, 4: 10, 5: 10}
SCORED = ("helmet", "safety-vest", "person")
RUNTIME_CONF = 0.25


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def image_files(folder: Path) -> list[Path]:
    return sorted(p for p in folder.rglob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png"})


def build_eval_set() -> dict:
    images = image_files(CHV / "images")
    seen = image_files(SH17_IMAGES) + image_files(KAGGLE)
    chv_hash = hashes(images)
    seen_hash = np.array(hashes(seen), dtype=np.uint64)
    duplicates = {}
    for image, h in zip(images, chv_hash):
        distance = np.array([bin(int(x) ^ h).count("1") for x in seen_hash])
        if distance.min() <= HAMMING_MAX:
            duplicates[image.name] = seen[int(distance.argmin())].relative_to(PPE / "data" / "raw").as_posix()
    if WORK.exists():
        shutil.rmtree(WORK)
    (WORK / "images").mkdir(parents=True)
    (WORK / "labels").mkdir(parents=True)
    counts, kept = Counter(), []
    for image in images:
        if image.name in duplicates:
            continue
        shutil.copy2(image, WORK / "images" / image.name)
        lines = []
        for line in (CHV / "annotations" / (image.stem + ".txt")).read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if len(parts) == 5:
                cls = CLASS_MAP[int(parts[0])]
                counts[{0: "person", 16: "safety-vest", 10: "helmet"}[cls]] += 1
                lines.append(" ".join([str(cls), *parts[1:]]))
        (WORK / "labels" / (image.stem + ".txt")).write_text("\n".join(lines) + "\n", encoding="utf-8")
        kept.append(WORK / "images" / image.name)
    (WORK / "test_images.txt").write_text("\n".join(str(p.resolve()) for p in kept) + "\n", encoding="utf-8")
    names = yaml.safe_load((PPE / "data" / "processed" / "sh17_yolo" / "dataset.yaml").read_text(encoding="utf-8"))["names"]
    listing = str((WORK / "test_images.txt").resolve())
    (WORK / "dataset.yaml").write_text(yaml.safe_dump({"train": listing, "val": listing, "test": listing,
                                                       "nc": len(names), "names": names}, sort_keys=False),
                                       encoding="utf-8")
    return {"source_images": len(images), "images_compared_against": len(seen), "hamming_max": HAMMING_MAX,
            "near_duplicates_excluded": len(duplicates), "duplicate_examples": dict(list(duplicates.items())[:10]),
            "images_evaluated": len(kept), "instances": dict(counts), "kept": [str(p) for p in kept]}


def detection(weights: Path, imgsz: int, name: str, instances: dict) -> dict:
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
                    "at_runtime_conf": {"precision": round(float(box.p_curve[row][i]), 4), "recall": round(recall_rt, 4),
                                        "recall_ci95": wilson(recall_rt * instances[cls], instances[cls])}}
    return out


def compliance(weights: Path, config: str, images: list[str], truth: dict) -> dict:
    pipeline = PPECompliancePipeline(config)
    pipeline.model = YOLO(str(weights))  # same frozen settings and policy, this model's weights
    pipeline.model_names = {int(k): str(v) for k, v in pipeline.model.names.items()}
    predicted = {p: pipeline.assess(p)["overall_status"] for p in images}
    return rates([(truth[p], predicted[p]) for p in images])


def main() -> None:
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable.")
    if sha256(MODELS["PPE-v3m (PR #31)"][0]) != V3_SHA256:
        raise SystemExit("PPE-v3m weights do not match the PR #31 metadata hash.")
    frozen = {k: sha256(w) for k, (w, _, _) in MODELS.items()}
    dataset = build_eval_set()
    images = dataset.pop("kept")
    print({k: v for k, v in dataset.items() if k != "duplicate_examples"})
    names = PPECompliancePipeline("v1").model_names
    truth = {p: truth_status(Path(p), names) for p in images}
    results, outcomes = {}, {}
    for name, (weights, imgsz, config) in MODELS.items():
        results[name] = detection(weights, imgsz, name.split()[0] + name.split()[-1].strip("()#"), dataset["instances"])
        outcomes[name] = compliance(weights, config, images, truth)
        print(name, "vest recall", results[name]["safety-vest"]["recall"], "agreement", outcomes[name]["agreement"])
    if {k: sha256(w) for k, (w, _, _) in MODELS.items()} != frozen:
        raise AssertionError("A model file changed during evaluation")

    OUT.mkdir(parents=True, exist_ok=True)
    report = {"label": "THIRD-DATASET TEST (CHV; nothing trained, selected or tuned on it; SH17 and Kaggle near-duplicates excluded)",
              "dataset": "CHV, Wang et al. 2021, Sensors 21(10):3478, doi:10.3390/s21103478; all 1,330 images",
              "class_mapping": {"person": "person", "vest": "safety-vest", "blue/red/white/yellow helmet": "helmet"},
              "weights_sha256": frozen, **dataset, "truth_distribution": dict(Counter(truth.values())),
              "detection": results, "compliance": outcomes}
    (OUT / "external_chv.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    lines = ["# Third-dataset test: CHV (Color Helmet and Vest)", "",
             f"{report['label']}. {dataset['images_evaluated']} of {dataset['source_images']} images "
             f"({dataset['near_duplicates_excluded']} near-duplicates of SH17 or Kaggle images excluded); "
             f"{dataset['instances'].get('person', 0)} people, {dataset['instances'].get('helmet', 0)} helmets, "
             f"{dataset['instances'].get('safety-vest', 0)} vests.", "",
             "## Detection", "",
             "| Model | Class | Precision | Recall | mAP@0.5 | mAP@0.5:0.95 | Recall at conf 0.25 (95% CI) |",
             "|---|---|---:|---:|---:|---:|---|"]
    for name, per_class in results.items():
        for cls in SCORED:
            x = per_class[cls]
            rt = x["at_runtime_conf"]
            lines.append(f"| {name} | {cls} | {x['precision']:.3f} | {x['recall']:.3f} | {x['map50']:.3f} | "
                         f"{x['map50_95']:.3f} | {rt['recall']:.3f} ({rt['recall_ci95'][0]:.3f}–{rt['recall_ci95'][1]:.3f}) |")
    lines += ["", "## Compliance (image status shown on the dashboard)", "",
              f"Ground truth (frozen policy on the labelled boxes): {report['truth_distribution']}.", "",
              "| Model | Agreement with truth | Violations caught | False alarms | Missed violations (reported COMPLIANT) |",
              "|---|---:|---:|---:|---:|"]
    pct = lambda v: "–" if v is None else f"{v:.1%}"
    for name, r in outcomes.items():
        lines.append(f"| {name} | {pct(r['agreement'])} | {pct(r['violations_caught'])} | {pct(r['false_alarms'])} | "
                     f"{pct(r['missed_violations'])} |")
    lines += ["", "Caveats: CHV images come from online sources and existing open datasets (overlaps with SH17 and the "
                  "Kaggle set were removed by difference hash); construction scenes, not data-centre ones; PPE-v3m is "
                  "PR #31's model, not yet merged or selectable at runtime.", ""]
    (OUT / "external_chv.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
