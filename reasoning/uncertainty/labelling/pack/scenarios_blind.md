# Scenarios (blind)

Times are minutes from the first alert in the scenario.

### Scenario S01

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| S01-E1 | +0 min (04:10) | ENVIRONMENTAL | WATER_LEAK_DETECTED | zone: ZONE-B · sensor: SEN-B-01 · source class: ENVIRONMENTAL_SENSOR |
| S01-E2 | +16 min (04:26) | MAINTENANCE | AT_RISK | zone: ZONE-B · rack: RACK-B1 · server: SRV-B1-02 · failure probability: 0.71 |

### Scenario S02

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| S02-E1 | +0 min (16:40) | ENVIRONMENTAL | HIGH_TEMPERATURE | zone: ZONE-B · rack: RACK-B1 · server: SRV-B1-02 · source class: HARDWARE_TELEMETRY |
| S02-E2 | +11 min (16:51) | MAINTENANCE | AT_RISK | zone: ZONE-B · rack: RACK-B1 · server: SRV-B1-02 · failure probability: 0.51 |

### Scenario S03

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| S03-E1 | +0 min (18:30) | ENVIRONMENTAL | WATER_LEAK_DETECTED | zone: ZONE-C · sensor: SEN-C-01 · source class: ENVIRONMENTAL_SENSOR |
| S03-E2 | +9 min (18:39) | SAFETY | PPE_NON_COMPLIANT | zone: ZONE-C · camera: CAM-C-01 · confidence: 0.8 |
| S03-E3 | +15 min (18:45) | MAINTENANCE | AT_RISK | zone: ZONE-B · rack: RACK-B1 · server: SRV-B1-01 · failure probability: 0.53 |

### Scenario S04

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| S04-E1 | +0 min (22:10) | PHYSICAL_SECURITY | RECOGNIZED | zone: ZONE-B · camera: CAM-B-01 · authorization: UNAUTHORIZED · person: P003 |
| S04-E2 | +38 min (22:48) | CYBERSECURITY | HIGH_CONFIDENCE_ANOMALY | zone: ZONE-B · rack: RACK-B1 · server: SRV-B1-01 |

### Scenario S05

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| S05-E1 | +0 min (01:15) | PHYSICAL_SECURITY | RECOGNIZED | zone: ZONE-A · camera: CAM-A-01 · authorization: UNAUTHORIZED · person: P003 |
| S05-E2 | +6 min (01:21) | CYBERSECURITY | EXPLICIT_SECURITY_EVENT | zone: ZONE-A · rack: RACK-A1 · server: SRV-A1-02 |

### Scenario S06

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| S06-E1 | +0 min (10:30) | MAINTENANCE | AT_RISK | zone: ZONE-B · rack: RACK-B1 · server: SRV-B1-01 · failure probability: 0.88 |
| S06-E2 | +35 min (11:05) | SAFETY | PPE_NON_COMPLIANT | zone: ZONE-B · camera: CAM-B-01 · confidence: 0.79 |

### Scenario S07

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| S07-E1 | +0 min (06:30) | ENVIRONMENTAL | COOLING_ANOMALY | zone: ZONE-C · sensor: SEN-C-01 · source class: ENVIRONMENTAL_SENSOR |
| S07-E2 | +18 min (06:48) | ENVIRONMENTAL | HIGH_TEMPERATURE | zone: ZONE-A · sensor: SEN-A-01 · source class: ENVIRONMENTAL_SENSOR |
| S07-E3 | +52 min (07:22) | MAINTENANCE | AT_RISK | zone: ZONE-A · rack: RACK-A1 · server: SRV-A1-02 · failure probability: 0.73 |
| S07-E4 | +55 min (07:25) | MAINTENANCE | AT_RISK | zone: ZONE-A · rack: RACK-A1 · server: SRV-A1-01 · failure probability: 0.48 |

### Scenario S08

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| S08-E1 | +0 min (03:20) | MAINTENANCE | AT_RISK | zone: ZONE-B · rack: RACK-B1 · server: SRV-B1-02 · failure probability: 0.91 |
| S08-E2 | +13 min (03:33) | PHYSICAL_SECURITY | RECOGNIZED | zone: ZONE-B · camera: CAM-B-01 · authorization: UNAUTHORIZED · person: P003 |

