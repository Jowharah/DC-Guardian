# Environmental Monitoring

## Purpose

DC-GUARDIAN Environmental Monitoring is a **deterministic monitoring component**, not a learned ML model. It converts configured environmental and hardware-telemetry conditions into structured assessments for Phase 2.

## Component design

The component supports two broad evidence sources:

- dedicated environmental sensors
- hardware-origin telemetry

The distinction is preserved because a dedicated sensor can provide independent infrastructure evidence, while hardware telemetry may overlap with evidence used by another detector.

## Validation approach

No artificial precision, recall, or accuracy values are reported because there is no learned classifier in the current baseline.

Validation instead checks:

- deterministic threshold/condition behavior,
- expected normal/abnormal assessment states,
- dedicated sensor handling,
- hardware telemetry handling,
- source and provenance preservation, and
- compatibility with the Phase 2 common-event contract.

## Source structure

```text
src/
  config.py
  environmental_detector.py
  sensor_monitor.py
  hardware_monitor.py

tests/
  test_config.py
  test_environmental_detector.py
  test_environmental_sources.py
```

## Phase 2 contract

Environmental evidence is normalized as the `ENVIRONMENTAL` domain. The graph supports dedicated sensors as well as hardware-derived sources without falsely assigning a dedicated sensor to a server merely to enable correlation.

The controlled DC-01 topology currently validates paths including sensor-to-zone, server telemetry, cooling equipment, and hard-drive telemetry.

## Limitations

The current thresholds serve the deterministic research-prototype contract. Production thresholds should be aligned with the selected sensor specifications, equipment operating limits, deployment environment, and operational policy.
