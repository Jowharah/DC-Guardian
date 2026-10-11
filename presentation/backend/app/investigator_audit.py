"""Outbound minimization and a hash-chained audit of every Investigator OpenAI call.

minimize(): applied at the single point where Investigator requests leave
(investigator_chat.ask_model), whatever the mode. Removes fields that are never
needed to explain Evidence and must not leave the system: facial landmarks and
face boxes, embeddings, images, reviewer identity, free-text rationale,
credentials. Mode-specific allowlists still apply first; this is the backstop.

record_call(): one append-only row per call (answered or failed): who, when,
mode, target, zone, Evidence references, model, SHA-256 of the exact payload
sent and of the answer, and the claim-check status. Content itself is not
stored here (opt-in history keeps conversations). Same chain scheme as the
review audits, verified by review_integrity.verify_records.
"""
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from uuid import uuid4

from presentation.backend.app.incident_store import _db_path

DENIED_KEYS = frozenset({
    "facial_area", "landmarks", "embedding", "embeddings", "face_embedding", "image", "image_bytes",
    "image_base64", "image_path", "thumbnail", "rationale", "reviewer", "evaluated_by", "created_by",
    "owner", "password", "api_key", "token", "authorization_header", "raw_log", "raw_lines",
})
FIELDS = ("audit_id", "recorded_at", "subject", "mode", "target_id", "zone_id", "evidence_refs",
          "model", "outcome", "payload_sha256", "answer_sha256", "claim_status", "previous_hash", "entry_hash")


def minimize(value):
    """Deep copy without denied keys (any nesting level)."""
    if isinstance(value, dict):
        return {k: minimize(v) for k, v in value.items() if k not in DENIED_KEYS}
    if isinstance(value, list):
        return [minimize(v) for v in value]
    return value


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest() if text is not None else None


def connect():
    db = sqlite3.connect(_db_path(), timeout=15)
    db.execute("""CREATE TABLE IF NOT EXISTS investigator_audit(
        audit_id TEXT PRIMARY KEY, recorded_at TEXT NOT NULL, subject TEXT NOT NULL, mode TEXT NOT NULL,
        target_id TEXT NOT NULL, zone_id TEXT, evidence_refs TEXT NOT NULL, model TEXT NOT NULL,
        outcome TEXT NOT NULL, payload_sha256 TEXT NOT NULL, answer_sha256 TEXT, claim_status TEXT,
        previous_hash TEXT NOT NULL, entry_hash TEXT NOT NULL)""")
    return db


def record_call(call, *, outcome, answer=None, claim_status=None):
    """call: dict with subject, mode, target_id, zone_id, evidence_refs, model, payload (exact JSON text)."""
    entry = {"audit_id": "DCG-IA-" + uuid4().hex.upper(), "recorded_at": datetime.now(timezone.utc).isoformat(),
             "subject": call["subject"], "mode": call["mode"], "target_id": call["target_id"],
             "zone_id": call.get("zone_id"), "evidence_refs": json.dumps(call.get("evidence_refs") or [], sort_keys=True),
             "model": call["model"], "outcome": outcome, "payload_sha256": digest(call["payload"]),
             "answer_sha256": digest(answer), "claim_status": claim_status}
    with connect() as db:
        previous = db.execute("SELECT entry_hash FROM investigator_audit ORDER BY rowid DESC LIMIT 1").fetchone()
        entry["previous_hash"] = previous[0] if previous else "GENESIS"
        entry["entry_hash"] = hashlib.sha256(json.dumps(entry, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        db.execute("INSERT INTO investigator_audit VALUES (" + ",".join("?" * len(FIELDS)) + ")",
                   tuple(entry[f] for f in FIELDS))
    return entry


def verify():
    from presentation.backend.app.review_integrity import verify_records
    with connect() as db:
        rows = db.execute("SELECT " + ",".join(FIELDS) + " FROM investigator_audit ORDER BY rowid ASC").fetchall()  # nosec B608: constant columns
    return verify_records(rows, FIELDS)