### Scenario S09

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| S09-E1 | +0 min (12:00) | CYBERSECURITY | HIGH_CONFIDENCE_ANOMALY | zone: ZONE-A · rack: RACK-A1 · server: SRV-A1-01 |
| S09-E2 | +44 min (12:44) | PHYSICAL_SECURITY | UNKNOWN_PERSON | zone: ZONE-A · camera: CAM-A-01 |

### Scenario S10

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| S10-E1 | +0 min (04:50) | CYBERSECURITY | ANOMALY_CANDIDATE | zone: ZONE-A · rack: RACK-A1 · server: SRV-A1-02 |
| S10-E2 | +4 min (04:54) | SAFETY | PPE_NON_COMPLIANT | zone: ZONE-B · camera: CAM-B-01 · confidence: 0.52 |
| S10-E3 | +30 min (05:20) | MAINTENANCE | AT_RISK | zone: ZONE-B · rack: RACK-B1 · server: SRV-B1-01 · failure probability: 0.47 |

### Scenario S11

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| S11-E1 | +0 min (05:15) | ENVIRONMENTAL | HIGH_HUMIDITY | zone: ZONE-A · sensor: SEN-A-01 · source class: ENVIRONMENTAL_SENSOR |
| S11-E2 | +95 min (06:50) | MAINTENANCE | AT_RISK | zone: ZONE-A · rack: RACK-A1 · server: SRV-A1-02 · failure probability: 0.79 |

### Scenario S12

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| S12-E1 | +0 min (03:05) | MAINTENANCE | AT_RISK | zone: ZONE-B · rack: RACK-B1 · server: SRV-B1-01 · failure probability: 0.62 |
| S12-E2 | +9 min (03:14) | ENVIRONMENTAL | LOW_HUMIDITY | zone: ZONE-A · sensor: SEN-A-01 · source class: ENVIRONMENTAL_SENSOR |

### Scenario S13

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| S13-E1 | +0 min (23:50) | CYBERSECURITY | HIGH_CONFIDENCE_ANOMALY | zone: ZONE-B · rack: RACK-B1 · server: SRV-B1-02 |
| S13-E2 | +3 min (23:53) | PHYSICAL_SECURITY | RECOGNIZED | zone: ZONE-A · camera: CAM-A-01 · authorization: UNAUTHORIZED · person: P003 |

### Scenario S14

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| S14-E1 | +0 min (08:00) | MAINTENANCE | AT_RISK | zone: ZONE-A · rack: RACK-A1 · server: SRV-A1-01 · failure probability: 0.84 |
| S14-E2 | +48 min (08:48) | SAFETY | PPE_NON_COMPLIANT | zone: ZONE-A · camera: CAM-A-01 · confidence: 0.77 |

### Scenario S15

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| S15-E1 | +0 min (15:10) | PHYSICAL_SECURITY | RECOGNIZED | zone: ZONE-A · camera: CAM-A-01 · authorization: UNAUTHORIZED · person: P003 |
| S15-E2 | +1 min (15:11) | SAFETY | PPE_NON_COMPLIANT | zone: ZONE-A · camera: CAM-A-01 · confidence: 0.9 |
| S15-E3 | +4 min (15:14) | CYBERSECURITY | EXPLICIT_SECURITY_EVENT | zone: ZONE-A · rack: RACK-A1 · server: SRV-A1-02 |
| S15-E4 | +20 min (15:30) | MAINTENANCE | AT_RISK | zone: ZONE-B · rack: RACK-B1 · server: SRV-B1-02 · failure probability: 0.66 |

### Scenario S16

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| S16-E1 | +0 min (14:45) | SAFETY | PPE_NON_COMPLIANT | zone: ZONE-A · camera: CAM-A-01 · confidence: 0.61 |
| S16-E2 | +6 min (14:51) | ENVIRONMENTAL | HIGH_TEMPERATURE | zone: ZONE-A · sensor: SEN-A-01 · source class: ENVIRONMENTAL_SENSOR |
| S16-E3 | +10 min (14:55) | CYBERSECURITY | ANOMALY_CANDIDATE | zone: ZONE-A · rack: RACK-A1 · server: SRV-A1-01 |
| S16-E4 | +14 min (14:59) | MAINTENANCE | AT_RISK | zone: ZONE-A · rack: RACK-A1 · server: SRV-A1-02 · failure probability: 0.81 |

