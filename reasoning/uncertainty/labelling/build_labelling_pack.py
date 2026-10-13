"""
DC-Guardian Reasoning
Build a blind labelling pack for independent labelling of the scenarios.

The scenario file states the answers: titles and narratives say what is
related ("an unrelated SSH candidate"), and every event carries its
ground-truth label. An independent labeller must see only what an operator
would see. This script writes:

    labelling/pack/INSTRUCTIONS.md     what to do, facility brief, glossary
    labelling/pack/scenarios_blind.md  40 scenarios, shuffled, neutral IDs,
                                       events only (no titles, narratives,
                                       labels, split or model output)
    labelling/pack/labels.csv          one row per candidate pair to fill in
    labelling/pack_key.json            neutral ID -> original ID (NOT for
                                       the labeller; kept outside pack/)

Send the labeller the pack/ folder only. Score the returned labels.csv with
score_labels.py. The output is deterministic (fixed shuffle seed).

Run from the repository root:
    python reasoning/uncertainty/labelling/build_labelling_pack.py
"""

from __future__ import annotations

import csv
import json
import random
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from reasoning.uncertainty.bayesian_correlation import load_knowledge_base  # noqa: E402
from reasoning.uncertainty.evaluate import candidate_pairs, load_scenarios  # noqa: E402

HERE = Path(__file__).resolve().parent
PACK_DIR = HERE / "pack"
KEY_PATH = HERE / "pack_key.json"
TOPOLOGY_PATH = PROJECT_ROOT / "shared" / "topology" / "data_center_topology.json"
SHUFFLE_SEED = 7042
# Fields an operator would see on an event. Labels and narratives are never copied.
VISIBLE = ("domain", "state", "zone_id", "rack_id", "server_id", "sensor_id", "camera_id",
           "source_class", "failure_probability", "confidence", "authorization", "person_id")

GLOSSARY = {
    "ENVIRONMENTAL": "Environmental sensor or hardware telemetry. States: HIGH_TEMPERATURE, HIGH_HUMIDITY, LOW_HUMIDITY, "
                     "AIRFLOW_ANOMALY, COOLING_ANOMALY, SMOKE_DETECTED, WATER_LEAK_DETECTED. Source ENVIRONMENTAL_SENSOR is a "
                     "dedicated room sensor; HARDWARE_TELEMETRY comes from a server's own sensors.",
    "MAINTENANCE": "Hard-drive failure-risk model (SMART data). AT_RISK = predicted failure within seven days; "
                   "failure_probability is the model score (alert threshold 0.45; most alerts are false alarms).",
    "CYBERSECURITY": "SSH login anomaly detector on a server. EXPLICIT_SECURITY_EVENT = the log itself shows a security "
                     "event (e.g. break-in attempt); HIGH_CONFIDENCE_ANOMALY = several detectors agree; ANOMALY_CANDIDATE = "
                     "only one detector flagged it (weaker).",
    "PHYSICAL_SECURITY": "Camera face recognition. UNKNOWN_PERSON = face not enrolled (visitor or stranger); "
                         "authorization UNAUTHORIZED = a recognized person who is not authorized for that zone.",
    "SAFETY": "Camera PPE detection. PPE_NON_COMPLIANT = a person without detected helmet or safety vest; confidence is "
              "the detector's confidence (the detector misses about half of PPE items, so low confidence is weak evidence).",
}


def facility_brief() -> list[str]:
    topology = json.loads(TOPOLOGY_PATH.read_text(encoding="utf-8"))
    lines = ["## The facility (synthetic data center DC-01)", ""]
    for zone in topology["data_center"]["zones"]:
        lines.append(f"**{zone['zone_id']} — {zone['name']}**")
        for rack in zone.get("racks", []):
            servers = ", ".join(s["server_id"] for s in rack.get("servers", []))
            lines.append(f"- Rack {rack['rack_id']}: servers {servers}")
        for kind in ("cameras", "sensors", "equipment"):
            for item in zone.get(kind, []):
                ident = item.get("camera_id") or item.get("sensor_id") or item.get("equipment_id") or item.get("id")
                lines.append(f"- {item.get('name', kind)} ({ident})")
        lines.append("")
    for dependency in load_knowledge_base()["infrastructure_dependencies"]["dependencies"]:
        lines.append(f"- Cooling: {dependency['provider_asset']} in {dependency['provider_zone']} cools "
                     f"{' and '.join(dependency['dependent_zones'])}.")
    people = topology.get("people", [])
    if people:
        lines += ["", "Staff and their authorized zones:", ""]
        lines += [f"- {p['person_id']} ({p.get('role', '').replace('_', ' ').lower()}): "
                  f"{', '.join(p.get('authorized_zones', []))}" for p in people]
    return lines + [""]


def _detail(key: str, value) -> str:
    if key == "measurements":  # raw environmental readings (scenario set v2)
        units = {"temperature_c": ("temperature", "°C"), "humidity_pct": ("humidity", "%")}
        return " · ".join(f"{units[k][0]}: {v} {units[k][1]}" for k, v in value.items() if v is not None)
    return f"{key.replace('_id', '').replace('_', ' ')}: {value}"


