"""
DC-Guardian Evidence
PPE — external test, input-size SENSITIVITY (explanatory, not used to choose)

The external images are 640 x 640. PPE-v1 runs at 640 px, so it sees them at
native size; the v2 models run at 1024 px, so every image is upscaled first.
This scores v2s1024 and v2m at 640 px on the same external set to test whether
the upscaling explains their weaker helmet result. It changes no model, no
runtime setting and no reported official result.

Run after evaluate_external_helmet_jacket.py (which builds the evaluation set):
    .venv-ppe\\Scripts\\python.exe evidence\\ppe_detection\\src\\evaluate_external_sensitivity.py
"""

from __future__ import annotations

import json

import torch

from evaluate_external_helmet_jacket import MODELS, OUT, SCORED, WORK, evaluate


def main() -> None:
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable.")
    if not (WORK / "dataset.yaml").exists():
        raise SystemExit("Run evaluate_external_helmet_jacket.py first.")
    official = json.loads((OUT / "external_helmet_jacket.json").read_text(encoding="utf-8"))
    rows = {}
    for name in ("PPE-v2 official (v2s1024)", "PPE-v2m (runtime)"):
        weights, _ = MODELS[name]
        rows[name] = evaluate(weights, 640, name.split()[0] + "_640", official["instances"])
    report = {"label": "SENSITIVITY (explanatory; v2 models at 640 px instead of 1024 px; not used to choose)",
              "at_640": rows, "at_native_setting": official["results"]}
    (OUT / "external_sensitivity_640.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = ["# External test — input-size sensitivity", "", report["label"] + ".", "",
             "| Model | Input size | Helmet mAP@0.5 | Helmet recall at 0.25 | Vest mAP@0.5 | Vest recall at 0.25 |",
             "|---|---:|---:|---:|---:|---:|"]
    for name in MODELS:
        for size, source in ((MODELS[name][1], official["results"].get(name)), (640, rows.get(name))):
            if source is None or (size == 640 and name == "PPE-v1" and source is not official["results"].get(name)):
                continue
            h, v = source["helmet"], source["safety-vest"]
            lines.append(f"| {name} | {size} | {h['map50']:.3f} | {h['at_runtime_conf']['recall']:.3f} | "
                         f"{v['map50']:.3f} | {v['at_runtime_conf']['recall']:.3f} |")
    (OUT / "external_sensitivity_640.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
