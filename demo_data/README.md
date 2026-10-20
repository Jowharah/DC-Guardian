# Demo data

Small fixed inputs for a fresh installation, loaded with `python demo_data/load_demo_data.py` (see [Installation and User Guide](../docs/INSTALLATION_AND_USER_GUIDE.md)).

| File | Loaded as | Source and terms |
|---|---|---|
| `inputs/ssh/demo_ssh_bruteforce.txt` | SSH log, ZONE-A, server SRV-A1-02 | Four lines (source IP 5.36.59.76) from LogHub `OpenSSH_2k.log`: Zhu et al. (2023), *Loghub*, ISSRE 2023; free for research or academic work, citing the paper and referring to the repository. |
| `inputs/smart/demo_drive_1.csv`, `demo_drive_2.csv` | SMART histories, ZONE-B, server SRV-B1-01 | Synthetic (drive `DEMO-DRIVE-001`), written for the project |
| `inputs/sensors/demo_sensor_1.csv`, `demo_sensor_2.csv` | Room-sensor readings, ZONE-B, sensor SEN-B-01 | Synthetic, written for the project; readings rise above the 35 °C threshold |

No images are included, because face photos are never committed and the SH17 photos show identifiable people. Add your own camera images in Scenario Lab (PPE image validation). Face recognition also needs an enrollment built from your own controlled photos (see the guide).
