# Scenarios (blind)

Times are minutes from the first alert in the scenario.

### Scenario V01

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| V01-E1 | +0 min (03:40) | SAFETY | PPE_NON_COMPLIANT | zone: ZONE-A · camera: CAM-A-01 · confidence: 0.64 |
| V01-E2 | +6 min (03:46) | PHYSICAL_SECURITY | UNKNOWN_PERSON | zone: ZONE-B · camera: CAM-B-01 |
| V01-E3 | +10 min (03:50) | ENVIRONMENTAL | HIGH_TEMPERATURE | zone: ZONE-B · rack: RACK-B1 · server: SRV-B1-01 · source class: HARDWARE_TELEMETRY · temperature: 41.2 °C · humidity: 40.0 % |

### Scenario V02

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| V02-E1 | +0 min (11:00) | ENVIRONMENTAL | HIGH_TEMPERATURE | zone: ZONE-C · sensor: SEN-C-01 · source class: ENVIRONMENTAL_SENSOR · temperature: 37.5 °C · humidity: 38.0 % |
| V02-E2 | +22 min (11:22) | ENVIRONMENTAL | HIGH_TEMPERATURE | zone: ZONE-B · sensor: SEN-B-01 · source class: ENVIRONMENTAL_SENSOR · temperature: 36.4 °C · humidity: 46.0 % |
| V02-E3 | +41 min (11:41) | MAINTENANCE | AT_RISK | zone: ZONE-B · rack: RACK-B1 · server: SRV-B1-01 · failure probability: 0.77 |

### Scenario V03

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| V03-E1 | +0 min (14:45) | SAFETY | PPE_NON_COMPLIANT | zone: ZONE-A · camera: CAM-A-01 · confidence: 0.61 |
| V03-E2 | +6 min (14:51) | ENVIRONMENTAL | HIGH_TEMPERATURE | zone: ZONE-A · sensor: SEN-A-01 · source class: ENVIRONMENTAL_SENSOR · temperature: 37.8 °C · humidity: 43.0 % |
| V03-E3 | +10 min (14:55) | CYBERSECURITY | ANOMALY_CANDIDATE | zone: ZONE-A · rack: RACK-A1 · server: SRV-A1-01 |
| V03-E4 | +14 min (14:59) | MAINTENANCE | AT_RISK | zone: ZONE-A · rack: RACK-A1 · server: SRV-A1-02 · failure probability: 0.81 |

### Scenario V04

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| V04-E1 | +0 min (15:10) | PHYSICAL_SECURITY | RECOGNIZED | zone: ZONE-A · camera: CAM-A-01 · authorization: UNAUTHORIZED · person: P003 |
| V04-E2 | +1 min (15:11) | SAFETY | PPE_NON_COMPLIANT | zone: ZONE-A · camera: CAM-A-01 · confidence: 0.9 |
| V04-E3 | +4 min (15:14) | CYBERSECURITY | EXPLICIT_SECURITY_EVENT | zone: ZONE-A · rack: RACK-A1 · server: SRV-A1-02 |
| V04-E4 | +20 min (15:30) | MAINTENANCE | AT_RISK | zone: ZONE-B · rack: RACK-B1 · server: SRV-B1-02 · failure probability: 0.66 |

### Scenario V05

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| V05-E1 | +0 min (02:35) | PHYSICAL_SECURITY | RECOGNIZED | zone: ZONE-B · camera: CAM-B-01 · authorization: UNAUTHORIZED · person: P003 |
| V05-E2 | +1 min (02:36) | SAFETY | PPE_NON_COMPLIANT | zone: ZONE-B · camera: CAM-B-01 · confidence: 0.83 |
| V05-E3 | +9 min (02:44) | CYBERSECURITY | EXPLICIT_SECURITY_EVENT | zone: ZONE-B · rack: RACK-B1 · server: SRV-B1-01 |

### Scenario V06

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| V06-E1 | +0 min (02:00) | ENVIRONMENTAL | HIGH_TEMPERATURE | zone: ZONE-A · sensor: SEN-A-01 · source class: ENVIRONMENTAL_SENSOR · temperature: 37.2 °C · humidity: 44.0 % |
| V06-E2 | +9 min (02:09) | MAINTENANCE | AT_RISK | zone: ZONE-A · rack: RACK-A1 · server: SRV-A1-01 · failure probability: 0.82 |

