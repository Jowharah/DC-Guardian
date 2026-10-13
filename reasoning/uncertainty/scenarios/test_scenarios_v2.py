"""Scenario set v2: every environmental state can be produced by the real detector.

The headline scenario set must not contain alerts the prototype cannot raise.
v1 is kept unchanged (published results); the 8 scenarios it needed leak,
smoke, airflow or cooling sensors for live on as the extended-sensor set.
"""
import csv
import hashlib
import json

import pytest

from evidence.environmental_monitoring.src.environmental_detector import assess_environmental_condition
from reasoning.uncertainty.bayesian_correlation import is_abnormal
from reasoning.uncertainty.labelling import build_labelling_pack, build_relabel_pack
from reasoning.uncertainty.scenarios import build_scenarios_v2 as v2

V1_SHA256 = "c73ae520823cad38bc27e664f46ab5a2bacbc1060a49d556795b355e1dbd12e1"  # LF bytes, as published


def _text(path):
    return path.read_bytes().replace(b"\r\n", b"\n")  # Windows checks out CRLF


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))["scenarios"]


@pytest.fixture(scope="module")
def producible_states():
    """Every state the frozen detector can assign, found by running it over the measurement range."""
    states = set()
    for source in ("ENVIRONMENTAL_SENSOR", "HARDWARE_TELEMETRY"):
        for temperature in range(-10, 81):
            for humidity in range(0, 101, 2):
                states.add(assess_environmental_condition(
                    source_class=source, source_id="X", observation_timestamp="2026-10-01T00:00:00+00:00",
                    temperature_c=float(temperature), humidity_pct=float(humidity))["assessment"])
    return states


def test_detector_cannot_produce_the_v1_only_states(producible_states):
    assert producible_states == {"NORMAL", "HIGH_TEMPERATURE", "HIGH_HUMIDITY", "LOW_HUMIDITY"}


def test_every_v2_environmental_state_is_producible_by_the_detector(producible_states):
    for scenario in _load(v2.V2_PATH):
        for event in scenario["events"]:
            if event["domain"] == "ENVIRONMENTAL":
                assert event["state"] in producible_states, (scenario["scenario_id"], event["state"])


def test_every_v2_environmental_state_is_what_the_detector_says_for_its_reading():
    for scenario in _load(v2.V2_PATH):
        for event in scenario["events"]:
            if event["domain"] != "ENVIRONMENTAL":
                continue
            m = event["measurements"]
            result = assess_environmental_condition(
                source_class=event["source_class"], source_id=event.get("sensor_id") or event.get("server_id"),
                observation_timestamp=event["timestamp"], temperature_c=m["temperature_c"],
                humidity_pct=m["humidity_pct"])
            assert result["assessment"] == event["state"], event["event_id"]
            assert is_abnormal(event), event["event_id"]


def test_committed_files_are_current():
    before = {p: _text(p) for p in (v2.V2_PATH, v2.EXTENDED_PATH)}
    v2.build()
    assert before == {p: _text(p) for p in before}, "Run build_scenarios_v2.py and commit the result."


def test_v1_is_unchanged():
    assert hashlib.sha256(_text(v2.V1_PATH)).hexdigest() == V1_SHA256


def test_extended_set_is_the_eight_v1_scenarios_verbatim():
    v1 = {s["scenario_id"]: s for s in _load(v2.V1_PATH)}
    extended = _load(v2.EXTENDED_PATH)
    assert sorted(s["scenario_id"] for s in extended) == sorted(v2.REWRITES)
    assert all(s == v1[s["scenario_id"]] for s in extended)


def test_only_the_rewritten_scenarios_change_beyond_readings():
    v1 = {s["scenario_id"]: s for s in _load(v2.V1_PATH)}
    for scenario in _load(v2.V2_PATH):
        if scenario["scenario_id"] in v2.REWRITES:
            continue
        old = v1[scenario["scenario_id"]]
        assert [e["state"] for e in scenario["events"]] == [e["state"] for e in old["events"]]
        assert [e.get("ground_truth_incident") for e in scenario["events"]] == \
               [e.get("ground_truth_incident") for e in old["events"]]


def test_rewritten_scenarios_carry_no_reused_labels():
    for scenario in _load(v2.V2_PATH):
        if scenario["scenario_id"] not in v2.REWRITES:
            assert "label_status" not in scenario
            continue
        if scenario["label_status"] == v2.PENDING:
            assert all("ground_truth_incident" not in e for e in scenario["events"])
        else:
            assert scenario["label_status"] == "OPERATOR_BLIND_RELABEL"


def test_pair_labels_become_incidents_and_contradictions_are_refused():
    scenario = {"scenario_id": "X", "events": [{"event_id": i} for i in ("A", "B", "C", "D")]}
    key = {"events": {"a": "A", "b": "B", "c": "C", "d": "D"}}
    rows = [{"event_a": "a", "event_b": "b", "related": "Y"}, {"event_a": "b", "event_b": "c", "related": "Y"},
            {"event_a": "a", "event_b": "d", "related": "N"}]
    assert v2.operator_incidents(scenario, key, rows) == {"A": "I1", "B": "I1", "C": "I1", "D": None}
    rows.append({"event_a": "a", "event_b": "c", "related": "N"})
    with pytest.raises(SystemExit, match="contradict"):
        v2.operator_incidents(scenario, key, rows)


def test_relabel_pack_is_current_blind_and_complete():
    pack_dir = build_relabel_pack.PACK_DIR
    before = {p.name: _text(p) for p in pack_dir.iterdir()}
    key_before = _text(build_relabel_pack.KEY_PATH)
    build_relabel_pack.build()
    assert before == {p.name: _text(p) for p in pack_dir.iterdir()} and key_before == _text(build_relabel_pack.KEY_PATH)
    text = "\n".join(p.read_text(encoding="utf-8").lower() for p in pack_dir.iterdir())
    leaks = ("ground_truth", "unrelated", "coincid", "narrative", "incident i", '"split"', "dev split", "test split",
             "leak", "smoke", "airflow", "cooling_anomaly", "chiller fault")
    for word in leaks:
        assert word not in text, f"relabel pack leaks '{word}'"
    v1 = {s["scenario_id"]: s for s in _load(v2.V1_PATH)}
    for sid, (title, _) in v2.REWRITES.items():
        assert title.lower() not in text and v1[sid]["title"].lower() not in text
        assert sid.lower() + "-" not in text, "pack leaks original event IDs"
    rows = list(csv.DictReader(open(pack_dir / "labels.csv", encoding="utf-8-sig")))
    assert len(rows) == 20 and all(not r["related"] for r in rows)
    assert build_labelling_pack.VISIBLE == tuple(v for v in build_relabel_pack.VISIBLE if v != "measurements")
