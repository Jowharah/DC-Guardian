"""Backup and restore check: consistent copy, manifest hashes, audit chains in the copy."""
import json
import sqlite3
from pathlib import Path

import pytest

from presentation.backend.app import backup, investigator_audit
from presentation.backend.app.incident_store import _db_path


def audited_call(n):
    investigator_audit.record_call({"subject": "op", "mode": "single", "target_id": f"ssh:S{n}", "zone_id": "ZONE-A",
                                    "evidence_refs": [], "model": "m", "payload": f"p{n}"},
                                   outcome="ANSWERED", answer="a", claim_status="NO_RECOGNIZED_PROBLEM")


@pytest.fixture
def live_data():
    audited_call(1)
    audited_call(2)
    images = Path(_db_path()).parent / "ppe_images"
    images.mkdir(exist_ok=True)
    (images / "img.png").write_bytes(b"png-bytes")


def test_backup_copies_data_and_verifies(live_data, tmp_path_factory):
    folder, manifest = backup.create(tmp_path_factory.mktemp("offsite"), include_graph=False)
    assert (folder / "presentation.sqlite3").exists() and (folder / "ppe_images" / "img.png").exists()
    assert manifest["tables"]["investigator_audit"] == 2
    assert manifest["audit_chains"]["investigator_calls"]["status"] == "PASS"
    assert backup.verify(folder)["status"] == "PASS"


def test_backup_does_not_change_the_live_database(live_data, tmp_path_factory):
    before = backup.sha256(_db_path())
    backup.create(tmp_path_factory.mktemp("offsite"), include_graph=False)
    assert backup.sha256(_db_path()) == before


def test_verify_detects_a_changed_or_tampered_copy(live_data, tmp_path_factory):
    folder, _ = backup.create(tmp_path_factory.mktemp("offsite"), include_graph=False)
    (folder / "ppe_images" / "img.png").write_bytes(b"other")
    with sqlite3.connect(folder / "presentation.sqlite3") as db:
        db.execute("UPDATE investigator_audit SET subject='x'")
    report = backup.verify(folder)
    assert report["status"] == "FAILED"
    assert any("changed ppe_images/img.png" in p for p in report["problems"])
    assert any("investigator_calls" in p for p in report["problems"])


def test_backups_must_be_written_outside_the_data_folder(live_data):
    with pytest.raises(ValueError):
        backup.create(Path(_db_path()).parent / "backups", include_graph=False)


def test_unreachable_neo4j_is_recorded_not_fatal(live_data, tmp_path_factory, monkeypatch):
    monkeypatch.setenv("NEO4J_URI", "bolt://127.0.0.1:1")
    monkeypatch.setattr(backup, "export_graph", lambda target: None)
    folder, manifest = backup.create(tmp_path_factory.mktemp("offsite"))
    assert manifest["graph"].startswith("NOT_EXPORTED")
    assert json.loads((folder / "manifest.json").read_text(encoding="utf-8"))["version"] == backup.VERSION
