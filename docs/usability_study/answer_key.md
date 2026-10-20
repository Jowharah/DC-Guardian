# Answer key (facilitator only; never show to participants)

Fill in during the pilot run, for the exact data prepared for the sessions. A task counts as **success (1)** when every point in the "Success requires" column is met without help, **partial (0.5)** with help or one wrong detail, and **failure (0)** otherwise.

| Task | Where in the dashboard | Correct answer (fill in) | Success requires |
|---|---|---|---|
| T1 | Monitoring Center summary cards and domain strip | Items needing attention: ___ · Domain with most abnormal results: ___ | Both values |
| T2 | Monitoring Center, correlated groups (severity shown) | Group ___ · severity ___ · domains ___ | Severity and every domain |
| T3 | Group detail (members, graph, linkage) | Linked by: same zone ___ / time ___ / known mechanism ___ | States the shared context, and that it is not proof of cause |
| T4 | PPE observation → Human verdict (Confirm / Override / Inconclusive, rationale of at least 15 characters) | Observation ___ | A verdict saved, with a rationale |
| T5 | Group detail → Investigation state: Start review → Resolve (resolution: No finding / False positive / Handled outside system / Duplicate; reason of at least 15 characters; acknowledgement ticked) | Either group (both start OPEN) | State ends RESOLVED with a reason; any resolution counts. Note which one they chose and why, and whether the acknowledgement box or the 15-character minimum held them up |
| T6 | Human Review Queue → item → Open Monitoring Center | Any pending item | Reaches the item's detail |
| T7 | Analytics Dashboard → Evidence by zone | Zone ___ | The correct zone |
| T8 | AI Investigator (opt-in) | n/a | Asks the question and gives a reasoned trust judgement |
| T9 | Scenario Lab → PPE image validation (`camera_snapshot.jpg`, ZONE-B) | Status ___ (COMPLIANT / NON_COMPLIANT / NO_PERSON) | States the status, and that "not detected" is not proof of absence |
| T10 | Scenario Lab → environmental sensor validation (`sensor_readings.csv`, SEN-B-01, ZONE-B), then the Monitoring Center | HIGH_TEMPERATURE: readings exceed 35 °C from 13:08 | Uploads the file, finds the new environmental result, and states it is a high temperature |

## Fixed answers for the study data

`prepare_study_data.py` rebuilds the same data before every session, so these answers hold for every participant. Group IDs change each time, so identify groups by zone and domains, not by ID.
- **T2:** the HIGH group in **ZONE-A**: cybersecurity (SSH, high-confidence anomaly) + physical security (unauthorized face) + safety (PPE non-compliant).
- **Second group:** MEDIUM, in ZONE-B: environmental, maintenance, physical security and safety.
- **T4:** any of the three PPE results (two in ZONE-B, one in ZONE-A); none has a verdict.
- **T5:** either group; both start OPEN.
- **T6:** both groups await their first human review.
- **T7:** **ZONE-B**, with 7 evidence records against 3 in ZONE-A (check the Analytics view agrees in the dry run).
