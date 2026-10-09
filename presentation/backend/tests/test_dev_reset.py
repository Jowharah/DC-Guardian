import json
import sqlite3
from presentation.backend.app.dev_reset import event_ids,inventory

def test_event_ids_from_stored_evidence():
    db=sqlite3.connect(":memory:")
    db.execute("CREATE TABLE ssh_published_evidence(event_id TEXT)")
    db.execute("INSERT INTO ssh_published_evidence VALUES ('SSH-EVT-ONE')")
    db.execute("CREATE TABLE maintenance_evidence(workflow_json TEXT)")
    db.execute("INSERT INTO maintenance_evidence VALUES (?)",(json.dumps({"graph_event_id":"MAINT-EVT-ONE-MAPPED"}),))
    db.execute("CREATE TABLE environmental_batches(event_ids_json TEXT)")
    db.execute("INSERT INTO environmental_batches VALUES (?)",(json.dumps(["ENV-EVT-ONE"]),))
    db.execute("CREATE TABLE face_observations(observation_id TEXT)")
    db.execute("INSERT INTO face_observations VALUES ('FACE-IMG-ONE')")
    assert event_ids(db)==sorted(["SSH-EVT-ONE-MAPPED","MAINT-EVT-ONE-MAPPED",
                                  "ENV-EVT-ONE-MAPPED","IMG-EVT-FACE-IMG-ONE"])

def test_inventory_does_not_modify_database(tmp_path):
    path=tmp_path/"presentation.sqlite3"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE ppe_observations(observation_id TEXT)")
        db.execute("INSERT INTO ppe_observations VALUES ('PPE-IMG-ONE')")
    report=inventory(path,tmp_path/"state.sqlite3")
    assert report["tables"]["ppe_observations"]==1
    assert report["mapped_event_ids"]==["IMG-EVT-PPE-IMG-ONE"]
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT COUNT(*) FROM ppe_observations").fetchone()[0]==1
