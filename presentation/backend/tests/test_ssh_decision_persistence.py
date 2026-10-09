"""Decision persistence is idempotent and preserves original detector provenance."""
from presentation.backend.app import ssh_publication as pub

def test_saved_decision_round_trip(monkeypatch, tmp_path):
    monkeypatch.setattr(pub, "_db_path", lambda: tmp_path / "ssh_decisions.sqlite3")
    decision={"severity":"MEDIUM","policy_version":"DCG-DECISION-v1",
              "autonomous_action_allowed":False}
    specialist={"assessment":"Grounded review","grounding_status":"SUPPORTED"}
    correlation={"status":"NO_CORRELATION"}
    pub.save_decision("SSH-EVT-TEST", decision, specialist, correlation)
    saved=pub.load_decision("SSH-EVT-TEST")
    assert saved["decision"]==decision
    assert saved["specialist"]==specialist
    assert saved["correlation"]==correlation
    pub.save_decision("SSH-EVT-TEST", decision, specialist, correlation)
    with pub.connect() as conn:
        count=conn.execute("SELECT count(*) FROM ssh_decisions").fetchone()[0]
    assert count==1
