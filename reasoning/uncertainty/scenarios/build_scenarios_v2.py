"""
DC-Guardian Reasoning
Build labelled scenario set v2: every environmental state comes from the real detector.

Scenario set v1 (labelled_scenarios.json) uses four environmental states the
frozen environmental detector cannot produce (it measures temperature and
humidity only): WATER_LEAK_DETECTED, SMOKE_DETECTED, AIRFLOW_ANOMALY and
COOLING_ANOMALY, in 8 of 40 scenarios. v1 stays unchanged so published results
remain reproducible. This script writes:

    labelled_scenarios_v2.json      40 scenarios; every environmental event
                                    carries a raw reading and the state the
                                    frozen detector assigns to it
    extended_sensor_scenarios.json  the 8 original scenarios, verbatim from v1:
                                    what leak/smoke/airflow sensors would add
                                    (future-work evidence, reported apart)

Operator decisions (2026-10-13):
- leak -> high humidity; smoke, airflow and cooling -> high temperature;
- narratives of the 8 rewritten scenarios describe what the sensors read, not
  what is related;
- all 40 v2 scenarios are relabelled blind by the operator (labelling/pack_v2/);
  no v1 label is copied into v2 and labels are never invented. Until the
  operator's labels exist (labelling/results/operator-v2_labels.csv) every
  scenario is marked PENDING_BLIND_RELABEL and carries no ground truth. The
  operator also wrote v1, so v2 labels are still not independent labels.

Run from the repository root:
    python reasoning/uncertainty/scenarios/build_scenarios_v2.py
"""

from __future__ import annotations

import copy
import csv
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evidence.environmental_monitoring.src.environmental_detector import assess_environmental_condition  # noqa: E402

HERE = Path(__file__).resolve().parent
V1_PATH = HERE / "labelled_scenarios.json"
V2_PATH = HERE / "labelled_scenarios_v2.json"
EXTENDED_PATH = HERE / "extended_sensor_scenarios.json"
LABELLING_DIR = HERE.parent / "labelling"
PACK_V2_KEY = LABELLING_DIR / "pack_v2_key.json"
OPERATOR_LABELS = LABELLING_DIR / "results" / "operator-v2_labels.csv"
PENDING = "PENDING_BLIND_RELABEL"
RELABELLED = "OPERATOR_BLIND_RELABEL"

# Raw readings (temperature_c, humidity_pct) for every environmental event.
# Thresholds of the frozen detector: temperature > 35 C, humidity > 80 % or < 20 %.
READINGS = {
    # unchanged states: the detector must reproduce the v1 state (checked below)
    "D01-E1": (37.2, 44.0), "D02-E1": (42.5, 40.0), "D03-E2": (36.4, 46.0), "D09-E1": (24.1, 85.0),
    "D11-E3": (41.8, 38.0), "T01-E1": (43.1, 39.0), "T02-E2": (36.9, 45.0), "T04-E2": (23.0, 16.0),
    "T05-E1": (24.6, 86.0), "T08-E2": (37.8, 43.0), "T10-E3": (36.2, 47.0), "T15-E1": (38.4, 42.0),
    "T16-E1": (37.0, 44.0), "T17-E1": (42.0, 41.0), "T20-E1": (23.8, 84.0), "T23-E3": (41.2, 40.0),
    # rewritten: what a temperature/humidity sensor would read instead of the unsupported state
    "D03-E1": (37.5, 38.0),  # was AIRFLOW_ANOMALY (utilities)
    "D10-E1": (46.0, 30.0),  # was SMOKE_DETECTED (utilities)
    "D14-E1": (25.0, 91.0),  # was WATER_LEAK_DETECTED (Hall B)
    "T02-E1": (38.2, 40.0),  # was COOLING_ANOMALY (utilities)
    "T09-E1": (36.8, 41.0),  # was AIRFLOW_ANOMALY (utilities)
    "T12-E1": (47.5, 28.0),  # was SMOKE_DETECTED (Hall A)
    "T19-E2": (37.9, 39.0),  # was COOLING_ANOMALY (utilities)
    "T22-E1": (24.5, 93.0),  # was WATER_LEAK_DETECTED (utilities)
}
# Operator mapping: the detector state each unsupported v1 state must become.
MAPPING = {"WATER_LEAK_DETECTED": "HIGH_HUMIDITY", "SMOKE_DETECTED": "HIGH_TEMPERATURE",
           "AIRFLOW_ANOMALY": "HIGH_TEMPERATURE", "COOLING_ANOMALY": "HIGH_TEMPERATURE"}

