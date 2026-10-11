import asyncio
import json
import os
import sqlite3
import time
from pathlib import Path
from presentation.backend.app import continuous_ingestion as ingest
from presentation.backend.app.authorization import Principal

def test_config_rejects_unknown_zone(tmp_path):
    folder=tmp_path/"incoming";folder.mkdir()
    config=tmp_path/"config.json"
    config.write_text(json.dumps({"sources":[{"kind":"ssh","directory":str(folder),
        "zone_id":"ZONE-INVALID","server_id":"SRV-B1-01"}]}))
    try:
        ingest.load_config(config)
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid zone accepted")

def test_scan_deduplicates_completed_file(tmp_path,monkeypatch):
    folder=tmp_path/"incoming";folder.mkdir()
    file=folder/"sample.log";file.write_text("approved synthetic ssh log")
    os.utime(file,(time.time()-20,time.time()-20))
    source={"kind":"ssh","directory":folder,"zone_id":"ZONE-B","server_id":"SRV-B1-01"}
    principal=Principal("operator",frozenset({"administrator"}),frozenset({"ZONE-B"}))
    calls=[]
    async def fake_dispatch(src,data,name,p,metadata=None):
        calls.append(name)
        # Same summary fields the real SSH dispatch returns and scan_once logs.
        return {"events":1,"partial":0,"processing_outcome":"PUBLISHED","parsed_count":1,
                "assessment_count":1,"security_relevant_count":1,"decision_complete_count":1}
    monkeypatch.setattr(ingest,"dispatch",fake_dispatch)
    with ingest.state_db(tmp_path/"state.sqlite3") as db:
        first=asyncio.run(ingest.scan_once([source],db,principal))
        second=asyncio.run(ingest.scan_once([source],db,principal))
    assert first["processed"]==1
    assert second["skipped"]==1
    assert calls==["sample.log"]

def test_preview_does_not_delete_input(tmp_path,monkeypatch):
    folder=tmp_path/"incoming";folder.mkdir()
    file=folder/"sample.csv";file.write_text("test")
    os.utime(file,(time.time()-20,time.time()-20))
    async def fake_dispatch(*args):return {"events":1,"partial":0}
    monkeypatch.setattr(ingest,"dispatch",fake_dispatch)
    principal=Principal("operator",frozenset({"administrator"}),frozenset({"ZONE-B"}))
    with ingest.state_db(tmp_path/"state.sqlite3") as db:
        asyncio.run(ingest.scan_once([{"kind":"maintenance","directory":folder,
            "zone_id":"ZONE-B","server_id":"SRV-B1-01"}],db,principal))
    assert file.exists()
