# DC-Guardian local continuous ingestion (controlled prototype)

This **opt-in separate process** watches approved local directories. It does not
start with FastAPI and does not connect to physical hardware or remote servers.
It uses the existing frozen SSH, maintenance, and environmental workflows.

## Configuration

Create an untracked JSON configuration file outside Git, e.g.
`C:/dcg-private/ingestion.json`:

```json
{
  "sources": [
    {"kind":"ssh","directory":"C:/dcg-private/incoming/ssh","zone_id":"ZONE-B","server_id":"SRV-B1-01"},
    {"kind":"maintenance","directory":"C:/dcg-private/incoming/smart","zone_id":"ZONE-B","server_id":"SRV-B1-01"},
    {"kind":"environment","directory":"C:/dcg-private/incoming/sensors","zone_id":"ZONE-B","sensor_id":"SEN-B-01"}
  ]
}
```

Create the three directories before starting. Only place **approved, licensed,
non-sensitive controlled test data** in these folders. Never commit raw logs,
biometric evidence, secrets, or actual employee data.

The process uses `DCG_LOCAL_USER`, `DCG_LOCAL_ROLE`, and `DCG_LOCAL_ZONES`
from the existing local authentication configuration. The role must have the
domain-specific detail permission and `scenario:execute` for each zone.

## Run one scan

From the repository root, with `.venv-dc-guardian` activated:

```powershell
python -m presentation.backend.app.continuous_ingestion --config "C:/dcg-private/ingestion.json" --state "C:/dcg-private/ingestion_state.sqlite3"
```

## Poll every 30 seconds

```powershell
python -m presentation.backend.app.continuous_ingestion --config "C:/dcg-private/ingestion.json" --state "C:/dcg-private/ingestion_state.sqlite3" --interval 30
```

Stop with Ctrl+C. Each file must be at least five seconds old and within the
existing upload size limits. Only immediate files (no nested directories) with
`.log`/`.txt` for SSH or `.csv` for maintenance/environment are considered.
The worker never deletes or moves source files.

Completed files are skipped on subsequent scans using file path and SHA-256.
A changed file is treated as a new input. Failed files can be retried; note that
some downstream graph writes may have happened before a failure, so do not
repeatedly retry unreviewed failures. A partial SSH event is checkpointed as
PARTIAL and requires operator review. This is **not exactly-once delivery**.

This worker does not perform cross-session correlation, assign unsupported
Decision severity, or provide a production-grade streaming service. Use the
Monitoring Feed to inspect published evidence and individual stage results.

Tests:
```powershell
python -m pytest presentation/backend/tests/test_continuous_ingestion.py -q
```