### Scenario V07

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| V07-E1 | +0 min (09:20) | ENVIRONMENTAL | HIGH_TEMPERATURE | zone: ZONE-A · sensor: SEN-A-01 · source class: ENVIRONMENTAL_SENSOR · temperature: 37.0 °C · humidity: 44.0 % |
| V07-E2 | +4 min (09:24) | PHYSICAL_SECURITY | RECOGNIZED | zone: ZONE-B · camera: CAM-B-01 · authorization: UNAUTHORIZED · person: P003 |
| V07-E3 | +7 min (09:27) | CYBERSECURITY | EXPLICIT_SECURITY_EVENT | zone: ZONE-B · rack: RACK-B1 · server: SRV-B1-01 |
| V07-E4 | +8 min (09:28) | MAINTENANCE | AT_RISK | zone: ZONE-A · rack: RACK-A1 · server: SRV-A1-01 · failure probability: 0.75 |

### Scenario V08

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| V08-E1 | +0 min (14:05) | CYBERSECURITY | ANOMALY_CANDIDATE | zone: ZONE-A · rack: RACK-A1 · server: SRV-A1-01 |
| V08-E2 | +11 min (14:16) | SAFETY | PPE_NON_COMPLIANT | zone: ZONE-A · camera: CAM-A-01 · confidence: 0.58 |

### Scenario V09

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| V09-E1 | +0 min (05:15) | ENVIRONMENTAL | HIGH_HUMIDITY | zone: ZONE-A · sensor: SEN-A-01 · source class: ENVIRONMENTAL_SENSOR · temperature: 23.8 °C · humidity: 84.0 % |
| V09-E2 | +95 min (06:50) | MAINTENANCE | AT_RISK | zone: ZONE-A · rack: RACK-A1 · server: SRV-A1-02 · failure probability: 0.79 |

### Scenario V10

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| V10-E1 | +0 min (01:15) | PHYSICAL_SECURITY | RECOGNIZED | zone: ZONE-A · camera: CAM-A-01 · authorization: UNAUTHORIZED · person: P003 |
| V10-E2 | +6 min (01:21) | CYBERSECURITY | EXPLICIT_SECURITY_EVENT | zone: ZONE-A · rack: RACK-A1 · server: SRV-A1-02 |

### Scenario V11

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| V11-E1 | +0 min (04:50) | CYBERSECURITY | ANOMALY_CANDIDATE | zone: ZONE-A · rack: RACK-A1 · server: SRV-A1-02 |
| V11-E2 | +4 min (04:54) | SAFETY | PPE_NON_COMPLIANT | zone: ZONE-B · camera: CAM-B-01 · confidence: 0.52 |
| V11-E3 | +30 min (05:20) | MAINTENANCE | AT_RISK | zone: ZONE-B · rack: RACK-B1 · server: SRV-B1-01 · failure probability: 0.47 |

### Scenario V12

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| V12-E1 | +0 min (03:20) | MAINTENANCE | AT_RISK | zone: ZONE-B · rack: RACK-B1 · server: SRV-B1-02 · failure probability: 0.91 |
| V12-E2 | +13 min (03:33) | PHYSICAL_SECURITY | RECOGNIZED | zone: ZONE-B · camera: CAM-B-01 · authorization: UNAUTHORIZED · person: P003 |

### Scenario V13

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| V13-E1 | +0 min (03:05) | MAINTENANCE | AT_RISK | zone: ZONE-B · rack: RACK-B1 · server: SRV-B1-01 · failure probability: 0.62 |
| V13-E2 | +9 min (03:14) | ENVIRONMENTAL | LOW_HUMIDITY | zone: ZONE-A · sensor: SEN-A-01 · source class: ENVIRONMENTAL_SENSOR · temperature: 23.0 °C · humidity: 16.0 % |

### Scenario V14

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| V14-E1 | +0 min (07:35) | PHYSICAL_SECURITY | RECOGNIZED | zone: ZONE-B · camera: CAM-B-01 · authorization: UNAUTHORIZED · person: P003 |
| V14-E2 | +1 min (07:36) | SAFETY | PPE_NON_COMPLIANT | zone: ZONE-B · camera: CAM-B-01 · confidence: 0.69 |

### Scenario V15

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| V15-E1 | +0 min (23:00) | CYBERSECURITY | EXPLICIT_SECURITY_EVENT | zone: ZONE-A · rack: RACK-A1 · server: SRV-A1-02 |
| V15-E2 | +2 min (23:02) | MAINTENANCE | AT_RISK | zone: ZONE-A · rack: RACK-A1 · server: SRV-A1-02 · failure probability: 0.86 |

### Scenario V16

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| V16-E1 | +0 min (21:40) | PHYSICAL_SECURITY | RECOGNIZED | zone: ZONE-B · camera: CAM-B-01 · authorization: UNAUTHORIZED · person: P003 |
| V16-E2 | +3 min (21:43) | CYBERSECURITY | EXPLICIT_SECURITY_EVENT | zone: ZONE-B · rack: RACK-B1 · server: SRV-B1-02 |