### Scenario S17

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| S17-E1 | +0 min (23:00) | CYBERSECURITY | EXPLICIT_SECURITY_EVENT | zone: ZONE-A · rack: RACK-A1 · server: SRV-A1-02 |
| S17-E2 | +2 min (23:02) | MAINTENANCE | AT_RISK | zone: ZONE-A · rack: RACK-A1 · server: SRV-A1-02 · failure probability: 0.86 |

### Scenario S18

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| S18-E1 | +0 min (02:15) | ENVIRONMENTAL | AIRFLOW_ANOMALY | zone: ZONE-C · sensor: SEN-C-01 · source class: ENVIRONMENTAL_SENSOR |
| S18-E2 | +5 min (02:20) | SAFETY | PPE_NON_COMPLIANT | zone: ZONE-C · camera: CAM-C-01 · confidence: 0.55 |
| S18-E3 | +33 min (02:48) | MAINTENANCE | AT_RISK | zone: ZONE-B · rack: RACK-B1 · server: SRV-B1-02 · failure probability: 0.76 |

### Scenario S19

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| S19-E1 | +0 min (10:05) | PHYSICAL_SECURITY | UNKNOWN_PERSON | zone: ZONE-B · camera: CAM-B-01 |
| S19-E2 | +3 min (10:08) | CYBERSECURITY | ANOMALY_CANDIDATE | zone: ZONE-B · rack: RACK-B1 · server: SRV-B1-02 |

### Scenario S20

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| S20-E1 | +0 min (02:00) | ENVIRONMENTAL | HIGH_TEMPERATURE | zone: ZONE-A · sensor: SEN-A-01 · source class: ENVIRONMENTAL_SENSOR |
| S20-E2 | +9 min (02:09) | MAINTENANCE | AT_RISK | zone: ZONE-A · rack: RACK-A1 · server: SRV-A1-01 · failure probability: 0.82 |

### Scenario S21

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| S21-E1 | +0 min (19:30) | PHYSICAL_SECURITY | RECOGNIZED | zone: ZONE-A · camera: CAM-A-01 · authorization: UNAUTHORIZED · person: P003 |
| S21-E2 | +21 min (19:51) | CYBERSECURITY | HIGH_CONFIDENCE_ANOMALY | zone: ZONE-A · rack: RACK-A1 · server: SRV-A1-01 |
| S21-E3 | +80 min (20:50) | ENVIRONMENTAL | HIGH_TEMPERATURE | zone: ZONE-A · sensor: SEN-A-01 · source class: ENVIRONMENTAL_SENSOR |

### Scenario S22

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| S22-E1 | +0 min (11:10) | ENVIRONMENTAL | SMOKE_DETECTED | zone: ZONE-A · sensor: SEN-A-01 · source class: ENVIRONMENTAL_SENSOR |
| S22-E2 | +4 min (11:14) | SAFETY | PPE_NON_COMPLIANT | zone: ZONE-A · camera: CAM-A-01 · confidence: 0.88 |
| S22-E3 | +5 min (11:15) | PHYSICAL_SECURITY | UNKNOWN_PERSON | zone: ZONE-A · camera: CAM-A-01 |

### Scenario S23

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| S23-E1 | +0 min (21:40) | PHYSICAL_SECURITY | RECOGNIZED | zone: ZONE-B · camera: CAM-B-01 · authorization: UNAUTHORIZED · person: P003 |
| S23-E2 | +3 min (21:43) | CYBERSECURITY | EXPLICIT_SECURITY_EVENT | zone: ZONE-B · rack: RACK-B1 · server: SRV-B1-02 |

### Scenario S24

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| S24-E1 | +0 min (13:00) | ENVIRONMENTAL | HIGH_HUMIDITY | zone: ZONE-A · sensor: SEN-A-01 · source class: ENVIRONMENTAL_SENSOR |
| S24-E2 | +2 min (13:02) | PHYSICAL_SECURITY | RECOGNIZED | zone: ZONE-A · camera: CAM-A-01 · authorization: UNAUTHORIZED · person: P003 |
| S24-E3 | +5 min (13:05) | CYBERSECURITY | EXPLICIT_SECURITY_EVENT | zone: ZONE-A · rack: RACK-A1 · server: SRV-A1-01 |
| S24-E4 | +12 min (13:12) | MAINTENANCE | AT_RISK | zone: ZONE-A · rack: RACK-A1 · server: SRV-A1-02 · failure probability: 0.74 |

