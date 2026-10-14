"""
DC-Guardian Evidence
PPE runtime check: compliance outcome and latency, PPE-v1 vs PPE-v2m.

Before PPE-v2m replaces PPE-v1 at runtime, check that the frozen compliance
policy (PPE-POLICY-v1: helmet and safety-vest; confidence 0.25; containment
association), tuned on PPE-v1 output, still behaves with the new detector.

Validation split only (810 original images); the locked test is not read.

1. Compliance: the image-level status the dashboard shows (COMPLIANT,
   NON_COMPLIANT, NO_PERSON) from each detector's full runtime pipeline,
   against the status the same association and policy give on the ground-truth
   boxes. Reported as a confusion table and three rates:
   - violations caught: truly NON_COMPLIANT images flagged NON_COMPLIANT;
   - false alarms: truly COMPLIANT images flagged NON_COMPLIANT;
   - missed violations: truly NON_COMPLIANT images reported COMPLIANT
     (the dangerous error: PPE "seen" that is not there).
2. Latency: cold start of the runtime worker (new process, model load, one
   image), as each dashboard upload does, and warm per-image inference.

Run with the PPE GPU environment from the repository root:
    .venv-ppe\\Scripts\\python.exe evidence\\ppe_detection\\src\\evaluate_runtime_compliance.py
Writes results/runtime_v2m/runtime_check.{md,json}.
"""

from __future__ import annotations

import json
import os
import statistics
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PIL import Image  # noqa: E402

from evidence.ppe_detection.src.ppe_association import associate_ppe_to_people  # noqa: E402
from evidence.ppe_detection.src.ppe_pipeline import PPECompliancePipeline  # noqa: E402
from evidence.ppe_detection.src.ppe_policy import evaluate_ppe_policy  # noqa: E402

PPE_ROOT = PROJECT_ROOT / "evidence" / "ppe_detection"
VALIDATION_LIST = PPE_ROOT / "data" / "processed" / "sh17_yolo_v2" / "validation_original.txt"
LOCKED_TEST_LIST = PPE_ROOT / "results" / "final_test" / "locked_test_images.txt"
OUT_DIR = PPE_ROOT / "results" / "runtime_v2m"
DETECTORS = ("v1", "v2m")
STATUSES = ("COMPLIANT", "NON_COMPLIANT", "NO_PERSON")
COLD_RUNS = 10
WARM_RUNS = 50
# A validation image close in size to the latency benchmark's (2758 x 1839, a locked-test image): 2493 x 1662.
LATENCY_IMAGE = PPE_ROOT / "data" / "raw" / "SH17" / "images" / "pexels-photo-2889082.jpeg"


def label_path(image: Path) -> Path:
    return Path(str(image).replace(f"{os.sep}images{os.sep}", f"{os.sep}labels{os.sep}")).with_suffix(".txt")


def truth_status(image: Path, names: dict[int, str]) -> str:
    """Status the frozen association and policy give on the ground-truth boxes."""
    with Image.open(image) as img:
        width, height = img.size
    detections = []
    for line in label_path(image).read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) != 5:
            continue
        cls, cx, cy, w, h = int(parts[0]), *map(float, parts[1:])
        detections.append({"class_id": cls, "class_name": names[cls], "confidence": 1.0,
                           "bbox_xyxy": [(cx - w / 2) * width, (cy - h / 2) * height,
                                         (cx + w / 2) * width, (cy + h / 2) * height]})
    return evaluate_ppe_policy(associate_ppe_to_people(detections, minimum_containment=0.5))["overall_status"]


def rates(pairs: list[tuple[str, str]]) -> dict:
    confusion = Counter(pairs)
    truly_non = sum(v for (t, _), v in confusion.items() if t == "NON_COMPLIANT")
    truly_ok = sum(v for (t, _), v in confusion.items() if t == "COMPLIANT")
    return {
        "confusion_truth_to_predicted": {f"{t}->{p}": confusion[(t, p)] for t in STATUSES for p in STATUSES},
        "images": len(pairs),
        "agreement": round(sum(v for (t, p), v in confusion.items() if t == p) / len(pairs), 4),
        "violations_caught": round(confusion[("NON_COMPLIANT", "NON_COMPLIANT")] / truly_non, 4) if truly_non else None,
        "false_alarms": round(confusion[("COMPLIANT", "NON_COMPLIANT")] / truly_ok, 4) if truly_ok else None,
        "missed_violations": round(confusion[("NON_COMPLIANT", "COMPLIANT")] / truly_non, 4) if truly_non else None,
        "truly_non_compliant": truly_non, "truly_compliant": truly_ok,
    }