### Scenario V17

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| V17-E1 | +0 min (23:50) | CYBERSECURITY | HIGH_CONFIDENCE_ANOMALY | zone: ZONE-B · rack: RACK-B1 · server: SRV-B1-02 |
| V17-E2 | +3 min (23:53) | PHYSICAL_SECURITY | RECOGNIZED | zone: ZONE-A · camera: CAM-A-01 · authorization: UNAUTHORIZED · person: P003 |

### Scenario V18

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| V18-E1 | +0 min (01:00) | ENVIRONMENTAL | HIGH_TEMPERATURE | zone: ZONE-A · rack: RACK-A1 · server: SRV-A1-01 · source class: HARDWARE_TELEMETRY · temperature: 43.1 °C · humidity: 39.0 % |
| V18-E2 | +3 min (01:03) | MAINTENANCE | AT_RISK | zone: ZONE-A · rack: RACK-A1 · server: SRV-A1-01 · failure probability: 0.79 |
| V18-E3 | +20 min (01:20) | CYBERSECURITY | ANOMALY_CANDIDATE | zone: ZONE-B · rack: RACK-B1 · server: SRV-B1-01 |

### Scenario V19

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| V19-E1 | +0 min (16:00) | CYBERSECURITY | ANOMALY_CANDIDATE | zone: ZONE-B · rack: RACK-B1 · server: SRV-B1-02 |
| V19-E2 | +70 min (17:10) | ENVIRONMENTAL | HIGH_TEMPERATURE | zone: ZONE-A · rack: RACK-A1 · server: SRV-A1-01 · source class: HARDWARE_TELEMETRY · temperature: 41.8 °C · humidity: 38.0 % |
| V19-E3 | +72 min (17:12) | MAINTENANCE | AT_RISK | zone: ZONE-A · rack: RACK-A1 · server: SRV-A1-01 · failure probability: 0.52 |

### Scenario V20

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| V20-E1 | +0 min (02:15) | ENVIRONMENTAL | HIGH_TEMPERATURE | zone: ZONE-C · sensor: SEN-C-01 · source class: ENVIRONMENTAL_SENSOR · temperature: 36.8 °C · humidity: 41.0 % |
| V20-E2 | +5 min (02:20) | SAFETY | PPE_NON_COMPLIANT | zone: ZONE-C · camera: CAM-C-01 · confidence: 0.55 |
| V20-E3 | +33 min (02:48) | MAINTENANCE | AT_RISK | zone: ZONE-B · rack: RACK-B1 · server: SRV-B1-02 · failure probability: 0.76 |

### Scenario V21

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| V21-E1 | +0 min (05:30) | ENVIRONMENTAL | HIGH_TEMPERATURE | zone: ZONE-B · rack: RACK-B1 · server: SRV-B1-02 · source class: HARDWARE_TELEMETRY · temperature: 42.5 °C · humidity: 40.0 % |
| V21-E2 | +4 min (05:34) | MAINTENANCE | AT_RISK | zone: ZONE-B · rack: RACK-B1 · server: SRV-B1-02 · failure probability: 0.55 |

### Scenario V22

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| V22-E1 | +0 min (22:10) | PHYSICAL_SECURITY | RECOGNIZED | zone: ZONE-B · camera: CAM-B-01 · authorization: UNAUTHORIZED · person: P003 |
| V22-E2 | +38 min (22:48) | CYBERSECURITY | HIGH_CONFIDENCE_ANOMALY | zone: ZONE-B · rack: RACK-B1 · server: SRV-B1-01 |

### Scenario V23

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| V23-E1 | +0 min (13:00) | ENVIRONMENTAL | HIGH_HUMIDITY | zone: ZONE-A · sensor: SEN-A-01 · source class: ENVIRONMENTAL_SENSOR · temperature: 24.1 °C · humidity: 85.0 % |
| V23-E2 | +2 min (13:02) | PHYSICAL_SECURITY | RECOGNIZED | zone: ZONE-A · camera: CAM-A-01 · authorization: UNAUTHORIZED · person: P003 |
| V23-E3 | +5 min (13:05) | CYBERSECURITY | EXPLICIT_SECURITY_EVENT | zone: ZONE-A · rack: RACK-A1 · server: SRV-A1-01 |
| V23-E4 | +12 min (13:12) | MAINTENANCE | AT_RISK | zone: ZONE-A · rack: RACK-A1 · server: SRV-A1-02 · failure probability: 0.74 |

