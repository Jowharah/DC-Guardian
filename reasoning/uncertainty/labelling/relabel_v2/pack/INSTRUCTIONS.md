# Independent labelling — DC-Guardian scenarios

Thank you for labelling. Your labels are an **independent check** of a research result, so please:

1. **Work alone** and do not discuss the scenarios with the person who wrote them.
2. **Use only the files in this folder.** Do not open the DC-Guardian repository, its documents or results.
3. Judge each pair as an experienced data-center operator would. There is no trick; disagreement is useful data.

## The task

Each scenario is a 120-minute window in which several abnormal alerts fired. For **every row in `labels.csv`** decide whether the two events are **part of the same underlying incident**: one caused the other, both have the same cause, or both come from the same person or response. Two problems that merely happen at the same time and place are **not** related.

Fill in for each row:

- `related`: **Y** (same incident) or **N** (not the same incident).
- `confidence`: **1** guess · **2** fairly sure · **3** sure.
- `note` (optional): your reason, especially when unsure.

There are 20 rows in 8 scenarios; expect about 10–15 minutes. Each row of `labels.csv` shows both events in full, the minutes between them and the other alerts in the same scenario, so you can work in Excel alone; `scenarios_blind.md` shows each scenario as a whole if you prefer. **Make a copy of `labels.csv`, fill in the copy**, save it as CSV (keep the columns) and send it back.

## The facility (synthetic data center DC-01)

**ZONE-A — Server Hall A**
- Rack RACK-A1: servers SRV-A1-01, SRV-A1-02
- Server Hall A Camera (CAM-A-01)
- Server Hall A Environmental Sensor (SEN-A-01)

**ZONE-B — Server Hall B**
- Rack RACK-B1: servers SRV-B1-01, SRV-B1-02
- Server Hall B Camera (CAM-B-01)
- Server Hall B Environmental Sensor (SEN-B-01)

**ZONE-C — Cooling and Utilities**
- Utilities Camera (CAM-C-01)
- Cooling Environmental Sensor (SEN-C-01)
- Primary Cooling Unit (CHILLER-C1)

- Cooling: CHILLER-C1 in ZONE-C cools ZONE-A and ZONE-B.

Staff and their authorized zones:

- P001 (system administrator): ZONE-A, ZONE-B
- P002 (data center technician): ZONE-A, ZONE-B, ZONE-C
- P003 (maintenance engineer): ZONE-C

## What the alerts mean

- **ENVIRONMENTAL:** Environmental sensor or hardware telemetry measuring temperature and humidity; the reading is shown. States: HIGH_TEMPERATURE (above 35 °C), HIGH_HUMIDITY (above 80 %), LOW_HUMIDITY (below 20 %). Source ENVIRONMENTAL_SENSOR is a dedicated room sensor; HARDWARE_TELEMETRY comes from a server's own sensors.
- **MAINTENANCE:** Hard-drive failure-risk model (SMART data). AT_RISK = predicted failure within seven days; failure_probability is the model score (alert threshold 0.45; most alerts are false alarms).
- **CYBERSECURITY:** SSH login anomaly detector on a server. EXPLICIT_SECURITY_EVENT = the log itself shows a security event (e.g. break-in attempt); HIGH_CONFIDENCE_ANOMALY = several detectors agree; ANOMALY_CANDIDATE = only one detector flagged it (weaker).
- **PHYSICAL_SECURITY:** Camera face recognition. UNKNOWN_PERSON = face not enrolled (visitor or stranger); authorization UNAUTHORIZED = a recognized person who is not authorized for that zone.
- **SAFETY:** Camera PPE detection. PPE_NON_COMPLIANT = a person without detected helmet or safety vest; confidence is the detector's confidence (the detector misses about half of PPE items, so low confidence is weak evidence).
