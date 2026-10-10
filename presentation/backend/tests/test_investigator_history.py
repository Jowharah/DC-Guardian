import pytest
from fastapi import HTTPException
from presentation.backend.app import investigator_history as history
from presentation.backend.app.authorization import Principal

ADMIN=Principal("operator-a",frozenset({"administrator"}),frozenset({"ZONE-A"}))
OTHER=Principal("operator-b",frozenset({"administrator"}),frozenset({"ZONE-B"}))

@pytest.fixture
def isolated(monkeypatch,tmp_path):
    monkeypatch.setattr(history,"_db_path",lambda:tmp_path/"history.sqlite3")
    monkeypatch.setattr(history,"local_setting",lambda key:{"DCG_INVESTIGATOR_HISTORY_ENABLED":"1","DCG_INVESTIGATOR_HISTORY_DAYS":"7"}.get(key,""))
    def group(group_id,principal):
        if "ZONE-A" not in principal.zones:raise HTTPException(403,"Access denied")
        return {"id":group_id,"zone_id":"ZONE-A"}
    monkeypatch.setattr(history,"find_group",group)

def test_save_reload_and_clear(isolated):
    row=history.save_history("G1",history.HistoryEntry(question="What happened?",answer="An anomaly was reported."),ADMIN)
    assert row["id"].startswith("DCG-CHAT-")
    assert len(history.get_history("G1",ADMIN)["messages"])==1
    assert history.get_history("G2",ADMIN)["messages"]==[]
    history.clear_history("G1",ADMIN)
    assert history.get_history("G1",ADMIN)["messages"]==[]

def test_cross_zone_denied_before_db(isolated):
    with pytest.raises(HTTPException) as exc:
        history.get_history("G1",OTHER)
    assert exc.value.status_code==403

def test_disabled_by_default(isolated,monkeypatch):
    monkeypatch.setattr(history,"local_setting",lambda key:"")
    with pytest.raises(HTTPException) as exc:
        history.get_history("G1",ADMIN)
    assert exc.value.status_code==503

def test_same_zone_different_operator_is_private(isolated):
    colleague=Principal("operator-colleague",frozenset({"administrator"}),frozenset({"ZONE-A"}))
    history.save_history("G1",history.HistoryEntry(question="What happened?",answer="An anomaly was reported."),ADMIN)
    assert history.get_history("G1",colleague)["messages"]==[]
    history.save_history("G1",history.HistoryEntry(question="What now?",answer="Review the evidence."),colleague)
    assert len(history.get_history("G1",ADMIN)["messages"])==1
    assert len(history.get_history("G1",colleague)["messages"])==1
    history.clear_history("G1",colleague)
    assert len(history.get_history("G1",ADMIN)["messages"])==1
    assert history.get_history("G1",colleague)["messages"]==[]