### Scenario V24

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| V24-E1 | +0 min (11:10) | ENVIRONMENTAL | HIGH_TEMPERATURE | zone: ZONE-A · sensor: SEN-A-01 · source class: ENVIRONMENTAL_SENSOR · temperature: 47.5 °C · humidity: 28.0 % |
| V24-E2 | +4 min (11:14) | SAFETY | PPE_NON_COMPLIANT | zone: ZONE-A · camera: CAM-A-01 · confidence: 0.88 |
| V24-E3 | +5 min (11:15) | PHYSICAL_SECURITY | UNKNOWN_PERSON | zone: ZONE-A · camera: CAM-A-01 |

### Scenario V25

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| V25-E1 | +0 min (15:25) | PHYSICAL_SECURITY | UNKNOWN_PERSON | zone: ZONE-A · camera: CAM-A-01 |
| V25-E2 | +8 min (15:33) | CYBERSECURITY | ANOMALY_CANDIDATE | zone: ZONE-A · rack: RACK-A1 · server: SRV-A1-01 |

### Scenario V26

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| V26-E1 | +0 min (18:30) | ENVIRONMENTAL | HIGH_HUMIDITY | zone: ZONE-C · sensor: SEN-C-01 · source class: ENVIRONMENTAL_SENSOR · temperature: 24.5 °C · humidity: 93.0 % |
| V26-E2 | +9 min (18:39) | SAFETY | PPE_NON_COMPLIANT | zone: ZONE-C · camera: CAM-C-01 · confidence: 0.8 |
| V26-E3 | +15 min (18:45) | MAINTENANCE | AT_RISK | zone: ZONE-B · rack: RACK-B1 · server: SRV-B1-01 · failure probability: 0.53 |

### Scenario V27

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| V27-E1 | +0 min (12:00) | CYBERSECURITY | HIGH_CONFIDENCE_ANOMALY | zone: ZONE-A · rack: RACK-A1 · server: SRV-A1-01 |
| V27-E2 | +44 min (12:44) | PHYSICAL_SECURITY | UNKNOWN_PERSON | zone: ZONE-A · camera: CAM-A-01 |

### Scenario V28

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| V28-E1 | +0 min (04:10) | ENVIRONMENTAL | HIGH_HUMIDITY | zone: ZONE-B · sensor: SEN-B-01 · source class: ENVIRONMENTAL_SENSOR · temperature: 25.0 °C · humidity: 91.0 % |
| V28-E2 | +16 min (04:26) | MAINTENANCE | AT_RISK | zone: ZONE-B · rack: RACK-B1 · server: SRV-B1-02 · failure probability: 0.71 |

### Scenario V29

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| V29-E1 | +0 min (06:30) | ENVIRONMENTAL | HIGH_TEMPERATURE | zone: ZONE-C · sensor: SEN-C-01 · source class: ENVIRONMENTAL_SENSOR · temperature: 38.2 °C · humidity: 40.0 % |
| V29-E2 | +18 min (06:48) | ENVIRONMENTAL | HIGH_TEMPERATURE | zone: ZONE-A · sensor: SEN-A-01 · source class: ENVIRONMENTAL_SENSOR · temperature: 36.9 °C · humidity: 45.0 % |
| V29-E3 | +52 min (07:22) | MAINTENANCE | AT_RISK | zone: ZONE-A · rack: RACK-A1 · server: SRV-A1-02 · failure probability: 0.73 |
| V29-E4 | +55 min (07:25) | MAINTENANCE | AT_RISK | zone: ZONE-A · rack: RACK-A1 · server: SRV-A1-01 · failure probability: 0.48 |

### Scenario V30

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| V30-E1 | +0 min (09:40) | PHYSICAL_SECURITY | UNKNOWN_PERSON | zone: ZONE-B · camera: CAM-B-01 |
| V30-E2 | +1 min (09:41) | SAFETY | PPE_NON_COMPLIANT | zone: ZONE-B · camera: CAM-B-01 · confidence: 0.81 |

### Scenario V31

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| V31-E1 | +0 min (19:30) | PHYSICAL_SECURITY | RECOGNIZED | zone: ZONE-A · camera: CAM-A-01 · authorization: UNAUTHORIZED · person: P003 |
| V31-E2 | +21 min (19:51) | CYBERSECURITY | HIGH_CONFIDENCE_ANOMALY | zone: ZONE-A · rack: RACK-A1 · server: SRV-A1-01 |
| V31-E3 | +80 min (20:50) | ENVIRONMENTAL | HIGH_TEMPERATURE | zone: ZONE-A · sensor: SEN-A-01 · source class: ENVIRONMENTAL_SENSOR · temperature: 36.2 °C · humidity: 47.0 % |

