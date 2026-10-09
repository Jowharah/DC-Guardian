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

## PPE and Face image ingestion (explicit opt-in)

The worker also supports `ppe` and `face` sources, but image retention must
be explicitly enabled per source. Create private folders outside the repository:

```json
{"kind":"ppe","directory":"C:/dcg-private/incoming/ppe","zone_id":"ZONE-B","retain_approved_images":true},
{"kind":"face","directory":"C:/dcg-private/incoming/face","zone_id":"ZONE-B","retain_approved_images":true}
```

Add these two objects inside the existing `sources` array (not as a separate
JSON document). Create both folders first. Only place approved test images
there, and ensure your organization permits biometric enrollment and retention.
The worker uses the same frozen `.venv-ppe` GPU and `.venv-face` inference
subprocesses as the existing manual validation endpoints. Accepted image
extensions: JPG, JPEG and PNG, up to 8 MiB. The existing image validators
check the decoded format and pixel limits. PPE requires CAMERA_DETAIL;
Face requires PERSON_DETAIL for the selected zone. Retained images are served
only by the existing authenticated observation image endpoints.

**Important scope boundary:** This is continuous *observation* ingestion, not
yet graph correlation or a Decision incident for PPE/Face. A recognized face
does not establish zone authorization or severity. PPE and Face images are
not automatically assigned to a physical camera without verified provenance.
The worker leaves source files in their incoming folders, which must have
private filesystem ACLs; do not use shared or synced directories. Existing
SHA-256 checkpoints prevent reprocessing the same unchanged file path after
successful completion. The worker does not yet provide encrypted-at-rest
storage, automated retention expiry, or end-to-end artifact auditing.

## Optional camera/capture-time sidecars (controlled prototype)

For an approved `incoming/ppe/worker.jpg`, place a JSON sidecar named
`worker.jpg.metadata.json` in the same folder:

```json
{"camera_id":"CAM-B-01","captured_at":"2026-10-09T08:05:00Z"}
```

For an approved `incoming/face/employee.jpg`, use
`employee.jpg.metadata.json` with its **actual** camera and capture time.
The worker validates camera membership in the declared zone, timezone-aware
ISO timestamps and non-future capture time. If a valid sidecar is present,
the worker writes a separate Neo4j Evidence event linked to the declared
camera. Original image retention and image access remain under the existing
PPE/Face observation APIs.

**Do not invent capture metadata for real images.** A matching topology
camera does not authenticate the claimed source: provenance remains
`OPERATOR_DECLARED_UNVERIFIED`. The new projection is not a validated
Common Event adapter, correlation result, authorization result, or Decision.
No physical-security incident is created automatically. If no sidecar exists,
the existing image-only ingestion behavior is unchanged.

Sidecars are only suitable for approved controlled testing until signed or
otherwise independently verified camera-source metadata is available.