def cold_start_ms(detector: str) -> list[float]:
    """New worker process per run, exactly as a dashboard upload starts it."""
    env = {**os.environ, "PYTHONPATH": str(PROJECT_ROOT), "DCG_PPE_DETECTOR": detector}
    times = []
    for _ in range(COLD_RUNS + 1):  # first run warms the disk cache and is discarded
        start = time.perf_counter()
        done = subprocess.run([sys.executable, "-m", "presentation.backend.app.ppe_worker", str(LATENCY_IMAGE)],
                              cwd=str(PROJECT_ROOT), env=env, capture_output=True, text=True, timeout=300,
                              check=False)  # nosec B603: fixed interpreter, module and project image
        if done.returncode != 0 or "DCG_PPE_RESULT=" not in done.stdout:
            raise SystemExit(f"worker failed for {detector}: {done.stderr[-500:]}")
        times.append((time.perf_counter() - start) * 1000)
    return times[1:]


def summary(values: list[float]) -> dict:
    ordered = sorted(values)
    return {"n": len(values), "median_ms": round(statistics.median(values), 1),
            "p95_ms": round(ordered[min(len(ordered) - 1, round(0.95 * (len(ordered) - 1)))], 1),
            "max_ms": round(max(values), 1)}


def main() -> int:
    images = [Path(p) for p in VALIDATION_LIST.read_text(encoding="utf-8").split()]
    locked = LOCKED_TEST_LIST.read_text(encoding="utf-8").split()
    locked_names = {Path(x).name for x in locked}
    if any(p.name in locked_names for p in [*images, LATENCY_IMAGE]):
        raise SystemExit("validation list overlaps the locked test; refusing to run")

    report = {"split": "validation (810 original images); locked test not read",
              "policy": "PPE-POLICY-v1 (helmet, safety-vest), confidence 0.25, containment 0.5",
              "compliance": {}, "latency": {}}
    pipelines = {d: PPECompliancePipeline(d) for d in DETECTORS}
    names = pipelines["v1"].model_names
    truth = {str(p): truth_status(p, names) for p in images}
    report["truth_distribution"] = dict(Counter(truth.values()))
    for detector, pipeline in pipelines.items():
        predicted = {str(p): pipeline.assess(str(p))["overall_status"] for p in images}
        report["compliance"][detector] = rates([(truth[k], predicted[k]) for k in truth])
        warm = []
        for _ in range(WARM_RUNS + 1):
            start = time.perf_counter()
            pipeline.assess(str(LATENCY_IMAGE))
            warm.append((time.perf_counter() - start) * 1000)
        report["latency"][detector] = {"warm_inference": summary(warm[1:])}
    del pipelines
    for detector in DETECTORS:
        report["latency"][detector]["cold_worker"] = summary(cold_start_ms(detector))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "runtime_check.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    c, lat = report["compliance"], report["latency"]
    lines = ["# PPE runtime check: PPE-v1 vs PPE-v2m", "",
             "Generated by `evidence/ppe_detection/src/evaluate_runtime_compliance.py`. Validation split only "
             "(810 original images); the locked test is not read. Same frozen policy for both detectors.", "",
             f"Ground-truth image status (policy on labelled boxes): {report['truth_distribution']}", "",
             "## Compliance outcome (image level, as shown on the dashboard)", "",
             "| Detector | Agreement with truth | Violations caught | False alarms | Missed violations (reported COMPLIANT) |",
             "|---|---:|---:|---:|---:|"]
    for d in DETECTORS:
        r = c[d]
        lines.append(f"| {d} | {r['agreement']:.1%} | {r['violations_caught']:.1%} | {r['false_alarms']:.1%} | "
                     f"{r['missed_violations']:.1%} |")
    lines += ["", "Confusion (truth → predicted):", "", "| Truth → predicted | " + " | ".join(DETECTORS) + " |",
              "|---|" + "---:|" * len(DETECTORS)]
    for key in c["v1"]["confusion_truth_to_predicted"]:
        lines.append(f"| {key} | " + " | ".join(str(c[d]["confusion_truth_to_predicted"][key]) for d in DETECTORS) + " |")
    lines += ["", "## Latency (operator workstation, RTX 3080 Ti; validation image 2493 x 1662)", "",
              "| Detector | Cold worker per upload, median (p95) | Warm inference per image, median (p95) |",
              "|---|---:|---:|"]
    for d in DETECTORS:
        cw, wi = lat[d]["cold_worker"], lat[d]["warm_inference"]
        lines.append(f"| {d} | {cw['median_ms'] / 1000:.2f} s ({cw['p95_ms'] / 1000:.2f} s) | "
                     f"{wi['median_ms']:.0f} ms ({wi['p95_ms']:.0f} ms) |")
    lines += ["", "Cold worker = new process, model load and one image, as each dashboard upload runs today "
              f"({COLD_RUNS} runs after one discarded warm-up). The dashboard adds up to 5 s for its refresh.", ""]
    (OUT_DIR / "runtime_check.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