### Scenario V32

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| V32-E1 | +0 min (10:05) | PHYSICAL_SECURITY | UNKNOWN_PERSON | zone: ZONE-B · camera: CAM-B-01 |
| V32-E2 | +3 min (10:08) | CYBERSECURITY | ANOMALY_CANDIDATE | zone: ZONE-B · rack: RACK-B1 · server: SRV-B1-02 |

### Scenario V33

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| V33-E1 | +0 min (12:20) | ENVIRONMENTAL | HIGH_HUMIDITY | zone: ZONE-B · sensor: SEN-B-01 · source class: ENVIRONMENTAL_SENSOR · temperature: 24.6 °C · humidity: 86.0 % |
| V33-E2 | +7 min (12:27) | CYBERSECURITY | HIGH_CONFIDENCE_ANOMALY | zone: ZONE-B · rack: RACK-B1 · server: SRV-B1-01 |

### Scenario V34

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| V34-E1 | +0 min (08:00) | MAINTENANCE | AT_RISK | zone: ZONE-A · rack: RACK-A1 · server: SRV-A1-01 · failure probability: 0.84 |
| V34-E2 | +48 min (08:48) | SAFETY | PPE_NON_COMPLIANT | zone: ZONE-A · camera: CAM-A-01 · confidence: 0.77 |

### Scenario V35

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| V35-E1 | +0 min (17:10) | PHYSICAL_SECURITY | UNKNOWN_PERSON | zone: ZONE-C · camera: CAM-C-01 |
| V35-E2 | +2 min (17:12) | SAFETY | PPE_NON_COMPLIANT | zone: ZONE-C · camera: CAM-C-01 · confidence: 0.72 |

### Scenario V36

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| V36-E1 | +0 min (16:40) | ENVIRONMENTAL | HIGH_TEMPERATURE | zone: ZONE-B · rack: RACK-B1 · server: SRV-B1-02 · source class: HARDWARE_TELEMETRY · temperature: 42.0 °C · humidity: 41.0 % |
| V36-E2 | +11 min (16:51) | MAINTENANCE | AT_RISK | zone: ZONE-B · rack: RACK-B1 · server: SRV-B1-02 · failure probability: 0.51 |

### Scenario V37

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| V37-E1 | +0 min (13:55) | ENVIRONMENTAL | HIGH_TEMPERATURE | zone: ZONE-B · sensor: SEN-B-01 · source class: ENVIRONMENTAL_SENSOR · temperature: 38.4 °C · humidity: 42.0 % |
| V37-E2 | +27 min (14:22) | MAINTENANCE | AT_RISK | zone: ZONE-B · rack: RACK-B1 · server: SRV-B1-01 · failure probability: 0.72 |
| V37-E3 | +29 min (14:24) | MAINTENANCE | AT_RISK | zone: ZONE-B · rack: RACK-B1 · server: SRV-B1-02 · failure probability: 0.49 |

### Scenario V38

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| V38-E1 | +0 min (07:45) | ENVIRONMENTAL | HIGH_TEMPERATURE | zone: ZONE-C · sensor: SEN-C-01 · source class: ENVIRONMENTAL_SENSOR · temperature: 46.0 °C · humidity: 30.0 % |
| V38-E2 | +7 min (07:52) | SAFETY | PPE_NON_COMPLIANT | zone: ZONE-C · camera: CAM-C-01 · confidence: 0.66 |

### Scenario V39

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| V39-E1 | +0 min (10:30) | MAINTENANCE | AT_RISK | zone: ZONE-B · rack: RACK-B1 · server: SRV-B1-01 · failure probability: 0.88 |
| V39-E2 | +35 min (11:05) | SAFETY | PPE_NON_COMPLIANT | zone: ZONE-B · camera: CAM-B-01 · confidence: 0.79 |

### Scenario V40

| Event | Time | Domain | State | Details |
|---|---|---|---|---|
| V40-E1 | +0 min (22:25) | PHYSICAL_SECURITY | RECOGNIZED | zone: ZONE-C · camera: CAM-C-01 · authorization: UNAUTHORIZED · person: P001 |
| V40-E2 | +12 min (22:37) | ENVIRONMENTAL | HIGH_TEMPERATURE | zone: ZONE-C · sensor: SEN-C-01 · source class: ENVIRONMENTAL_SENSOR · temperature: 37.9 °C · humidity: 39.0 % |
| V40-E3 | +58 min (23:23) | MAINTENANCE | AT_RISK | zone: ZONE-A · rack: RACK-A1 · server: SRV-A1-01 · failure probability: 0.71 |