# Observation-only titles and narratives: what the sensors and cameras show, never what is related.
REWRITES = {
    "D03": ("Utilities heat, Hall B heat, Hall B drive",
            "The utilities sensor reads 37.5 °C. Hall B exceeds the temperature threshold 22 minutes later, and a "
            "Hall B drive is flagged at minute 41."),
    "D10": ("Utilities heat and PPE alert",
            "The utilities temperature reaches 46 °C; seven minutes later a person without full PPE is seen in utilities."),
    "D14": ("Hall B humidity and drive",
            "Humidity in Hall B rises sharply to 91%; 16 minutes later a drive on SRV-B1-02 is flagged."),
    "T02": ("Utilities heat, Hall A heat, two Hall A drives",
            "The utilities sensor reads 38.2 °C; Hall A exceeds the temperature threshold 18 minutes later; two "
            "Hall A drives are flagged around minutes 52-55."),
    "T09": ("Utilities heat, Hall B drive, PPE alert",
            "The utilities sensor reads 36.8 °C; a Hall B drive is flagged 33 minutes later; a low-confidence PPE "
            "alert fires in utilities at minute 5."),
    "T12": ("Hall A heat, PPE alert and unknown person",
            "Hall A reads 47.5 °C; within five minutes a person without full PPE and an unknown person are seen in Hall A."),
    "T19": ("Unauthorized person, utilities heat, Hall A drive",
            "P001 is recognized in utilities without authorization; 12 minutes later the utilities sensor reads "
            "37.9 °C; a Hall A drive is flagged 58 minutes after the first alert."),
    "T22": ("Utilities humidity, PPE alert, Hall B drive",
            "Humidity in utilities rises sharply to 93%; nine minutes later a person without PPE is seen there; a "
            "Hall B drive is flagged at minute 15."),
}


def detector_state(event: dict, reading: tuple[float, float]) -> dict:
    temperature, humidity = reading
    result = assess_environmental_condition(
        source_class=event["source_class"], source_id=event.get("sensor_id") or event.get("server_id"),
        observation_timestamp=event["timestamp"], temperature_c=temperature, humidity_pct=humidity)
    return result


def operator_incidents(scenario: dict, key: dict, rows: list[dict]) -> dict[str, str | None]:
    """Incident IDs from the operator's pair labels: connected components of Y pairs.

    Refuses contradictory labels (two events in one component that the operator
    marked N) instead of guessing; the operator resolves them.
    """
    ids = [e["event_id"] for e in scenario["events"]]
    parent = {e: e for e in ids}

    def find(x):
        while parent[x] != x:
            x = parent[x]
        return x

    marked = {}
    for r in rows:
        a, b = key["events"][r["event_a"]], key["events"][r["event_b"]]
        if a not in parent:
            continue
        marked[(a, b)] = r["related"].strip().upper()
        if marked[(a, b)] == "Y":
            parent[find(a)] = find(b)
    conflicts = [f"{a} + {b}" for (a, b), v in marked.items() if v == "N" and find(a) == find(b)]
    if conflicts:
        raise SystemExit(f"{scenario['scenario_id']}: labels contradict each other ({', '.join(conflicts)}); "
                         "ask the operator to resolve them.")
    groups: dict[str, list[str]] = {}
    for e in ids:
        groups.setdefault(find(e), []).append(e)
    incidents, number = {}, 0
    for members in sorted(groups.values(), key=lambda m: ids.index(m[0])):
        if len(members) == 1:
            incidents[members[0]] = None
        else:
            number += 1
            for m in members:
                incidents[m] = f"I{number}"
    return incidents


