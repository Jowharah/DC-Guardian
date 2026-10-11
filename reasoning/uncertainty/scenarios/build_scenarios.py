"""
DC-Guardian Reasoning
Build the labelled multi-domain scenario set.

Each scenario is a 120-minute snapshot of the synthetic DC-01 data center
containing several abnormal Evidence events. Every event carries a
`ground_truth_incident` label: events with the same label belong to one
underlying incident, and `null` marks unrelated background abnormalities.
The label is written from the scenario narrative, not from any model output.

Splits:
- dev  (16 scenarios): written first and used while building the model code.
- test (24 scenarios): written afterwards without scoring them; the
  knowledge base was frozen before any evaluation.

Run from the repository root:
    python reasoning/uncertainty/scenarios/build_scenarios.py
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


OUTPUT = Path(__file__).resolve().parent / "labelled_scenarios.json"

SERVERS = {
    "SRV-A1-01": ("RACK-A1", "ZONE-A"),
    "SRV-A1-02": ("RACK-A1", "ZONE-A"),
    "SRV-B1-01": ("RACK-B1", "ZONE-B"),
    "SRV-B1-02": ("RACK-B1", "ZONE-B"),
}
ZONE_SENSOR = {"ZONE-A": "SEN-A-01", "ZONE-B": "SEN-B-01", "ZONE-C": "SEN-C-01"}
ZONE_CAMERA = {"ZONE-A": "CAM-A-01", "ZONE-B": "CAM-B-01", "ZONE-C": "CAM-C-01"}


class Scenario:
    def __init__(self, scenario_id, split, start, title, narrative):
        self.data = {
            "scenario_id": scenario_id,
            "split": split,
            "title": title,
            "narrative": narrative,
            "events": [],
        }
        self.start = datetime.fromisoformat(start).replace(tzinfo=timezone.utc)

    def _add(self, minute, incident, **fields):
        number = len(self.data["events"]) + 1
        event = {
            "event_id": f"{self.data['scenario_id']}-E{number}",
            "timestamp": (self.start + timedelta(minutes=minute)).isoformat(),
            **fields,
            "ground_truth_incident": incident,
        }
        self.data["events"].append(event)
        return self

    def ssh(self, minute, server, state, incident=None):
        rack, zone = SERVERS[server]
        return self._add(minute, incident, domain="CYBERSECURITY", state=state,
                         server_id=server, rack_id=rack, zone_id=zone)

    def maint(self, minute, server, probability, incident=None):
        rack, zone = SERVERS[server]
        return self._add(minute, incident, domain="MAINTENANCE", state="AT_RISK",
                         failure_probability=probability, server_id=server, rack_id=rack, zone_id=zone)

    def env_sensor(self, minute, zone, state, incident=None):
        return self._add(minute, incident, domain="ENVIRONMENTAL", state=state,
                         source_class="ENVIRONMENTAL_SENSOR", sensor_id=ZONE_SENSOR[zone], zone_id=zone)

    def env_hw(self, minute, server, state, incident=None):
        rack, zone = SERVERS[server]
        return self._add(minute, incident, domain="ENVIRONMENTAL", state=state,
                         source_class="HARDWARE_TELEMETRY", server_id=server, rack_id=rack, zone_id=zone)

    def face_unauthorized(self, minute, zone, person, incident=None):
        return self._add(minute, incident, domain="PHYSICAL_SECURITY", state="RECOGNIZED",
                         authorization="UNAUTHORIZED", person_id=person,
                         camera_id=ZONE_CAMERA[zone], zone_id=zone)

    def face_unknown(self, minute, zone, incident=None):
        return self._add(minute, incident, domain="PHYSICAL_SECURITY", state="UNKNOWN_PERSON",
                         camera_id=ZONE_CAMERA[zone], zone_id=zone)

    def ppe(self, minute, zone, confidence, incident=None):
        return self._add(minute, incident, domain="SAFETY", state="PPE_NON_COMPLIANT",
                         confidence=confidence, camera_id=ZONE_CAMERA[zone], zone_id=zone)


def scenarios():
    s = []
    # ---------------------------------------------------------------- dev
    s.append(Scenario("D01", "dev", "2026-10-01T02:00", "Hall A hotspot",
        "A dedicated sensor reports high temperature in Server Hall A; nine minutes later a drive on SRV-A1-01 is assessed at risk.")
        .env_sensor(0, "ZONE-A", "HIGH_TEMPERATURE", "I1").maint(9, "SRV-A1-01", 0.82, "I1"))
    s.append(Scenario("D02", "dev", "2026-10-01T05:30", "Server heat and drive risk",
        "Hardware telemetry on SRV-B1-02 reports high temperature and the same server's drive is flagged at moderate risk four minutes later.")
        .env_hw(0, "SRV-B1-02", "HIGH_TEMPERATURE", "I1").maint(4, "SRV-B1-02", 0.55, "I1"))
    s.append(Scenario("D03", "dev", "2026-10-01T11:00", "Chiller fault cascade",
        "The primary chiller loses airflow. Hall B warms 22 minutes later and a Hall B drive is flagged at minute 41.")
        .env_sensor(0, "ZONE-C", "AIRFLOW_ANOMALY", "I1").env_sensor(22, "ZONE-B", "HIGH_TEMPERATURE", "I1")
        .maint(41, "SRV-B1-01", 0.77, "I1"))
    s.append(Scenario("D04", "dev", "2026-10-02T01:15", "Unauthorized entry then attack",
        "P003, who is authorized only for utilities, is recognized in Hall A; six minutes later OpenSSH logs a break-in attempt on SRV-A1-02.")
        .face_unauthorized(0, "ZONE-A", "P003", "I1").ssh(6, "SRV-A1-02", "EXPLICIT_SECURITY_EVENT", "I1"))
    s.append(Scenario("D05", "dev", "2026-10-02T09:40", "Tailgater without PPE",
        "An unknown person follows staff into Hall B and is detected without a helmet a minute later.")
        .face_unknown(0, "ZONE-B", "I1").ppe(1, "ZONE-B", 0.81, "I1"))
    s.append(Scenario("D06", "dev", "2026-10-02T14:05", "Scanner noise and a missed vest",
        "A single-vote SSH anomaly from an internet scanner coincides with a low-confidence PPE alert for an authorized engineer.")
        .ssh(0, "SRV-A1-01", "ANOMALY_CANDIDATE").ppe(11, "ZONE-A", 0.58))
    s.append(Scenario("D07", "dev", "2026-10-03T03:20", "Wrong hall, worn drive",
        "A drive on SRV-B1-02 is wearing out; separately, P003 walks into Hall B by mistake 13 minutes later.")
        .maint(0, "SRV-B1-02", 0.91).face_unauthorized(13, "ZONE-B", "P003"))
    s.append(Scenario("D08", "dev", "2026-10-03T22:10", "Slow insider attack",
        "P003 is recognized in Hall B; 38 minutes later the SSH detector reaches consensus on SRV-B1-01 as the same person works from a console.")
        .face_unauthorized(0, "ZONE-B", "P003", "I1").ssh(38, "SRV-B1-01", "HIGH_CONFIDENCE_ANOMALY", "I1"))
    s.append(Scenario("D09", "dev", "2026-10-04T13:00", "Two incidents in one hall",
        "In Hall A a humidity fault stresses a drive, while at the same time an unauthorized visitor attempts a console break-in.")
        .env_sensor(0, "ZONE-A", "HIGH_HUMIDITY", "I1").maint(12, "SRV-A1-02", 0.74, "I1")
        .ssh(5, "SRV-A1-01", "EXPLICIT_SECURITY_EVENT", "I2").face_unauthorized(2, "ZONE-A", "P003", "I2"))
    s.append(Scenario("D10", "dev", "2026-10-05T07:45", "Smoke response",
        "Smoke is detected in utilities; a responder enters without full PPE seven minutes later.")
        .env_sensor(0, "ZONE-C", "SMOKE_DETECTED", "I1").ppe(7, "ZONE-C", 0.66, "I1"))
    s.append(Scenario("D11", "dev", "2026-10-05T16:00", "Quiet window with one real issue",
        "An isolated SSH candidate is internet noise. Seventy minutes later SRV-A1-01 runs hot and its drive is flagged two minutes after that.")
        .ssh(0, "SRV-B1-02", "ANOMALY_CANDIDATE").maint(72, "SRV-A1-01", 0.52, "I1")
        .env_hw(70, "SRV-A1-01", "HIGH_TEMPERATURE", "I1"))
    s.append(Scenario("D12", "dev", "2026-10-06T10:30", "Engineer dispatched",
        "A high-risk drive alert on SRV-B1-01 brings an engineer, who is seen without a vest 35 minutes later.")
        .maint(0, "SRV-B1-01", 0.88, "I1").ppe(35, "ZONE-B", 0.79, "I1"))
    s.append(Scenario("D13", "dev", "2026-10-06T23:50", "Cross-hall coincidence",
        "An internet brute-force attack reaches consensus on SRV-B1-02 while, unrelatedly, P003 strays into Hall A.")
        .ssh(0, "SRV-B1-02", "HIGH_CONFIDENCE_ANOMALY").face_unauthorized(3, "ZONE-A", "P003"))
    s.append(Scenario("D14", "dev", "2026-10-07T04:10", "Leak and drive",
        "A water leak sensor trips in Hall B; 16 minutes later a drive on SRV-B1-02 is flagged.")
        .env_sensor(0, "ZONE-B", "WATER_LEAK_DETECTED", "I1").maint(16, "SRV-B1-02", 0.71, "I1"))
    s.append(Scenario("D15", "dev", "2026-10-07T15:25", "Escorted visitor and scanner noise",
        "An escorted, unenrolled visitor appears in Hall A while an internet scanner triggers a single-vote SSH anomaly.")
        .face_unknown(0, "ZONE-A").ssh(8, "SRV-A1-01", "ANOMALY_CANDIDATE"))
    s.append(Scenario("D16", "dev", "2026-10-08T02:35", "Intruder without PPE attacks a server",
        "P003 enters Hall B without PPE and attempts a console break-in on SRV-B1-01.")
        .face_unauthorized(0, "ZONE-B", "P003", "I1").ppe(1, "ZONE-B", 0.83, "I1")
        .ssh(9, "SRV-B1-01", "EXPLICIT_SECURITY_EVENT", "I1"))

    # --------------------------------------------------------------- test
    s.append(Scenario("T01", "test", "2026-10-12T01:00", "Rack A1 overheating",
        "SRV-A1-01 overheats and its drive is flagged three minutes later; an unrelated SSH candidate appears in Hall B.")
        .env_hw(0, "SRV-A1-01", "HIGH_TEMPERATURE", "I1").maint(3, "SRV-A1-01", 0.79, "I1")
        .ssh(20, "SRV-B1-01", "ANOMALY_CANDIDATE"))
    s.append(Scenario("T02", "test", "2026-10-12T06:30", "Chiller degradation",
        "A cooling anomaly in utilities warms Hall A after 18 minutes; two Hall A drives are flagged around minute 52-55.")
        .env_sensor(0, "ZONE-C", "COOLING_ANOMALY", "I1").env_sensor(18, "ZONE-A", "HIGH_TEMPERATURE", "I1")
        .maint(52, "SRV-A1-02", 0.73, "I1").maint(55, "SRV-A1-01", 0.48, "I1"))
    s.append(Scenario("T03", "test", "2026-10-12T21:40", "Console attack",
        "P003 is recognized in Hall B and a break-in attempt is logged on SRV-B1-02 three minutes later.")
        .face_unauthorized(0, "ZONE-B", "P003", "I1").ssh(3, "SRV-B1-02", "EXPLICIT_SECURITY_EVENT", "I1"))
    s.append(Scenario("T04", "test", "2026-10-13T03:05", "Night-shift coincidence",
        "A Hall B drive is flagged at moderate risk; nine minutes later Hall A reports low humidity from dry outside air.")
        .maint(0, "SRV-B1-01", 0.62).env_sensor(9, "ZONE-A", "LOW_HUMIDITY"))
    s.append(Scenario("T05", "test", "2026-10-13T12:20", "Humidity and brute force",
        "Seasonal humidity rises in Hall B while an internet brute-force attack reaches consensus on SRV-B1-01.")
        .env_sensor(0, "ZONE-B", "HIGH_HUMIDITY").ssh(7, "SRV-B1-01", "HIGH_CONFIDENCE_ANOMALY"))
    s.append(Scenario("T06", "test", "2026-10-13T17:10", "Unenrolled contractor",
        "An unenrolled contractor enters utilities and is seen without PPE two minutes later.")
        .face_unknown(0, "ZONE-C", "I1").ppe(2, "ZONE-C", 0.72, "I1"))
    s.append(Scenario("T07", "test", "2026-10-14T08:00", "Engineer dispatched to Hall A",
        "A high-risk drive on SRV-A1-01 brings an engineer, seen without a vest 48 minutes later.")
        .maint(0, "SRV-A1-01", 0.84, "I1").ppe(48, "ZONE-A", 0.77, "I1"))
    s.append(Scenario("T08", "test", "2026-10-14T14:45", "Busy hall",
        "Hall A warms and a drive is flagged eight minutes later. A low-confidence PPE alert and an SSH candidate in the same window are unrelated.")
        .ppe(0, "ZONE-A", 0.61).env_sensor(6, "ZONE-A", "HIGH_TEMPERATURE", "I1")
        .maint(14, "SRV-A1-02", 0.81, "I1").ssh(10, "SRV-A1-01", "ANOMALY_CANDIDATE"))
    s.append(Scenario("T09", "test", "2026-10-15T02:15", "Slow cooling cascade",
        "Chiller airflow drops; a Hall B drive is flagged 33 minutes later. A low-confidence PPE alert in utilities is unrelated.")
        .env_sensor(0, "ZONE-C", "AIRFLOW_ANOMALY", "I1").maint(33, "SRV-B1-02", 0.76, "I1")
        .ppe(5, "ZONE-C", 0.55))
    s.append(Scenario("T10", "test", "2026-10-15T19:30", "Insider with delay",
        "P003 is recognized in Hall A and the SSH detector reaches consensus on SRV-A1-01 21 minutes later. A heat alert at minute 80 is unrelated.")
        .face_unauthorized(0, "ZONE-A", "P003", "I1").ssh(21, "SRV-A1-01", "HIGH_CONFIDENCE_ANOMALY", "I1")
        .env_sensor(80, "ZONE-A", "HIGH_TEMPERATURE"))
    s.append(Scenario("T11", "test", "2026-10-16T04:50", "Pure noise",
        "Three unrelated low-strength abnormalities in different places.")
        .ssh(0, "SRV-A1-02", "ANOMALY_CANDIDATE").ppe(4, "ZONE-B", 0.52).maint(30, "SRV-B1-01", 0.47))
    s.append(Scenario("T12", "test", "2026-10-16T11:10", "Fire response",
        "Smoke is detected in Hall A; a responder without full PPE and an unknown person (a fire officer) arrive within five minutes.")
        .env_sensor(0, "ZONE-A", "SMOKE_DETECTED", "I1").ppe(4, "ZONE-A", 0.88, "I1").face_unknown(5, "ZONE-A", "I1"))
    s.append(Scenario("T13", "test", "2026-10-16T23:00", "Same server, unrelated",
        "An internet break-in attempt targets SRV-A1-02 while the same server's old drive is independently flagged two minutes later.")
        .ssh(0, "SRV-A1-02", "EXPLICIT_SECURITY_EVENT").maint(2, "SRV-A1-02", 0.86))
    s.append(Scenario("T14", "test", "2026-10-17T07:35", "Tailgating into Hall B",
        "P003, authorized only for utilities, follows staff into Hall B and is seen without PPE a minute later.")
        .face_unauthorized(0, "ZONE-B", "P003", "I1").ppe(1, "ZONE-B", 0.69, "I1"))
    s.append(Scenario("T15", "test", "2026-10-17T13:55", "Delayed drive risk after heat",
        "Hall B overheats; two drives are flagged 27 and 29 minutes later.")
        .env_sensor(0, "ZONE-B", "HIGH_TEMPERATURE", "I1").maint(27, "SRV-B1-01", 0.72, "I1")
        .maint(29, "SRV-B1-02", 0.49, "I1"))
    s.append(Scenario("T16", "test", "2026-10-18T09:20", "Simultaneous incidents in two halls",
        "Hall A overheats and stresses a drive while, in Hall B, P003 attempts a console break-in.")
        .env_sensor(0, "ZONE-A", "HIGH_TEMPERATURE", "I1").maint(8, "SRV-A1-01", 0.75, "I1")
        .face_unauthorized(4, "ZONE-B", "P003", "I2").ssh(7, "SRV-B1-01", "EXPLICIT_SECURITY_EVENT", "I2"))
    s.append(Scenario("T17", "test", "2026-10-18T16:40", "Weak but real",
        "Hardware telemetry shows SRV-B1-02 running warm and its drive reaches moderate risk 11 minutes later.")
        .env_hw(0, "SRV-B1-02", "HIGH_TEMPERATURE", "I1").maint(11, "SRV-B1-02", 0.51, "I1"))
    s.append(Scenario("T18", "test", "2026-10-19T10:05", "Visitor and weak scan",
        "An unenrolled visitor is escorted through Hall B while an internet scanner causes a single-vote SSH anomaly.")
        .face_unknown(0, "ZONE-B").ssh(3, "SRV-B1-02", "ANOMALY_CANDIDATE"))
    s.append(Scenario("T19", "test", "2026-10-19T22:25", "Utilities intruder",
        "P001 is recognized in utilities without authorization and tampers with the chiller; a Hall A drive is flagged later.")
        .face_unauthorized(0, "ZONE-C", "P001", "I1").env_sensor(12, "ZONE-C", "COOLING_ANOMALY", "I1")
        .maint(58, "SRV-A1-01", 0.71, "I1"))
    s.append(Scenario("T20", "test", "2026-10-20T05:15", "Long gap, unrelated",
        "Hall A humidity rises; 95 minutes later a drive is flagged from long-term wear.")
        .env_sensor(0, "ZONE-A", "HIGH_HUMIDITY").maint(95, "SRV-A1-02", 0.79))
    s.append(Scenario("T21", "test", "2026-10-20T12:00", "Brute force with an on-site helper",
        "SSH consensus on SRV-A1-01, then an unknown person enters Hall A 44 minutes later to plug in a device.")
        .ssh(0, "SRV-A1-01", "HIGH_CONFIDENCE_ANOMALY", "I1").face_unknown(44, "ZONE-A", "I1"))
    s.append(Scenario("T22", "test", "2026-10-20T18:30", "Leak and responder",
        "A water leak in utilities brings an engineer without PPE nine minutes later; a moderate Hall B drive alert is unrelated.")
        .env_sensor(0, "ZONE-C", "WATER_LEAK_DETECTED", "I1").ppe(9, "ZONE-C", 0.80, "I1")
        .maint(15, "SRV-B1-01", 0.53))
    s.append(Scenario("T23", "test", "2026-10-21T03:40", "Multi-hall noise",
        "Three unrelated abnormalities across Halls A and B.")
        .ppe(0, "ZONE-A", 0.64).face_unknown(6, "ZONE-B").env_hw(10, "SRV-B1-01", "HIGH_TEMPERATURE"))
    s.append(Scenario("T24", "test", "2026-10-21T15:10", "Intrusion triple",
        "P003 enters Hall A without PPE and attempts a break-in on SRV-A1-02; an unrelated Hall B drive alert follows.")
        .face_unauthorized(0, "ZONE-A", "P003", "I1").ppe(1, "ZONE-A", 0.90, "I1")
        .ssh(4, "SRV-A1-02", "EXPLICIT_SECURITY_EVENT", "I1").maint(20, "SRV-B1-02", 0.66))
    return [x.data for x in s]


def main() -> None:
    data = {
        "scenario_set_version": "DCG-LABELLED-SCENARIOS-v1",
        "topology": "DC-01 (synthetic)",
        "labelling": "Ground truth written from each narrative by the scenario author. Events sharing a ground_truth_incident value belong to one incident; null marks unrelated background abnormalities.",
        "scenarios": scenarios(),
    }
    OUTPUT.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    counts = {split: sum(1 for x in data["scenarios"] if x["split"] == split) for split in ("dev", "test")}
    print(f"Wrote {OUTPUT.name}: {counts['dev']} dev + {counts['test']} test scenarios")


if __name__ == "__main__":
    main()