### Scenario S25

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| S25-E1 | +0 min (02:35) | PHYSICAL_SECURITY | RECOGNIZED | zone: ZONE-B · camera: CAM-B-01 · authorization: UNAUTHORIZED · person: P003 |
| S25-E2 | +1 min (02:36) | SAFETY | PPE_NON_COMPLIANT | zone: ZONE-B · camera: CAM-B-01 · confidence: 0.83 |
| S25-E3 | +9 min (02:44) | CYBERSECURITY | EXPLICIT_SECURITY_EVENT | zone: ZONE-B · rack: RACK-B1 · server: SRV-B1-01 |

### Scenario S26

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| S26-E1 | +0 min (09:20) | ENVIRONMENTAL | HIGH_TEMPERATURE | zone: ZONE-A · sensor: SEN-A-01 · source class: ENVIRONMENTAL_SENSOR |
| S26-E2 | +4 min (09:24) | PHYSICAL_SECURITY | RECOGNIZED | zone: ZONE-B · camera: CAM-B-01 · authorization: UNAUTHORIZED · person: P003 |
| S26-E3 | +7 min (09:27) | CYBERSECURITY | EXPLICIT_SECURITY_EVENT | zone: ZONE-B · rack: RACK-B1 · server: SRV-B1-01 |
| S26-E4 | +8 min (09:28) | MAINTENANCE | AT_RISK | zone: ZONE-A · rack: RACK-A1 · server: SRV-A1-01 · failure probability: 0.75 |

### Scenario S27

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| S27-E1 | +0 min (14:05) | CYBERSECURITY | ANOMALY_CANDIDATE | zone: ZONE-A · rack: RACK-A1 · server: SRV-A1-01 |
| S27-E2 | +11 min (14:16) | SAFETY | PPE_NON_COMPLIANT | zone: ZONE-A · camera: CAM-A-01 · confidence: 0.58 |

### Scenario S28

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| S28-E1 | +0 min (07:45) | ENVIRONMENTAL | SMOKE_DETECTED | zone: ZONE-C · sensor: SEN-C-01 · source class: ENVIRONMENTAL_SENSOR |
| S28-E2 | +7 min (07:52) | SAFETY | PPE_NON_COMPLIANT | zone: ZONE-C · camera: CAM-C-01 · confidence: 0.66 |

### Scenario S29

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| S29-E1 | +0 min (13:55) | ENVIRONMENTAL | HIGH_TEMPERATURE | zone: ZONE-B · sensor: SEN-B-01 · source class: ENVIRONMENTAL_SENSOR |
| S29-E2 | +27 min (14:22) | MAINTENANCE | AT_RISK | zone: ZONE-B · rack: RACK-B1 · server: SRV-B1-01 · failure probability: 0.72 |
| S29-E3 | +29 min (14:24) | MAINTENANCE | AT_RISK | zone: ZONE-B · rack: RACK-B1 · server: SRV-B1-02 · failure probability: 0.49 |

### Scenario S30

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| S30-E1 | +0 min (22:25) | PHYSICAL_SECURITY | RECOGNIZED | zone: ZONE-C · camera: CAM-C-01 · authorization: UNAUTHORIZED · person: P001 |
| S30-E2 | +12 min (22:37) | ENVIRONMENTAL | COOLING_ANOMALY | zone: ZONE-C · sensor: SEN-C-01 · source class: ENVIRONMENTAL_SENSOR |
| S30-E3 | +58 min (23:23) | MAINTENANCE | AT_RISK | zone: ZONE-A · rack: RACK-A1 · server: SRV-A1-01 · failure probability: 0.71 |

### Scenario S31

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| S31-E1 | +0 min (09:40) | PHYSICAL_SECURITY | UNKNOWN_PERSON | zone: ZONE-B · camera: CAM-B-01 |
| S31-E2 | +1 min (09:41) | SAFETY | PPE_NON_COMPLIANT | zone: ZONE-B · camera: CAM-B-01 · confidence: 0.81 |

### Scenario S32

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| S32-E1 | +0 min (16:00) | CYBERSECURITY | ANOMALY_CANDIDATE | zone: ZONE-B · rack: RACK-B1 · server: SRV-B1-02 |
| S32-E2 | +70 min (17:10) | ENVIRONMENTAL | HIGH_TEMPERATURE | zone: ZONE-A · rack: RACK-A1 · server: SRV-A1-01 · source class: HARDWARE_TELEMETRY |
| S32-E3 | +72 min (17:12) | MAINTENANCE | AT_RISK | zone: ZONE-A · rack: RACK-A1 · server: SRV-A1-01 · failure probability: 0.52 |