def load_operator_labels() -> tuple[dict, list[dict]] | None:
    if not OPERATOR_LABELS.exists():
        return None
    key = json.loads(PACK_V2_KEY.read_text(encoding="utf-8"))
    rows = list(csv.DictReader(open(OPERATOR_LABELS, encoding="utf-8-sig")))
    bad = [r["pair"] for r in rows if r["related"].strip().upper() not in ("Y", "N")]
    if bad:
        raise SystemExit(f"{OPERATOR_LABELS.name}: related must be Y or N ({', '.join(bad)})")
    expected = {r["pair"] for r in csv.DictReader(open(LABELLING_DIR / "pack_v2" / "labels.csv", encoding="utf-8-sig"))}
    if {r["pair"] for r in rows} != expected or len(rows) != len(expected):
        raise SystemExit(f"{OPERATOR_LABELS.name}: must contain every pair of pack_v2/labels.csv exactly once")
    return key, rows


def build() -> dict:
    v1 = json.loads(V1_PATH.read_text(encoding="utf-8"))
    labels = load_operator_labels()
    v2_scenarios, extended = [], []
    for scenario in v1["scenarios"]:
        new = copy.deepcopy(scenario)
        rewritten = scenario["scenario_id"] in REWRITES
        for event in new["events"]:
            if event["domain"] != "ENVIRONMENTAL":
                continue
            result = detector_state(event, READINGS[event["event_id"]])
            expected = MAPPING.get(event["state"], event["state"])
            if result["assessment"] != expected:
                raise SystemExit(f"{event['event_id']}: detector gives {result['assessment']}, expected {expected}")
            event["state"] = result["assessment"]
            event["measurements"] = result["measurements"]
            event["state_source"] = f"{result['component']} {result['component_version']} (frozen detector)"
        if rewritten:
            extended.append(copy.deepcopy(scenario))
            new["title"], new["narrative"] = REWRITES[scenario["scenario_id"]]
            new["original_v1_states"] = sorted({e["state"] for e in scenario["events"]
                                                 if e["domain"] == "ENVIRONMENTAL" and e["state"] in MAPPING})
        # No v1 label is carried into v2: ground truth comes only from the operator's blind labels.
        for event in new["events"]:
            event.pop("ground_truth_incident", None)
        if labels:
            for event_id, incident in operator_incidents(new, *labels).items():
                next(e for e in new["events"] if e["event_id"] == event_id)["ground_truth_incident"] = incident
            new["label_status"] = RELABELLED
        else:
            new["label_status"] = PENDING
        v2_scenarios.append(new)

    v2 = {"scenario_set_version": "DCG-LABELLED-SCENARIOS-v2", "topology": v1["topology"],
          "derived_from": "DCG-LABELLED-SCENARIOS-v1 (unchanged)",
          "environmental_states": "Every environmental state is assigned by the frozen environmental detector "
                                  "(assess_environmental_condition) from the event's measurements; "
                                  "built by build_scenarios_v2.py.",
          "labelling": "Full blind relabel of all 40 scenarios by the operator (labelling/pack_v2/), who also wrote "
                       "v1, so these are not independent labels. Pair labels become incidents: events joined by "
                       "related pairs share a ground_truth_incident; null marks an event related to no other. "
                       "PENDING_BLIND_RELABEL: no ground truth yet; no v1 label is copied.",
          "scenarios": v2_scenarios}
    ext = {"scenario_set_version": "DCG-EXTENDED-SENSOR-SCENARIOS-v1", "topology": v1["topology"],
           "purpose": "Future-work evidence: the 8 v1 scenarios whose environmental states need leak, smoke or "
                      "airflow sensors the prototype does not have. Verbatim from v1, with v1 labels; reported "
                      "apart from the headline results.",
           "labelling": v1["labelling"], "scenarios": extended}
    V2_PATH.write_text(json.dumps(v2, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    EXTENDED_PATH.write_text(json.dumps(ext, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    pending = sum(s.get("label_status") == PENDING for s in v2_scenarios)
    return {"scenarios": len(v2_scenarios), "rewritten": len(extended), "pending_labels": pending}


if __name__ == "__main__":
    summary = build()
    print(f"v2: {summary['scenarios']} scenarios, {summary['rewritten']} rewritten, "
          f"{summary['pending_labels']} awaiting blind labels")
    print(f"Wrote {V2_PATH.relative_to(PROJECT_ROOT)} and {EXTENDED_PATH.relative_to(PROJECT_ROOT)}")