def event_view(event: dict, start: datetime, visible: tuple = VISIBLE) -> dict:
    """What an operator sees of one event: relative time, domain, state, details."""
    when = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
    minute = int((when - start).total_seconds() // 60)
    details = " · ".join(_detail(k, event[k]) for k in visible[2:] if event.get(k) is not None)
    return {"id": event["neutral_id"], "time": f"+{minute} min ({when:%H:%M})", "minute": minute,
            "domain": event["domain"], "state": event["state"], "details": details}


def event_line(event: dict, start: datetime, visible: tuple = VISIBLE) -> str:
    v = event_view(event, start, visible)
    return f"| {v['id']} | {v['time']} | {v['domain']} | {v['state']} | {v['details']} |"


def build(scenarios: list[dict] | None = None, *, pack_dir: Path = PACK_DIR, key_path: Path = KEY_PATH,
          prefix: str = "S", seed: int = SHUFFLE_SEED, visible: tuple = VISIBLE, glossary: dict = GLOSSARY,
          duration: str = "60–90 minutes") -> dict:
    """Write a blind pack. Defaults build the published 40-scenario pack (v1); other
    arguments build a smaller pack, e.g. the v2 relabelling round."""
    scenarios = load_scenarios() if scenarios is None else scenarios
    order = list(range(len(scenarios)))
    random.Random(seed).shuffle(order)
    key, blind, rows = {"scenarios": {}, "events": {}}, [], []
    for number, index in enumerate(order, start=1):
        scenario = scenarios[index]
        sid = f"{prefix}{number:02d}"
        key["scenarios"][sid] = {"original_id": scenario["scenario_id"], "split": scenario["split"]}
        events = sorted(scenario["events"], key=lambda e: e["timestamp"])
        for position, event in enumerate(events, start=1):
            event["neutral_id"] = f"{sid}-E{position}"
            key["events"][event["neutral_id"]] = event["event_id"]
        start = datetime.fromisoformat(events[0]["timestamp"].replace("Z", "+00:00"))
        blind += [f"### Scenario {sid}", "", "| Event | Time | Domain | State | Details |", "|---|---|---|---|---|"]
        blind += [event_line(e, start, visible) for e in events] + [""]
        views = {e["neutral_id"]: event_view(e, start, visible) for e in events}
        for left, right in candidate_pairs(scenario):
            a, b = sorted([left["neutral_id"], right["neutral_id"]])
            va, vb = views[a], views[b]
            others = " | ".join(f"{v['id']} {v['time']} {v['domain']} {v['state']}"
                                for k, v in views.items() if k not in (a, b)) or "none"
            # One self-contained row: everything needed to judge the pair, then the three columns to fill.
            rows.append({"scenario": sid, "pair": f"{a} + {b}",
                         "event_a": a, "a_time": va["time"], "a_domain": va["domain"], "a_state": va["state"],
                         "a_details": va["details"],
                         "event_b": b, "b_time": vb["time"], "b_domain": vb["domain"], "b_state": vb["state"],
                         "b_details": vb["details"],
                         "minutes_apart": abs(vb["minute"] - va["minute"]), "other_events_in_scenario": others,
                         "related": "", "confidence": "", "note": ""})

    pack_dir.mkdir(parents=True, exist_ok=True)
    instructions = [
        "# Independent labelling — DC-Guardian scenarios",
        "",
        "Thank you for labelling. Your labels are an **independent check** of a research result, so please:",
        "",
        "1. **Work alone** and do not discuss the scenarios with the person who wrote them.",
        "2. **Use only the files in this folder.** Do not open the DC-Guardian repository, its documents or results.",
        "3. Judge each pair as an experienced data-center operator would. There is no trick; disagreement is useful data.",
        "",
        "## The task",
        "",
        "Each scenario is a 120-minute window in which several abnormal alerts fired. For **every row in `labels.csv`** "
        "decide whether the two events are **part of the same underlying incident**: one caused the other, both have "
        "the same cause, or both come from the same person or response. Two problems that merely happen at the same "
        "time and place are **not** related.",
        "",
        "Fill in for each row:",
        "",
        "- `related`: **Y** (same incident) or **N** (not the same incident).",
        "- `confidence`: **1** guess · **2** fairly sure · **3** sure.",
        "- `note` (optional): your reason, especially when unsure.",
        "",
        f"There are {len(rows)} rows in {len(scenarios)} scenarios; expect about {duration}. Each row of "
        "`labels.csv` shows both events in full, the minutes between them and the other alerts in the same scenario, "
        "so you can work in Excel alone; `scenarios_blind.md` shows each scenario as a whole if you prefer. "
        "**Make a copy of `labels.csv`, fill in the copy**, save it as CSV (keep the columns) and send it back.",
        "",
        *facility_brief(),
        "## What the alerts mean",
        "",
        *[f"- **{domain}:** {text}" for domain, text in glossary.items()],
        "",
    ]
    (pack_dir / "INSTRUCTIONS.md").write_text("\n".join(instructions), encoding="utf-8")
    (pack_dir / "scenarios_blind.md").write_text(
        "\n".join(["# Scenarios (blind)", "", "Times are minutes from the first alert in the scenario.", ""] + blind),
        encoding="utf-8")
    with open(pack_dir / "labels.csv", "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    key_path.write_text(json.dumps(key, indent=2) + "\n", encoding="utf-8")
    return {"scenarios": len(scenarios), "pairs": len(rows)}


if __name__ == "__main__":
    summary = build()
    print(f"Pack written to {PACK_DIR.relative_to(PROJECT_ROOT)}: {summary['scenarios']} scenarios, {summary['pairs']} pairs.")
    print(f"Key (keep away from the labeller): {KEY_PATH.relative_to(PROJECT_ROOT)}")