### Scenario S33

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| S33-E1 | +0 min (03:40) | SAFETY | PPE_NON_COMPLIANT | zone: ZONE-A · camera: CAM-A-01 · confidence: 0.64 |
| S33-E2 | +6 min (03:46) | PHYSICAL_SECURITY | UNKNOWN_PERSON | zone: ZONE-B · camera: CAM-B-01 |
| S33-E3 | +10 min (03:50) | ENVIRONMENTAL | HIGH_TEMPERATURE | zone: ZONE-B · rack: RACK-B1 · server: SRV-B1-01 · source class: HARDWARE_TELEMETRY |

### Scenario S34

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| S34-E1 | +0 min (07:35) | PHYSICAL_SECURITY | RECOGNIZED | zone: ZONE-B · camera: CAM-B-01 · authorization: UNAUTHORIZED · person: P003 |
| S34-E2 | +1 min (07:36) | SAFETY | PPE_NON_COMPLIANT | zone: ZONE-B · camera: CAM-B-01 · confidence: 0.69 |

### Scenario S35

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| S35-E1 | +0 min (12:20) | ENVIRONMENTAL | HIGH_HUMIDITY | zone: ZONE-B · sensor: SEN-B-01 · source class: ENVIRONMENTAL_SENSOR |
| S35-E2 | +7 min (12:27) | CYBERSECURITY | HIGH_CONFIDENCE_ANOMALY | zone: ZONE-B · rack: RACK-B1 · server: SRV-B1-01 |

### Scenario S36

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| S36-E1 | +0 min (01:00) | ENVIRONMENTAL | HIGH_TEMPERATURE | zone: ZONE-A · rack: RACK-A1 · server: SRV-A1-01 · source class: HARDWARE_TELEMETRY |
| S36-E2 | +3 min (01:03) | MAINTENANCE | AT_RISK | zone: ZONE-A · rack: RACK-A1 · server: SRV-A1-01 · failure probability: 0.79 |
| S36-E3 | +20 min (01:20) | CYBERSECURITY | ANOMALY_CANDIDATE | zone: ZONE-B · rack: RACK-B1 · server: SRV-B1-01 |

### Scenario S37

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| S37-E1 | +0 min (05:30) | ENVIRONMENTAL | HIGH_TEMPERATURE | zone: ZONE-B · rack: RACK-B1 · server: SRV-B1-02 · source class: HARDWARE_TELEMETRY |
| S37-E2 | +4 min (05:34) | MAINTENANCE | AT_RISK | zone: ZONE-B · rack: RACK-B1 · server: SRV-B1-02 · failure probability: 0.55 |

### Scenario S38

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| S38-E1 | +0 min (15:25) | PHYSICAL_SECURITY | UNKNOWN_PERSON | zone: ZONE-A · camera: CAM-A-01 |
| S38-E2 | +8 min (15:33) | CYBERSECURITY | ANOMALY_CANDIDATE | zone: ZONE-A · rack: RACK-A1 · server: SRV-A1-01 |

### Scenario S39

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| S39-E1 | +0 min (17:10) | PHYSICAL_SECURITY | UNKNOWN_PERSON | zone: ZONE-C · camera: CAM-C-01 |
| S39-E2 | +2 min (17:12) | SAFETY | PPE_NON_COMPLIANT | zone: ZONE-C · camera: CAM-C-01 · confidence: 0.72 |

### Scenario S40

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| S40-E1 | +0 min (11:00) | ENVIRONMENTAL | AIRFLOW_ANOMALY | zone: ZONE-C · sensor: SEN-C-01 · source class: ENVIRONMENTAL_SENSOR |
| S40-E2 | +22 min (11:22) | ENVIRONMENTAL | HIGH_TEMPERATURE | zone: ZONE-B · sensor: SEN-B-01 · source class: ENVIRONMENTAL_SENSOR |
| S40-E3 | +41 min (11:41) | MAINTENANCE | AT_RISK | zone: ZONE-B · rack: RACK-B1 · server: SRV-B1-01 · failure probability: 0.77 |
