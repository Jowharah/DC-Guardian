"""External audit checkpoints: detect tail deletion and database replacement."""
import json
import shutil
from pathlib import Path

import pytest

from presentation.backend.app import audit_checkpoint, investigator_audit
from presentation.backend.app.incident_store import _db_path


def call(n):
    investigator_audit.record_call({"subject": "op", "mode": "single", "target_id": f"ssh:S{n}", "zone_id": "ZONE-A",
                                    "evidence_refs": [], "model": "m", "payload": f"p{n}"},
                                   outcome="ANSWERED", answer="a", claim_status="NO_RECOGNIZED_PROBLEM")


def test_checkpoint_passes_and_counts_records_added_since(tmp_path):
    call(1); call(2)
    checkpoint = audit_checkpoint.snapshot()
    call(3)
    report = audit_checkpoint.verify(checkpoint)
    assert report["status"] == "PASS"
    assert report["chains"]["investigator_calls"]["added_since"] == 1


def test_deleting_the_newest_records_is_detected():
    call(1); call(2)
    checkpoint = audit_checkpoint.snapshot()
    with investigator_audit.connect() as db:
        db.execute("DELETE FROM investigator_audit WHERE rowid=(SELECT max(rowid) FROM investigator_audit)")
    report = audit_checkpoint.verify(checkpoint)
    assert report["status"] == "FAILED"
    assert report["chains"]["investigator_calls"]["reason"] == "RECORDS_MISSING_SINCE_CHECKPOINT"


def test_replacing_the_database_is_detected(tmp_path):
    call(1)
    original = Path(_db_path())
    backup = tmp_path / "older.sqlite3"
    shutil.copy(original, backup)
    call(2)
    checkpoint = audit_checkpoint.snapshot()
    # Swap in an older but internally consistent copy, then add a fresh record so the length matches.
    shutil.copy(backup, original)
    call(99)
    report = audit_checkpoint.verify(checkpoint)
    assert report["status"] == "FAILED"
    assert report["chains"]["investigator_calls"]["reason"] == "CHECKPOINTED_RECORD_CHANGED_OR_DATABASE_REPLACED"


def test_signed_checkpoint_rejects_edits(monkeypatch):
    monkeypatch.setenv("DCG_CHECKPOINT_KEY", "operator-secret")
    call(1)
    checkpoint = audit_checkpoint.snapshot()
    assert audit_checkpoint.verify(checkpoint)["signature"] == "VERIFIED"
    forged = json.loads(json.dumps(checkpoint))
    forged["chains"]["investigator_calls"]["length"] = 0
    assert audit_checkpoint.verify(forged)["reason"] == "CHECKPOINT_SIGNATURE_INVALID"


def test_checkpoint_must_be_stored_outside_the_database_folder(tmp_path_factory):
    with pytest.raises(ValueError):
        audit_checkpoint.write(Path(_db_path()).parent / "checkpoints")
    path, _ = audit_checkpoint.write(tmp_path_factory.mktemp("offsite"))
    assert path.exists()
